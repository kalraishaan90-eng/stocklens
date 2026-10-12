import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional

# Minimum NET move (%) for a cluster of significant days to be reported as an
# anomaly (matches the documented "outlier >= 3.2%" rule used in the UI/report).
MIN_NET_MOVE_PCT = 3.2

def detect_price_anomalies(
    df: pd.DataFrame,
    max_events: int = 6
) -> List[Dict[str, Any]]:
    """
    Detects notable price jumps and drops in the 2-year history.
    
    Scientific Rules:
    1. A day is a Significant Move if:
       |return| >= 2.5 standard deviations of that stock's rolling 60-day returns
       OR |return| >= 5.0%.
    2. Consecutive significant days are merged into one event with cumulative return.
    3. Keeps the top 6 events by magnitude per company.
    4. For each event stores: date, % change, direction, volume spike multiplier, and gap up/down.
    5. Returns events sorted chronologically by date.
    """
    if df.empty or "Adj Close" not in df.columns:
        return []

    sorted_df = df.sort_index().copy()
    
    # Ensure columns exist
    if "Close" not in sorted_df.columns:
        sorted_df["Close"] = sorted_df["Adj Close"]
    if "Open" not in sorted_df.columns:
        sorted_df["Open"] = sorted_df["Close"]
    if "Volume" not in sorted_df.columns:
        sorted_df["Volume"] = 1000000

    # Clean index to timezone-naive date if needed
    if sorted_df.index.tz is not None:
        sorted_df.index = sorted_df.index.tz_localize(None).floor("D")
    else:
        sorted_df.index = sorted_df.index.floor("D")

    # 1. Daily returns
    sorted_df["daily_return"] = sorted_df["Adj Close"].pct_change() * 100.0
    
    # 2. Rolling 60-day standard deviation (min_periods=20)
    sorted_df["roll_std"] = sorted_df["daily_return"].rolling(window=60, min_periods=20).std()
    # Fallback for early days with missing rolling std
    overall_std = sorted_df["daily_return"].std()
    if pd.isna(overall_std) or overall_std <= 0:
        overall_std = 2.0
    sorted_df["roll_std"] = sorted_df["roll_std"].fillna(overall_std)

    # 3. 20-day average volume for volume spike multiplier
    sorted_df["vol_ma20"] = sorted_df["Volume"].rolling(window=20, min_periods=5).mean().fillna(sorted_df["Volume"])

    # 4. Open-to-previous-close gap %
    sorted_df["prev_close"] = sorted_df["Close"].shift(1).fillna(sorted_df["Open"])
    sorted_df["gap_pct"] = ((sorted_df["Open"] - sorted_df["prev_close"]) / sorted_df["prev_close"].replace(0, np.nan)) * 100.0
    sorted_df["gap_pct"] = sorted_df["gap_pct"].fillna(0.0)

    # 5. Significant Move condition: |return| >= 2.5 * std OR |return| >= 5%
    threshold_2_5_std = 2.5 * sorted_df["roll_std"]
    is_significant = (sorted_df["daily_return"].abs() >= threshold_2_5_std) | (sorted_df["daily_return"].abs() >= 5.0)
    sorted_df["is_sig"] = is_significant

    # Find indices of significant days
    sig_indices = [i for i, v in enumerate(sorted_df["is_sig"]) if bool(v)]

    # If fewer than 2 significant events found, fallback to top moves to ensure exhibition demo has content
    if len(sig_indices) < 2 and len(sorted_df) >= 10:
        valid_returns = sorted_df["daily_return"].dropna()
        if len(valid_returns) >= 2:
            top_gain_idx = sorted_df.index.get_loc(valid_returns.idxmax())
            top_loss_idx = sorted_df.index.get_loc(valid_returns.idxmin())
            sig_indices = sorted(list(set([top_gain_idx, top_loss_idx])))

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

    events: List[Dict[str, Any]] = []

    for cluster in clusters:
        start_idx = cluster[0]
        end_idx = cluster[-1]

        start_dt = sorted_df.index[start_idx]
        end_dt = sorted_df.index[end_idx]

        prev_idx = max(0, start_idx - 1)
        prev_close = sorted_df["Adj Close"].iloc[prev_idx]
        end_close = sorted_df["Adj Close"].iloc[end_idx]

        if prev_close > 0:
            cum_ret = ((end_close - prev_close) / prev_close) * 100.0
        else:
            cum_ret = float(sorted_df["daily_return"].iloc[start_idx])

        # Cluster single-day returns
        cluster_returns = sorted_df["daily_return"].iloc[cluster].values
        max_abs_day = float(np.max(np.abs(cluster_returns))) if len(cluster_returns) > 0 else abs(cum_ret)

        # Volume spike multiplier vs 20-day average volume prior to event
        prev_20_vol = sorted_df["vol_ma20"].iloc[start_idx]
        if pd.isna(prev_20_vol) or prev_20_vol <= 0:
            vol_multiplier = 1.0
        else:
            cluster_vol = sorted_df["Volume"].iloc[cluster].mean()
            vol_multiplier = float(cluster_vol / prev_20_vol)

        # Gap at open of event start
        gap = float(sorted_df["gap_pct"].iloc[start_idx])

        # Direction
        direction = "jump" if cum_ret >= 0 else "drop"
        # Magnitude represents the strength of the shock
        magnitude = max(abs(cum_ret), max_abs_day)

        start_str = start_dt.strftime("%Y-%m-%d")
        end_str = end_dt.strftime("%Y-%m-%d")
        date_label = start_str if start_idx == end_idx else f"{start_str} to {end_str}"

        events.append({
            "date": date_label,
            "primary_date": start_str,
            "start_date": start_str,
            "end_date": end_str,
            "change_pct": round(float(cum_ret), 2),
            "direction": direction,
            "magnitude": round(float(magnitude), 2),
            "volume_spike_multiplier": round(float(vol_multiplier), 2),
            "gap_pct": round(float(gap), 2),
            "is_recent": False
        })

    # Keep top `max_events` by magnitude.
    # Net-move floor (exhibition spec): a cluster of significant days must still
    # net out to a meaningful move (>= 3.2%) - spike+rebound pairs that wash out
    # to noise are not reportable "price shifts".
    events = [e for e in events if abs(e["change_pct"]) >= MIN_NET_MOVE_PCT]
    events.sort(key=lambda x: x["magnitude"], reverse=True)
    top_events = events[:max_events]

    # Re-sort chronologically by start date
    top_events.sort(key=lambda x: x["primary_date"])
    return top_events

def detect_recent_change(
    df: pd.DataFrame,
    threshold_pct: float = 2.5
) -> Optional[Dict[str, Any]]:
    """
    Recent Change Mode:
    Analyzes the last 5 trading days' price action.
    Returns an event if the 5-day move is notable (|return| >= 2.5% OR has a significant spike).
    """
    if df.empty or len(df) < 5 or "Adj Close" not in df.columns:
        return None

    sorted_df = df.sort_index().copy()
    if sorted_df.index.tz is not None:
        sorted_df.index = sorted_df.index.tz_localize(None).floor("D")
    else:
        sorted_df.index = sorted_df.index.floor("D")

    last_5 = sorted_df.iloc[-5:]
    start_dt = last_5.index[0]
    end_dt = last_5.index[-1]

    idx_before_5 = max(0, len(sorted_df) - 6)
    base_close = sorted_df["Adj Close"].iloc[idx_before_5]
    end_close = last_5["Adj Close"].iloc[-1]

    if base_close <= 0:
        return None

    five_day_return = ((end_close - base_close) / base_close) * 100.0

    # Check daily moves within the 5 days
    daily_returns = sorted_df["Adj Close"].pct_change() * 100.0
    recent_daily = daily_returns.iloc[-5:]
    roll_std = daily_returns.rolling(window=60, min_periods=20).std().fillna(2.0)
    recent_sig = ((recent_daily.abs() >= (2.5 * roll_std.iloc[-5:])) | (recent_daily.abs() >= 5.0)).any()

    # Notable if cumulative >= threshold_pct or any single day was significant
    is_notable = (abs(five_day_return) >= threshold_pct) or bool(recent_sig)
    if not is_notable:
        return None

    # Volume comparison
    if "Volume" in sorted_df.columns:
        vol_ma20 = sorted_df["Volume"].rolling(20, min_periods=5).mean().iloc[-5]
        recent_avg_vol = last_5["Volume"].mean()
        vol_multiplier = float(recent_avg_vol / vol_ma20) if (pd.notna(vol_ma20) and vol_ma20 > 0) else 1.0
    else:
        vol_multiplier = 1.0

    # Gap on latest session
    if "Open" in sorted_df.columns and "Close" in sorted_df.columns:
        prev_c = sorted_df["Close"].iloc[-2]
        latest_o = sorted_df["Open"].iloc[-1]
        gap = float(((latest_o - prev_c) / prev_c) * 100.0) if prev_c > 0 else 0.0
    else:
        gap = 0.0

    start_str = start_dt.strftime("%Y-%m-%d")
    end_str = end_dt.strftime("%Y-%m-%d")
    direction = "jump" if five_day_return >= 0 else "drop"

    return {
        "date": f"{start_str} to {end_str} (Last 5 Days)",
        "primary_date": end_str,
        "start_date": start_str,
        "end_date": end_str,
        "change_pct": round(float(five_day_return), 2),
        "direction": direction,
        "magnitude": round(float(abs(five_day_return)), 2),
        "volume_spike_multiplier": round(float(vol_multiplier), 2),
        "gap_pct": round(float(gap), 2),
        "is_recent": True
    }
