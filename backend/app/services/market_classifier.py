import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
import yfinance as yf
from app.services.cache import get_cached, set_cached

# Mapping sectors to reliable benchmarks
SECTOR_BENCHMARK_MAP = {
    "energy": ("CPSEETF.NS", "CPSE / Energy Index ETF"),
    "oil": ("CPSEETF.NS", "CPSE / Energy Index ETF"),
    "gas": ("CPSEETF.NS", "CPSE / Energy Index ETF"),
    "power": ("CPSEETF.NS", "Power / Energy Sector ETF"),
    "utility": ("CPSEETF.NS", "Utilities Sector ETF"),
    "consumer": ("CONSUMBEES.NS", "NIFTY Consumption ETF"),
    "fmcg": ("CONSUMBEES.NS", "NIFTY Consumption ETF"),
    "retail": ("CONSUMBEES.NS", "NIFTY Consumption ETF"),
    "durables": ("CONSUMBEES.NS", "NIFTY Consumption ETF"),
    "luxury": ("CONSUMBEES.NS", "NIFTY Consumption ETF"),
    "technology": ("^CNXIT", "NIFTY IT Index"),
    "it": ("^CNXIT", "NIFTY IT Index"),
    "software": ("^CNXIT", "NIFTY IT Index"),
    "banking": ("^NSEBANK", "NIFTY Bank Index"),
    "bank": ("^NSEBANK", "NIFTY Bank Index"),
    "financial": ("^NSEBANK", "NIFTY Bank Index"),
    "auto": ("AUTOBEES.NS", "NIFTY Auto ETF"),
    "automobile": ("AUTOBEES.NS", "NIFTY Auto ETF"),
    "pharma": ("^CNXPHARMA", "NIFTY Pharma Index"),
    "healthcare": ("^CNXPHARMA", "NIFTY Pharma Index"),
    "defence": ("INFRABEES.NS", "NIFTY Infra / Defence ETF"),
    "defense": ("INFRABEES.NS", "NIFTY Infra / Defence ETF"),
    "infra": ("INFRABEES.NS", "NIFTY Infra ETF"),
    "infrastructure": ("INFRABEES.NS", "NIFTY Infra ETF"),
    "capital": ("INFRABEES.NS", "NIFTY Capital Goods ETF"),
    "industrial": ("INFRABEES.NS", "NIFTY Industrials ETF"),
}

def get_sector_benchmark(sector_str: Optional[str]) -> Tuple[str, str]:
    """Selects the best sectoral benchmark symbol and display name."""
    if not sector_str:
        return "^NSEI", "NIFTY 50"
    s_lower = sector_str.lower()
    for key, (ticker, label) in SECTOR_BENCHMARK_MAP.items():
        if key in s_lower:
            return ticker, label
    return "^NSEI", "NIFTY 50"

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df_clean = df.copy()
    if df_clean.index.tz is not None:
        df_clean.index = df_clean.index.tz_localize(None).floor("D")
    else:
        df_clean.index = df_clean.index.floor("D")
    return df_clean

async def fetch_benchmark_series(ticker: str, days: int = 730) -> pd.DataFrame:
    """Fetches benchmark daily price data with caching."""
    cache_key = f"benchmark_series:{ticker}:{days}"
    cached = get_cached(cache_key)
    if cached:
        df = pd.DataFrame(cached)
        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            return df

    def _download():
        t = yf.Ticker(ticker)
        h = t.history(period="2y", auto_adjust=False)
        return h

    try:
        raw_df = await asyncio.wait_for(asyncio.to_thread(_download), timeout=8.0)
        if raw_df is not None and not raw_df.empty:
            df = _normalize_df(raw_df)
            if "Adj Close" not in df.columns:
                df["Adj Close"] = df["Close"]
            
            # Cache
            save_recs = df.reset_index().to_dict(orient="records")
            for r in save_recs:
                r["Date"] = r["Date"].strftime("%Y-%m-%d")
            set_cached(cache_key, save_recs, ttl_seconds=86400)
            return df
    except Exception:
        pass

    return pd.DataFrame()

def classify_event_market_level(
    stock_return: float,
    nifty_return: float,
    sector_return: Optional[float],
    beta_nifty: float = 1.0,
    beta_sector: float = 1.0,
    sector_name: str = "Sector Index"
) -> Dict[str, Any]:
    """
    Classifies the cause level of a sudden move using market context:
    - residual = stock_return - (beta * nifty_return)
    - If NIFTY moved sharply and residual is small -> "Market-wide move"
    - If sector moved sharply and residual vs sector is small -> "Sector-wide move"
    - Otherwise -> "Company-specific move"
    """
    residual_nifty = stock_return - (beta_nifty * nifty_return)
    
    sec_ret = sector_return if sector_return is not None else 0.0
    residual_sector = stock_return - (beta_sector * sec_ret)

    # NIFTY sharp move: absolute return >= 1.25%
    is_nifty_sharp = abs(nifty_return) >= 1.25
    # Small residual: residual is within 2.5% or less than 45% of total stock return, and direction aligns
    is_nifty_resid_small = abs(residual_nifty) <= max(2.5, 0.45 * abs(stock_return)) and (stock_return * nifty_return > 0)

    # Sector sharp move: absolute return >= 1.75%
    is_sec_sharp = abs(sec_ret) >= 1.75
    is_sec_resid_small = abs(residual_sector) <= max(2.5, 0.45 * abs(stock_return)) and (stock_return * sec_ret > 0)

    if is_nifty_sharp and is_nifty_resid_small:
        classification = "Market-wide move"
        explanation_factor = (
            f"NIFTY 50 moved {nifty_return:+.2f}% on this session. "
            f"The stock's residual move was {residual_nifty:+.2f}% vs market, indicating this was primarily a market-wide trend."
        )
    elif is_sec_sharp and is_sec_resid_small:
        classification = "Sector-wide move"
        explanation_factor = (
            f"{sector_name} moved {sec_ret:+.2f}% on this session. "
            f"The stock's residual move was {residual_sector:+.2f}% vs sector, indicating a sector-wide movement."
        )
    else:
        classification = "Company-specific move"
        explanation_factor = (
            f"Stock moved {stock_return:+.2f}% with a residual move of {residual_nifty:+.2f}% vs NIFTY ({nifty_return:+.2f}%), "
            f"indicating the price was driven by company-specific catalysts."
        )

    return {
        "stock_return_pct": round(float(stock_return), 2),
        "nifty_return_pct": round(float(nifty_return), 2),
        "sector_return_pct": round(float(sec_ret), 2) if sector_return is not None else None,
        "residual_pct": round(float(residual_nifty), 2),
        "classification": classification,
        "sector_name": sector_name,
        "explanation_factor": explanation_factor
    }

async def analyze_market_context_for_events(
    stock_df: pd.DataFrame,
    events: list[Dict[str, Any]],
    sector_str: Optional[str] = None
) -> list[Dict[str, Any]]:
    """
    Enriches each event with exact market context (Stock return, NIFTY 50, Sector index, Residual, and Classification).
    """
    if not events:
        return events

    # Fetch NIFTY 50 and Sector benchmarks in parallel
    sec_ticker, sec_label = get_sector_benchmark(sector_str)
    
    nifty_df_task = fetch_benchmark_series("^NSEI")
    sec_df_task = fetch_benchmark_series(sec_ticker) if sec_ticker != "^NSEI" else asyncio.sleep(0, result=pd.DataFrame())

    nifty_df, sec_df = await asyncio.gather(nifty_df_task, sec_df_task)

    clean_stock = _normalize_df(stock_df)
    clean_stock["daily_ret"] = clean_stock["Adj Close"].pct_change() * 100.0

    if not nifty_df.empty:
        nifty_clean = _normalize_df(nifty_df)
        nifty_clean["nifty_ret"] = nifty_clean["Adj Close"].pct_change() * 100.0
    else:
        nifty_clean = pd.DataFrame()

    if not sec_df.empty:
        sec_clean = _normalize_df(sec_df)
        sec_clean["sec_ret"] = sec_clean["Adj Close"].pct_change() * 100.0
    else:
        sec_clean = pd.DataFrame()

    # Calculate beta vs NIFTY and Sector
    beta_nifty = 1.0
    if not nifty_clean.empty:
        m_n = pd.DataFrame({"stock": clean_stock["daily_ret"], "nifty": nifty_clean["nifty_ret"]}).dropna()
        if len(m_n) > 20:
            cov = m_n["stock"].cov(m_n["nifty"])
            var = m_n["nifty"].var()
            if var > 0:
                beta_nifty = float(cov / var)

    beta_sec = 1.0
    if not sec_clean.empty:
        m_s = pd.DataFrame({"stock": clean_stock["daily_ret"], "sec": sec_clean["sec_ret"]}).dropna()
        if len(m_s) > 20:
            cov = m_s["stock"].cov(m_s["sec"])
            var = m_s["sec"].var()
            if var > 0:
                beta_sec = float(cov / var)

    enriched_events = []
    for ev in events:
        start_dt = pd.to_datetime(ev["start_date"])
        end_dt = pd.to_datetime(ev["end_date"])
        
        # Stock return for this event
        stock_ret = ev["change_pct"]

        # Calculate NIFTY return over the event window
        nifty_ret = 0.0
        if not nifty_clean.empty:
            window_nifty = nifty_clean.loc[(nifty_clean.index >= start_dt) & (nifty_clean.index <= end_dt)]
            if not window_nifty.empty and len(window_nifty) > 0:
                # Cumulative return of nifty in window
                n_start = window_nifty["Adj Close"].iloc[0]
                n_end = window_nifty["Adj Close"].iloc[-1]
                idx_prev = max(0, nifty_clean.index.get_loc(window_nifty.index[0]) - 1)
                n_base = nifty_clean["Adj Close"].iloc[idx_prev]
                if n_base > 0:
                    nifty_ret = ((n_end - n_base) / n_base) * 100.0
                elif len(window_nifty) == 1 and "nifty_ret" in window_nifty.columns:
                    nifty_ret = float(window_nifty["nifty_ret"].iloc[0])

        # Calculate Sector return over the event window
        sec_ret = None
        if not sec_clean.empty:
            window_sec = sec_clean.loc[(sec_clean.index >= start_dt) & (sec_clean.index <= end_dt)]
            if not window_sec.empty and len(window_sec) > 0:
                s_end = window_sec["Adj Close"].iloc[-1]
                idx_prev = max(0, sec_clean.index.get_loc(window_sec.index[0]) - 1)
                s_base = sec_clean["Adj Close"].iloc[idx_prev]
                if s_base > 0:
                    sec_ret = ((s_end - s_base) / s_base) * 100.0
                elif len(window_sec) == 1 and "sec_ret" in window_sec.columns:
                    sec_ret = float(window_sec["sec_ret"].iloc[0])

        # Classify
        context = classify_event_market_level(
            stock_return=stock_ret,
            nifty_return=nifty_ret,
            sector_return=sec_ret,
            beta_nifty=beta_nifty,
            beta_sector=beta_sec,
            sector_name=sec_label
        )

        ev_copy = dict(ev)
        ev_copy["market_context"] = context
        enriched_events.append(ev_copy)

    return enriched_events
