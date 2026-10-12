import yfinance as yf
import pandas as pd
import numpy as np

def detect_spikes(df):
    df = df.copy()
    df["Return"] = df["Adj Close"].pct_change() * 100.0
    df["RollStd"] = df["Return"].rolling(window=60, min_periods=20).std()
    df["Vol20"] = df["Volume"].rolling(window=20, min_periods=5).mean()
    
    # Prev Close for gap calculation
    df["PrevClose"] = df["Close"].shift(1)
    # Gap % = (Open - PrevClose) / PrevClose * 100
    df["Gap"] = ((df["Open"] - df["PrevClose"]) / df["PrevClose"]) * 100.0
    
    df["IsSig"] = (df["Return"].abs() >= (2.5 * df["RollStd"])) | (df["Return"].abs() >= 5.0)
    
    sig_indices = [i for i, v in enumerate(df["IsSig"]) if v]
    
    # Merge consecutive trading day indices
    clusters = []
    if sig_indices:
        current_cluster = [sig_indices[0]]
        for idx in sig_indices[1:]:
            if idx == current_cluster[-1] + 1:
                current_cluster.append(idx)
            else:
                clusters.append(current_cluster)
                current_cluster = [idx]
        clusters.append(current_cluster)
        
    events = []
    for cluster in clusters:
        start_idx = cluster[0]
        end_idx = cluster[-1]
        
        start_dt = df.index[start_idx]
        end_dt = df.index[end_idx]
        
        prev_idx = max(0, start_idx - 1)
        prev_close = df["Adj Close"].iloc[prev_idx]
        end_close = df["Adj Close"].iloc[end_idx]
        
        cum_ret = ((end_close - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
        
        # Max single day move magnitude in cluster
        cluster_returns = df["Return"].iloc[cluster].values
        max_abs_single_day = float(np.max(np.abs(cluster_returns)))
        
        # Volume vs 20-day average volume prior to start
        prev_20_vol = df["Vol20"].iloc[start_idx]
        if pd.isna(prev_20_vol) or prev_20_vol == 0:
            vol_multiplier = 1.0
        else:
            avg_cluster_vol = df["Volume"].iloc[cluster].mean()
            vol_multiplier = float(avg_cluster_vol / prev_20_vol)
            
        gap = float(df["Gap"].iloc[start_idx]) if pd.notna(df["Gap"].iloc[start_idx]) else 0.0
        
        date_str = start_dt.strftime("%Y-%m-%d")
        if start_idx != end_idx:
            date_display = f"{start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}"
        else:
            date_display = date_str
            
        # Direction
        direction = "jump" if cum_ret >= 0 else "drop"
        magnitude = max(abs(cum_ret), max_abs_single_day)
        
        events.append({
            "date": date_display,
            "primary_date": start_dt.strftime("%Y-%m-%d"),
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "change_pct": round(cum_ret, 2),
            "direction": direction,
            "magnitude": round(magnitude, 2),
            "volume_spike_multiplier": round(vol_multiplier, 2),
            "gap_pct": round(gap, 2)
        })
        
    # Top 6 by magnitude
    events.sort(key=lambda x: x["magnitude"], reverse=True)
    top_6 = events[:6]
    top_6.sort(key=lambda x: x["primary_date"])
    return top_6

def normalize_df_index(df):
    df = df.copy()
    if df.index.tz is not None:
        df.index = df.index.tz_convert(None).floor("D")
    else:
        df.index = df.index.floor("D")
    return df

def test_market_classification():
    nifty = normalize_df_index(yf.Ticker('^NSEI').history(period='2y', auto_adjust=False))
    nifty['ret'] = nifty['Adj Close'].pct_change() * 100.0
    
    for s, sec_ticker in [('RELIANCE.NS', 'CPSEETF.NS'), ('TITAN.NS', 'CONSUMBEES.NS'), ('ADANIPOWER.NS', 'CPSEETF.NS')]:
        stock = normalize_df_index(yf.Ticker(s).history(period='2y', auto_adjust=False))
        stock['ret'] = stock['Adj Close'].pct_change() * 100.0
        
        sec = normalize_df_index(yf.Ticker(sec_ticker).history(period='2y', auto_adjust=False))
        sec['ret'] = sec['Adj Close'].pct_change() * 100.0
        
        merged = pd.DataFrame({
            'stock': stock['ret'],
            'nifty': nifty['ret'],
            'sec': sec['ret']
        }).dropna()
        
        cov_nifty = merged['stock'].cov(merged['nifty'])
        var_nifty = merged['nifty'].var()
        beta_nifty = cov_nifty / var_nifty if var_nifty > 0 else 1.0
        
        cov_sec = merged['stock'].cov(merged['sec'])
        var_sec = merged['sec'].var()
        beta_sec = cov_sec / var_sec if var_sec > 0 else 1.0
        
        print(f"\n=== {s} (Beta Nifty={beta_nifty:.2f}, Beta Sector={beta_sec:.2f}, Rows={len(merged)}) ===")
        events = detect_spikes(stock)
        for e in events:
            p_dt = pd.to_datetime(e['primary_date'])
            if p_dt in merged.index:
                row = merged.loc[p_dt]
                s_ret = float(row['stock'])
                n_ret = float(row['nifty'])
                sec_ret = float(row['sec'])
                
                resid_nifty = s_ret - (beta_nifty * n_ret)
                resid_sec = s_ret - (beta_sec * sec_ret)
                
                # Classification logic:
                # - Compute residual move = stock return - (beta * NIFTY 50 return)
                # - If NIFTY moved sharply and residual is small -> "Market-wide move"
                # - If Sector moved sharply and residual vs sector is small -> "Sector-wide move"
                # - Otherwise -> "Company-specific move"
                is_nifty_sharp = abs(n_ret) >= 1.25
                is_nifty_resid_small = abs(resid_nifty) <= max(2.5, 0.45 * abs(s_ret)) and (s_ret * n_ret > 0)
                
                is_sec_sharp = abs(sec_ret) >= 1.75
                is_sec_resid_small = abs(resid_sec) <= max(2.5, 0.45 * abs(s_ret)) and (s_ret * sec_ret > 0)
                
                if is_nifty_sharp and is_nifty_resid_small:
                    classification = "Market-wide move"
                elif is_sec_sharp and is_sec_resid_small:
                    classification = "Sector-wide move"
                else:
                    classification = "Company-specific move"
                    
                print(f"  {e['date']}: [{classification}] | Stock={s_ret:+.2f}%, NIFTY={n_ret:+.2f}%, Sector={sec_ret:+.2f}%, Resid={resid_nifty:+.2f}%")



if __name__ == "__main__":
    test_market_classification()


