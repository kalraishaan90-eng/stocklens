"""
analytics.py — Dual Stock Quantitative Analytics, Moving Average Modeling & Financial Metrics Engine.

Mirrors the senior school science exhibition project methodology:
1. Builds monthly time-series by sampling the LAST adjusted close of each calendar month.
2. Aligns both target companies on identical calendar months.
3. Computes 3-Month and 6-Month rolling Simple Moving Averages (SMA).
4. Generates output table matching the exact project template shape:
   Month-Year | Company1 Close | Company1 MA | Company2 Close | Company2 MA
5. Calculates multi-dimensional performance, volatility, drawdown, and momentum metrics.
6. Computes 0-100 Stability and Growth Scores using configurable weights.
7. Generates deterministic, plain-English comparative sentences without generative hallucination.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional, Union

from app.config import (
    RISK_FREE_RATE_PCT,
    STABILITY_WEIGHTS,
    GROWTH_WEIGHTS
)
from app.models.schemas import (
    MonthlyPricePoint,
    DailyPricePoint,
    PerformanceMetrics,
    OverlayPoint,
    ProjectTemplateTableRow,
    MonthlyTableRow,
    MovingAverageRow,
    DayReturnPoint,
    MonthReturnPoint,
    MetricComparisonItem,
    ComparisonObject
)

# ---------------------------------------------------------------------------
# Section A & B: Monthly Resampling, Alignment & Moving Averages
# ---------------------------------------------------------------------------

def _extract_monthly_last_closes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts the last trading day's adjusted closing price for each calendar month.
    Mirrors Excel formula: TEXT(Date, "YYYY-MM") + last closing price in that group.

    Parameters:
        df: pd.DataFrame with 'Adj Close' (or 'Close') and a DatetimeIndex or 'Date' column.

    Returns:
        pd.DataFrame sorted chronologically with columns:
        ['month_year', 'date', 'month_label', 'adj_close']
    """
    if df.empty:
        return pd.DataFrame(columns=["month_year", "date", "month_label", "adj_close"])

    df_copy = df.copy()
    if not isinstance(df_copy.index, pd.DatetimeIndex):
        if "Date" in df_copy.columns:
            df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            df_copy.set_index("Date", inplace=True)
        else:
            df_copy.index = pd.to_datetime(df_copy.index)

    df_copy.sort_index(inplace=True)
    price_col = "Adj Close" if "Adj Close" in df_copy.columns else "Close"
    if price_col not in df_copy.columns:
        return pd.DataFrame(columns=["month_year", "date", "month_label", "adj_close"])
    df_copy = df_copy.loc[pd.to_numeric(df_copy[price_col], errors="coerce").notna()]
    if df_copy.empty:
        return pd.DataFrame(columns=["month_year", "date", "month_label", "adj_close"])

    # Assign month-year identifier (YYYY-MM)
    df_copy["month_year"] = df_copy.index.strftime("%Y-%m")

    # Group by month_year and take the very last trading session of that month
    records = []
    for month_key, group in df_copy.groupby("month_year", sort=True):
        last_row = group.iloc[-1]
        last_dt = group.index[-1]
        records.append({
            "month_year": month_key,
            "date": last_dt.strftime("%Y-%m-%d"),
            "month_label": last_dt.strftime("%b %Y"),
            "adj_close": float(round(last_row[price_col], 2))
        })

    return pd.DataFrame(records)


def compute_monthly_series(df: pd.DataFrame) -> List[MonthlyPricePoint]:
    """
    Computes monthly closing prices and 3-month/6-month rolling moving averages for a single stock.

    Plain-English Meaning:
        Instead of daily fluctuations which contain noisy market chatter, taking the final
        closing price of each month provides a clear month-by-month financial snapshot.
        The 3-month moving average (MA-3M) averages the current month and preceding two months,
        smoothing out short-term price spikes and identifying medium-term trends.
        The first two months are null because a 3-month lookback window requires 3 full data points.
    """
    if df.empty:
        return []

    monthly_df = _extract_monthly_last_closes(df)
    if monthly_df.empty:
        return []

    closes = monthly_df["adj_close"].values
    n = len(closes)

    # Compute 3-Month Moving Average: =AVERAGE(B2:B4) dragged down; first two months null
    ma_3m = [None] * n
    for i in range(2, n):
        ma_3m[i] = round(float(np.mean(closes[i-2 : i+1])), 2)

    # Compute 6-Month Moving Average (optional extra lookback)
    ma_6m = [None] * n
    for i in range(5, n):
        ma_6m[i] = round(float(np.mean(closes[i-5 : i+1])), 2)

    points: List[MonthlyPricePoint] = []
    for i, row in monthly_df.iterrows():
        points.append(
            MonthlyPricePoint(
                date=row["date"],
                month_label=row["month_label"],
                month_year=row["month_year"],
                adj_close=float(row["adj_close"]),
                ma_3m=ma_3m[i],
                ma_6m=ma_6m[i]
            )
        )
    return points


def build_monthly_table(
    df1: pd.DataFrame,
    df2: pd.DataFrame
) -> Tuple[List[MonthlyPricePoint], List[MonthlyPricePoint], List[ProjectTemplateTableRow]]:
    """
    Builds aligned monthly summaries and moving averages for both companies over identical calendar months.

    Steps:
      1. Extracts month-end adjusted close for each company (TEXT(Date, 'YYYY-MM') + last close).
      2. Aligns both companies on the exact intersection of available calendar months.
      3. Computes 3-month moving average (=AVERAGE(B2:B4) dragged down) where first 2 months are null.
      4. Computes 6-month moving average as an optional extra.
      5. Formats output table in the exact project template shape:
         Month-Year | Company1 Close | Company1 MA | Company2 Close | Company2 MA.

    Returns:
        (monthly_pts_company1, monthly_pts_company2, project_template_rows)
    """
    m1 = _extract_monthly_last_closes(df1)
    m2 = _extract_monthly_last_closes(df2)

    if m1.empty or m2.empty:
        return [], [], []

    # Align on common calendar months (intersection) sorted chronologically
    common_months = sorted(list(set(m1["month_year"]).intersection(set(m2["month_year"]))))
    if not common_months:
        return [], [], []

    m1_aligned = m1[m1["month_year"].isin(common_months)].sort_values("month_year").reset_index(drop=True)
    m2_aligned = m2[m2["month_year"].isin(common_months)].sort_values("month_year").reset_index(drop=True)

    n = len(common_months)
    c1_closes = m1_aligned["adj_close"].values
    c2_closes = m2_aligned["adj_close"].values

    # 3-Month Moving Average: first two months null
    c1_ma3 = [None] * n
    c2_ma3 = [None] * n
    for i in range(2, n):
        c1_ma3[i] = round(float(np.mean(c1_closes[i-2 : i+1])), 2)
        c2_ma3[i] = round(float(np.mean(c2_closes[i-2 : i+1])), 2)

    # 6-Month Moving Average: first five months null
    c1_ma6 = [None] * n
    c2_ma6 = [None] * n
    for i in range(5, n):
        c1_ma6[i] = round(float(np.mean(c1_closes[i-5 : i+1])), 2)
        c2_ma6[i] = round(float(np.mean(c2_closes[i-5 : i+1])), 2)

    pts1: List[MonthlyPricePoint] = []
    pts2: List[MonthlyPricePoint] = []
    template_rows: List[ProjectTemplateTableRow] = []

    for i in range(n):
        my = common_months[i]
        r1 = m1_aligned.iloc[i]
        r2 = m2_aligned.iloc[i]

        p1 = MonthlyPricePoint(
            date=r1["date"],
            month_label=r1["month_label"],
            month_year=my,
            adj_close=float(c1_closes[i]),
            ma_3m=c1_ma3[i],
            ma_6m=c1_ma6[i]
        )
        p2 = MonthlyPricePoint(
            date=r2["date"],
            month_label=r2["month_label"],
            month_year=my,
            adj_close=float(c2_closes[i]),
            ma_3m=c2_ma3[i],
            ma_6m=c2_ma6[i]
        )
        pts1.append(p1)
        pts2.append(p2)

        # Exact project template row:
        # Month-Year | Company1 Close | Company1 MA | Company2 Close | Company2 MA
        template_rows.append(
            ProjectTemplateTableRow(
                month_year=my,
                company1_close=float(c1_closes[i]),
                company1_ma=c1_ma3[i],
                company2_close=float(c2_closes[i]),
                company2_ma=c2_ma3[i],
                company1_ma_6m=c1_ma6[i],
                company2_ma_6m=c2_ma6[i]
            )
        )

    return pts1, pts2, template_rows


# ---------------------------------------------------------------------------
# Section C: Daily Moving Averages & Trend Signals (50-DMA, 200-DMA, RSI)
# ---------------------------------------------------------------------------

def compute_daily_mas(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes daily 50-day and 200-day Simple Moving Averages (DMA) and compares
    the latest closing price against them.

    Plain-English Meaning:
        - 50-DMA (50-Day Moving Average): Reflects intermediate momentum (~10 trading weeks).
          When price trades above 50-DMA, short-to-medium term sentiment is bullish.
        - 200-DMA (200-Day Moving Average): The gold standard long-term trend baseline (~40 trading weeks).
          Trading comfortably above 200-DMA confirms a long-term structural uptrend.
    """
    price_col = "Adj Close" if "Adj Close" in df.columns else "Close"
    empty_result = {
        "dma_50": None, "price_vs_50_dma_status": None, "price_vs_50_dma_pct": None,
        "dma_200": None, "price_vs_200_dma_status": None, "price_vs_200_dma_pct": None,
    }
    if df.empty or price_col not in df.columns:
        return empty_result

    ordered = df.copy()
    if "Date" in ordered.columns and not isinstance(ordered.index, pd.DatetimeIndex):
        ordered["Date"] = pd.to_datetime(ordered["Date"])
        ordered.set_index("Date", inplace=True)
    ordered.sort_index(inplace=True)
    prices = pd.to_numeric(ordered[price_col], errors="coerce").dropna()

    if len(prices) == 0:
        return empty_result

    latest_price = float(prices.iloc[-1])

    # 50-day MA
    dma_50_val: Optional[float] = None
    status_50: Optional[str] = None
    dist_50: Optional[float] = None
    if len(prices) >= 50:
        s50 = prices.rolling(window=50, min_periods=50).mean()
        val = s50.iloc[-1]
        if pd.notna(val) and val > 0:
            dma_50_val = round(float(val), 2)
            status_50 = "ABOVE" if latest_price >= dma_50_val else "BELOW"
            dist_50 = round(((latest_price - dma_50_val) / dma_50_val) * 100.0, 2)

    # 200-day MA
    dma_200_val: Optional[float] = None
    status_200: Optional[str] = None
    dist_200: Optional[float] = None
    if len(prices) >= 200:
        s200 = prices.rolling(window=200, min_periods=200).mean()
        val2 = s200.iloc[-1]
        if pd.notna(val2) and val2 > 0:
            dma_200_val = round(float(val2), 2)
            status_200 = "ABOVE" if latest_price >= dma_200_val else "BELOW"
            dist_200 = round(((latest_price - dma_200_val) / dma_200_val) * 100.0, 2)

    return {
        "dma_50": dma_50_val,
        "price_vs_50_dma_status": status_50,
        "price_vs_50_dma_pct": dist_50,
        "dma_200": dma_200_val,
        "price_vs_200_dma_status": status_200,
        "price_vs_200_dma_pct": dist_200,
    }


def compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """
    Computes the standard 14-period Relative Strength Index (RSI).

    Plain-English Meaning:
        The Relative Strength Index (RSI) is an oscillator scaled from 0 to 100 that
        measures the speed and velocity of recent price changes.
        - RSI > 70: Overbought territory; stock has surged strongly and may be due for consolidation.
        - RSI < 30: Oversold territory; stock has experienced heavy selling and may offer support.
        - RSI 40-60: Neutral equilibrium.
    """
    clean_prices = prices.dropna()
    if len(clean_prices) < period + 1:
        return 50.0

    deltas = clean_prices.diff().dropna()
    gains = deltas.clip(lower=0)
    losses = -deltas.clip(upper=0)

    # Wilder's exponential smoothing
    avg_gain = gains.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(np.clip(rsi, 0.0, 100.0)), 2)


def compute_beta(stock_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Computes Beta coefficient vs NIFTY 50 benchmark index.

    Plain-English Meaning:
        Beta quantifies systematic market risk.
        - Beta = 1.0: Stock moves in lockstep with the broader market.
        - Beta > 1.0: Higher volatility than the market (aggressive growth / cyclical).
        - Beta < 1.0: Lower volatility than the market (defensive / capital preservation).
        - Formula: Covariance(Stock Returns, NIFTY Returns) / Variance(NIFTY Returns).
    """
    combined = pd.DataFrame({"stock": stock_returns, "bench": benchmark_returns}).dropna()
    if len(combined) < 20:
        return 1.0

    var_bench = combined["bench"].var()
    if var_bench == 0 or np.isnan(var_bench):
        return 1.0

    cov = combined["stock"].cov(combined["bench"])
    beta = cov / var_bench
    if np.isnan(beta):
        return 1.0

    return round(float(beta), 2)


def compute_max_drawdown_details(prices: pd.Series) -> Tuple[float, str, str, Optional[str]]:
    """
    Computes Maximum Drawdown (MDD) along with its start (peak) and end (trough) dates.

    Plain-English Meaning:
        Maximum Drawdown represents the deepest percentage loss an investor would have endured
        if buying at the worst possible peak and selling at the lowest subsequent bottom.
        Start Date = Date when the all-time peak was set before the fall.
        End Date = Date of the lowest trough bottom before recovery.
    """
    if len(prices) < 2:
        return 0.0, "", "", None

    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax

    min_dd_idx = drawdown.idxmin()
    min_dd_val = float(drawdown.loc[min_dd_idx])
    max_dd_pct = round(abs(min_dd_val) * 100.0, 2)

    # Find the peak that preceded this trough
    prices_prior = prices.loc[:min_dd_idx]
    peak_idx = prices_prior.idxmax()

    # Find recovery date if price surpassed peak_price afterwards
    peak_price = prices.loc[peak_idx]
    prices_after = prices.loc[min_dd_idx:].iloc[1:]
    recovered = prices_after[prices_after >= peak_price]
    recovery_idx = recovered.index[0] if not recovered.empty else None
    recovery_date_str = (
        recovery_idx.strftime("%Y-%m-%d") if hasattr(recovery_idx, "strftime")
        else str(recovery_idx) if recovery_idx is not None
        else None
    )

    peak_date_str = peak_idx.strftime("%Y-%m-%d") if hasattr(peak_idx, "strftime") else str(peak_idx)
    trough_date_str = min_dd_idx.strftime("%Y-%m-%d") if hasattr(min_dd_idx, "strftime") else str(min_dd_idx)

    return max_dd_pct, peak_date_str, trough_date_str, recovery_date_str


# ---------------------------------------------------------------------------
# Section D: Comprehensive Performance Metrics
# ---------------------------------------------------------------------------

def compute_performance_metrics(
    df: pd.DataFrame,
    benchmark_df: Optional[pd.DataFrame] = None,
    risk_free_rate_pct: float = RISK_FREE_RATE_PCT
) -> PerformanceMetrics:
    """
    Computes all school exhibition financial metrics for a single stock.

    All metrics are fully documented below with their mathematical formulation
    and plain-English interpretation:

    1. Total Return (%):
       Total percentage price appreciation from start of period to end: ((P_end - P_start) / P_start) * 100.
    2. CAGR (Compound Annual Growth Rate, %):
       The steady annual compounding growth rate equivalent: (P_end / P_start) ** (365.25 / days) - 1.
    3. Annualized Volatility (%):
       StdDev(Daily Returns) * sqrt(252). Reflects annual price swing uncertainty.
    4. Monthly Return StdDev (%):
       Standard deviation of month-over-month percentage changes from monthly closing prices.
    5. Max Drawdown (% + dates):
       Steepest peak-to-trough price collapse, including peak date and trough date.
    6. Sharpe-Style Ratio:
       (CAGR - Risk Free Rate) / Annualized Volatility. Measures excess return per unit of total risk.
    7. Best & Worst Day:
       The single highest and lowest daily percentage change sessions.
    8. Best & Worst Month:
       The single highest and lowest calendar month percentage return.
    9. Beta vs NIFTY 50:
       Sensitivity of the stock's returns to broad market swings.
    10. RSI(14):
        14-period momentum oscillator (0-100) indicating overbought (>70) or oversold (<30) condition.
    11. Price vs 50-DMA and 200-DMA:
        Percentage distance and ABOVE/BELOW status relative to medium and long-term moving averages.
    12. 3-Month MA Slope & 3-Month Momentum:
        Direction of 3-month moving average ('RISING', 'FALLING', 'FLAT') and trailing 3-month % return.
    13. Coefficient of Variation (CV, %):
        StdDev(Monthly Closes) / Mean(Monthly Closes) * 100. Normalized dispersion of price levels.
    14. Trend Consistency (%):
        Percentage of completed months where closing price was above its 3-month moving average.
    15. Stability Score & Growth Score:
        0-100 quantitative composite scores combining stability and expansion dimensions.
    """
    price_col = "Adj Close" if "Adj Close" in df.columns else "Close"
    sorted_df = df.copy()
    if not isinstance(sorted_df.index, pd.DatetimeIndex):
        if "Date" in sorted_df.columns:
            sorted_df["Date"] = pd.to_datetime(sorted_df["Date"])
            sorted_df.set_index("Date", inplace=True)
        else:
            sorted_df.index = pd.to_datetime(sorted_df.index)
    sorted_df.sort_index(inplace=True)

    prices = sorted_df[price_col].dropna()
    if len(prices) < 2:
        return PerformanceMetrics(
            current_price=0.0,
            cagr_pct=0.0,
            annualized_volatility_pct=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            high_52w=0.0,
            low_52w=0.0,
            total_return_pct=0.0,
            positive_days_pct=0.0
        )

    start_price = float(prices.iloc[0])
    current_price = float(prices.iloc[-1])

    # 1. Total Return & Calendar Duration
    total_return_pct = round(((current_price - start_price) / start_price) * 100.0, 2)
    start_dt = prices.index[0]
    end_dt = prices.index[-1]
    total_days = max((end_dt - start_dt).days, 1)
    years = total_days / 365.25

    # 2. CAGR
    if start_price > 0 and current_price > 0 and years > 0:
        cagr = round((((current_price / start_price) ** (1.0 / years)) - 1.0) * 100.0, 2)
    else:
        cagr = 0.0

    # 3. Daily Returns, Annualized Volatility & Best/Worst Day
    daily_returns = prices.pct_change().dropna()
    if len(daily_returns) > 1:
        daily_vol = float(daily_returns.std(ddof=1))
        annualized_volatility_pct = round(daily_vol * np.sqrt(252) * 100.0, 2)
        positive_days_pct = round(float((daily_returns > 0).mean() * 100.0), 2)

        best_day_idx = daily_returns.idxmax()
        worst_day_idx = daily_returns.idxmin()
        best_day = DayReturnPoint(
            date=best_day_idx.strftime("%Y-%m-%d"),
            return_pct=round(float(daily_returns.loc[best_day_idx]) * 100.0, 2)
        )
        worst_day = DayReturnPoint(
            date=worst_day_idx.strftime("%Y-%m-%d"),
            return_pct=round(float(daily_returns.loc[worst_day_idx]) * 100.0, 2)
        )
    else:
        annualized_volatility_pct = 0.0
        positive_days_pct = 50.0
        best_day = None
        worst_day = None

    # 4. Maximum Drawdown with peak and trough dates
    max_dd_pct, peak_dt, trough_dt, rec_dt = compute_max_drawdown_details(prices)

    # 5. Sharpe Ratio
    if annualized_volatility_pct > 0.01:
        sharpe_ratio = round((cagr - risk_free_rate_pct) / annualized_volatility_pct, 2)
    else:
        sharpe_ratio = 0.0

    # 6. 52-Week High / Low
    last_year_prices = prices.iloc[-min(len(prices), 252):]
    high_52w = round(float(last_year_prices.max()), 2)
    low_52w = round(float(last_year_prices.min()), 2)

    # 7. Monthly Resampling Metrics (Monthly Return StdDev, Best/Worst Month, CV, Trend Consistency)
    monthly_df = _extract_monthly_last_closes(sorted_df)
    monthly_closes = monthly_df["adj_close"].values if not monthly_df.empty else np.array([])

    if len(monthly_closes) >= 2:
        monthly_series = pd.Series(monthly_closes, index=monthly_df["month_year"])
        monthly_ret = monthly_series.pct_change().dropna()

        monthly_return_std_pct = round(float(monthly_ret.std(ddof=1) * 100.0), 2)
        best_m_key = monthly_ret.idxmax()
        worst_m_key = monthly_ret.idxmin()
        best_month = MonthReturnPoint(month=best_m_key, return_pct=round(float(monthly_ret.loc[best_m_key]) * 100.0, 2))
        worst_month = MonthReturnPoint(month=worst_m_key, return_pct=round(float(monthly_ret.loc[worst_m_key]) * 100.0, 2))

        # Coefficient of variation of monthly closes
        mean_monthly = float(np.mean(monthly_closes))
        std_monthly = float(np.std(monthly_closes, ddof=1))
        cv_monthly = round((std_monthly / mean_monthly) * 100.0, 2) if mean_monthly > 0 else 0.0

        # Trend Consistency: % of months where close was above its 3-month MA
        n_m = len(monthly_closes)
        ma_3m_vals = [None] * n_m
        above_count = 0
        valid_ma_count = 0
        for i in range(2, n_m):
            avg3 = np.mean(monthly_closes[i-2 : i+1])
            ma_3m_vals[i] = avg3
            valid_ma_count += 1
            if monthly_closes[i] > avg3:
                above_count += 1

        trend_consistency_pct = round((above_count / valid_ma_count) * 100.0, 2) if valid_ma_count > 0 else 50.0

        # 3-Month MA Slope: comparing latest 3M MA to previous month's 3M MA
        if n_m >= 4 and ma_3m_vals[-1] is not None and ma_3m_vals[-2] is not None:
            latest_ma = ma_3m_vals[-1]
            prev_ma = ma_3m_vals[-2]
            slope_change_pct = ((latest_ma - prev_ma) / prev_ma) * 100.0
            if slope_change_pct > 0.5:
                ma_3m_slope = "RISING"
            elif slope_change_pct < -0.5:
                ma_3m_slope = "FALLING"
            else:
                ma_3m_slope = "FLAT"
        else:
            ma_3m_slope = "FLAT"

        # Trailing 3 months momentum (% change over last 3 completed months)
        if n_m >= 4 and monthly_closes[-4] > 0:
            momentum_3m_pct = round(((monthly_closes[-1] - monthly_closes[-4]) / monthly_closes[-4]) * 100.0, 2)
        elif n_m >= 2 and monthly_closes[0] > 0:
            momentum_3m_pct = round(((monthly_closes[-1] - monthly_closes[0]) / monthly_closes[0]) * 100.0, 2)
        else:
            momentum_3m_pct = 0.0
    else:
        monthly_return_std_pct = 0.0
        best_month = None
        worst_month = None
        cv_monthly = 0.0
        trend_consistency_pct = 50.0
        ma_3m_slope = "FLAT"
        momentum_3m_pct = 0.0

    # 8. Beta vs NIFTY 50
    if benchmark_df is not None and not benchmark_df.empty:
        bench_col = "Adj Close" if "Adj Close" in benchmark_df.columns else "Close"
        bench_returns = benchmark_df[bench_col].pct_change().dropna()
        beta_nifty = compute_beta(daily_returns, bench_returns)
    else:
        beta_nifty = 1.0

    # 9. RSI(14)
    rsi_14 = compute_rsi(prices, period=14)

    # 10. Price vs 50-DMA and 200-DMA
    dma_signals = compute_daily_mas(sorted_df)

    # 11. Stability Score & Growth Score
    stability_score = compute_stability_score(
        annualized_volatility=annualized_volatility_pct,
        max_drawdown=max_dd_pct,
        trend_consistency_pct=trend_consistency_pct
    )
    growth_score = compute_growth_score(
        cagr=cagr,
        momentum_3m=momentum_3m_pct,
        price_vs_50_dma_pct=dma_signals["price_vs_50_dma_pct"] or 0.0,
        ma_3m_slope=ma_3m_slope
    )

    return PerformanceMetrics(
        current_price=round(current_price, 2),
        cagr_pct=cagr,
        annualized_volatility_pct=annualized_volatility_pct,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe_ratio,
        high_52w=high_52w,
        low_52w=low_52w,
        total_return_pct=total_return_pct,
        positive_days_pct=positive_days_pct,
        monthly_return_std_pct=monthly_return_std_pct,
        drawdown_peak_date=peak_dt,
        drawdown_trough_date=trough_dt,
        drawdown_recovery_date=rec_dt,
        best_day=best_day,
        worst_day=worst_day,
        best_month=best_month,
        worst_month=worst_month,
        beta_nifty=beta_nifty,
        rsi_14=rsi_14,
        dma_50=dma_signals["dma_50"],
        price_vs_50_dma_status=dma_signals["price_vs_50_dma_status"],
        price_vs_50_dma_pct=dma_signals["price_vs_50_dma_pct"],
        dma_200=dma_signals["dma_200"],
        price_vs_200_dma_status=dma_signals["price_vs_200_dma_status"],
        price_vs_200_dma_pct=dma_signals["price_vs_200_dma_pct"],
        ma_3m_slope=ma_3m_slope,
        momentum_3m_pct=momentum_3m_pct,
        coefficient_of_variation_monthly=cv_monthly,
        trend_consistency_pct=trend_consistency_pct,
        stability_score=stability_score,
        growth_score=growth_score
    )


# ---------------------------------------------------------------------------
# Section E & F: Stability Ranking & Growth Score (0 to 100)
# ---------------------------------------------------------------------------

def compute_stability_score(
    annualized_volatility: float,
    max_drawdown: float,
    trend_consistency_pct: float,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes a 0-100 Stability Score combining volatility, drawdown, and consistency.
    Higher = more stable.

    Weights (documented in config.py):
      - Volatility: 40% (calmer is better; 15% vol maps to 100 pts, 55%+ maps to 0 pts)
      - Max Drawdown: 35% (shallower is better; 10% drawdown maps to 100 pts, 50%+ maps to 0 pts)
      - Consistency: 25% (% of months above 3M MA, already 0-100 scale)
    """
    if weights is None:
        weights = STABILITY_WEIGHTS

    w_vol = weights.get("volatility", 0.40)
    w_dd = weights.get("drawdown", 0.35)
    w_cons = weights.get("consistency", 0.25)

    # Volatility score: <= 15% is stellar (100 pts), >= 55% is high risk (0 pts)
    vol_pts = float(np.clip(100.0 - ((annualized_volatility - 15.0) / 40.0) * 100.0, 0.0, 100.0))

    # Drawdown score: <= 10% is stellar (100 pts), >= 50% is severe (0 pts)
    dd_pts = float(np.clip(100.0 - ((max_drawdown - 10.0) / 40.0) * 100.0, 0.0, 100.0))

    # Consistency score: 0 to 100 directly
    cons_pts = float(np.clip(trend_consistency_pct, 0.0, 100.0))

    score = w_vol * vol_pts + w_dd * dd_pts + w_cons * cons_pts
    return round(float(np.clip(score, 0.0, 100.0)), 1)


def compute_growth_score(
    cagr: float,
    momentum_3m: float,
    price_vs_50_dma_pct: float,
    ma_3m_slope: str,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes a 0-100 Growth Score combining CAGR, trailing 3-month momentum, and trend signals.
    Higher = stronger compounding and expansion velocity.

    Weights (documented in config.py):
      - CAGR: 45% (0% CAGR maps to 20 pts, 50%+ CAGR maps to 100 pts)
      - Momentum: 30% (-15% to +25% trailing 3M return maps to 0-100)
      - Trend: 25% (Position vs 50-DMA and 3-month MA slope)
    """
    if weights is None:
        weights = GROWTH_WEIGHTS

    w_cagr = weights.get("cagr", 0.45)
    w_mom = weights.get("momentum", 0.30)
    w_trend = weights.get("trend", 0.25)

    # CAGR score: 0% maps to 20 pts, 50% maps to 100 pts, negative maps to max(0, 20 + cagr)
    if cagr >= 0.0:
        cagr_pts = float(np.clip(20.0 + (cagr / 50.0) * 80.0, 0.0, 100.0))
    else:
        cagr_pts = float(max(0.0, 20.0 + cagr))

    # Momentum score: -15% maps to 0 pts, +25% maps to 100 pts
    mom_pts = float(np.clip(((momentum_3m - (-15.0)) / 40.0) * 100.0, 0.0, 100.0))

    # Trend score:
    # 50-DMA position contributes 50 base pts if above, plus distance bonus
    trend_base = 50.0 if price_vs_50_dma_pct >= 0.0 else 20.0
    dist_bonus = float(np.clip(price_vs_50_dma_pct * 2.0, -20.0, 20.0))
    slope_bonus = 25.0 if ma_3m_slope == "RISING" else (10.0 if ma_3m_slope == "FLAT" else 0.0)
    trend_pts = float(np.clip(trend_base + dist_bonus + slope_bonus, 0.0, 100.0))

    score = w_cagr * cagr_pts + w_mom * mom_pts + w_trend * trend_pts
    return round(float(np.clip(score, 0.0, 100.0)), 1)


# ---------------------------------------------------------------------------
# Section G: Comparison Object & Programmatic Plain-English Sentences
# ---------------------------------------------------------------------------

def build_comparison_object(
    comp1_name: str,
    comp1_ticker: str,
    m1: PerformanceMetrics,
    comp2_name: str,
    comp2_ticker: str,
    m2: PerformanceMetrics
) -> ComparisonObject:
    """
    Creates a comprehensive metric-by-metric comparison object showing who wins each dimension,
    and programmatically generates 5-8 plain-English comparison sentences without AI hallucination.
    """
    items: List[MetricComparisonItem] = []

    def _add_metric(key, display, v1, v2, higher_is_better=True, is_pct=True, preferred_target=None):
        if v1 is None or v2 is None:
            items.append(MetricComparisonItem(
                metric_key=key,
                display_name=display,
                company1_val=v1,
                company2_val=v2,
                winner_ticker=None,
                winner_name=None,
                advantage_pct=0.0,
                advantage_description="Not available for both companies"
            ))
            return
        compare_v1 = abs(v1 - preferred_target) if preferred_target is not None else v1
        compare_v2 = abs(v2 - preferred_target) if preferred_target is not None else v2
        if preferred_target is not None:
            winner_t = comp1_ticker if compare_v1 < compare_v2 else (comp2_ticker if compare_v2 < compare_v1 else None)
            winner_n = comp1_name if compare_v1 < compare_v2 else (comp2_name if compare_v2 < compare_v1 else None)
        elif higher_is_better:
            winner_t = comp1_ticker if compare_v1 > compare_v2 else (comp2_ticker if compare_v2 > compare_v1 else None)
            winner_n = comp1_name if compare_v1 > compare_v2 else (comp2_name if compare_v2 > compare_v1 else None)
        else:
            winner_t = comp1_ticker if compare_v1 < compare_v2 else (comp2_ticker if compare_v2 < compare_v1 else None)
            winner_n = comp1_name if compare_v1 < compare_v2 else (comp2_name if compare_v2 < compare_v1 else None)

        diff_abs = round(abs(v1 - v2), 2)
        base = max(abs(v1), abs(v2))
        adv_pct = round((diff_abs / base) * 100.0, 1) if base > 0 else 0.0

        if winner_n:
            unit = "%" if is_pct else ""
            desc = f"{winner_n} leads by {diff_abs}{unit}"
        else:
            desc = "Evenly matched"

        items.append(
            MetricComparisonItem(
                metric_key=key,
                display_name=display,
                company1_val=v1,
                company2_val=v2,
                winner_ticker=winner_t,
                winner_name=winner_n,
                advantage_pct=adv_pct,
                advantage_description=desc
            )
        )

    # Core metrics comparison
    _add_metric("cagr_pct", "Compound Annual Growth Rate (CAGR)", m1.cagr_pct, m2.cagr_pct, higher_is_better=True)
    _add_metric("total_return_pct", "2-Year Total Return", m1.total_return_pct, m2.total_return_pct, higher_is_better=True)
    _add_metric("annualized_volatility_pct", "Annualized Volatility (Risk)", m1.annualized_volatility_pct, m2.annualized_volatility_pct, higher_is_better=False)
    _add_metric("max_drawdown_pct", "Maximum Drawdown", m1.max_drawdown_pct, m2.max_drawdown_pct, higher_is_better=False)
    _add_metric("sharpe_ratio", "Sharpe Ratio (Risk-Adjusted Return)", m1.sharpe_ratio, m2.sharpe_ratio, higher_is_better=True, is_pct=False)
    _add_metric("stability_score", "Stability Score (0-100)", m1.stability_score, m2.stability_score, higher_is_better=True, is_pct=False)
    _add_metric("growth_score", "Growth Score (0-100)", m1.growth_score, m2.growth_score, higher_is_better=True, is_pct=False)
    _add_metric("trend_consistency_pct", "Trend Consistency (% Months Above 3M MA)", m1.trend_consistency_pct, m2.trend_consistency_pct, higher_is_better=True)
    _add_metric("momentum_3m_pct", "Trailing 3-Month Momentum", m1.momentum_3m_pct, m2.momentum_3m_pct, higher_is_better=True)
    _add_metric("monthly_return_std_pct", "Monthly Return Standard Deviation", m1.monthly_return_std_pct, m2.monthly_return_std_pct, higher_is_better=False)
    _add_metric("coefficient_of_variation_monthly", "Monthly Price CV (Stability)", m1.coefficient_of_variation_monthly, m2.coefficient_of_variation_monthly, higher_is_better=False)
    _add_metric("best_day_return_pct", "Best Daily Return", m1.best_day.return_pct if m1.best_day else None, m2.best_day.return_pct if m2.best_day else None, higher_is_better=True)
    _add_metric("worst_day_return_pct", "Worst Daily Return", m1.worst_day.return_pct if m1.worst_day else None, m2.worst_day.return_pct if m2.worst_day else None, higher_is_better=True)
    _add_metric("best_month_return_pct", "Best Monthly Return", m1.best_month.return_pct if m1.best_month else None, m2.best_month.return_pct if m2.best_month else None, higher_is_better=True)
    _add_metric("worst_month_return_pct", "Worst Monthly Return", m1.worst_month.return_pct if m1.worst_month else None, m2.worst_month.return_pct if m2.worst_month else None, higher_is_better=True)
    _add_metric("beta_nifty", "Beta vs NIFTY 50 (Lower Exposure)", abs(m1.beta_nifty) if m1.beta_nifty is not None else None, abs(m2.beta_nifty) if m2.beta_nifty is not None else None, higher_is_better=False, is_pct=False)
    _add_metric("price_vs_50_dma_pct", "Price Distance from 50-DMA", m1.price_vs_50_dma_pct, m2.price_vs_50_dma_pct, higher_is_better=True)
    _add_metric("price_vs_200_dma_pct", "Price Distance from 200-DMA", m1.price_vs_200_dma_pct, m2.price_vs_200_dma_pct, higher_is_better=True)
    _add_metric("rsi_14", "RSI(14) Distance from Neutral 50", m1.rsi_14, m2.rsi_14, is_pct=False, preferred_target=50.0)
    slope_rank = {"FALLING": 0, "FLAT": 1, "RISING": 2}
    slope_a = slope_rank.get(m1.ma_3m_slope or "")
    slope_b = slope_rank.get(m2.ma_3m_slope or "")
    if slope_a is not None and slope_b is not None:
        slope_winner_t = comp1_ticker if slope_a > slope_b else (comp2_ticker if slope_b > slope_a else None)
        slope_winner_n = comp1_name if slope_a > slope_b else (comp2_name if slope_b > slope_a else None)
        items.append(MetricComparisonItem(
            metric_key="ma_3m_slope",
            display_name="3-Month Moving Average Slope",
            company1_val=m1.ma_3m_slope,
            company2_val=m2.ma_3m_slope,
            winner_ticker=slope_winner_t,
            winner_name=slope_winner_n,
            advantage_pct=0.0,
            advantage_description=(f"{slope_winner_n} has the stronger slope" if slope_winner_n else "Evenly matched")
        ))

    # Winners
    stab_win_t = comp1_ticker if m1.stability_score >= m2.stability_score else comp2_ticker
    stab_win_n = comp1_name if m1.stability_score >= m2.stability_score else comp2_name

    growth_win_t = comp1_ticker if m1.growth_score >= m2.growth_score else comp2_ticker
    growth_win_n = comp1_name if m1.growth_score >= m2.growth_score else comp2_name

    # Overall pick combines Sharpe, Growth, and Stability
    total_pts_1 = m1.stability_score * 0.4 + m1.growth_score * 0.4 + m1.sharpe_ratio * 10.0
    total_pts_2 = m2.stability_score * 0.4 + m2.growth_score * 0.4 + m2.sharpe_ratio * 10.0
    overall_win_t = comp1_ticker if total_pts_1 >= total_pts_2 else comp2_ticker
    overall_win_n = comp1_name if total_pts_1 >= total_pts_2 else comp2_name

    # Programmatic Generation of 5-8 Plain-English Comparison Sentences
    sentences: List[str] = []

    # Sentence 1: Return & CAGR Comparison
    if m1.total_return_pct >= m2.total_return_pct:
        diff_cagr = round(m1.cagr_pct - m2.cagr_pct, 1)
        sentences.append(
            f"{comp1_name} outperformed in total price appreciation with a {m1.total_return_pct:+.1f}% gain "
            f"({m1.cagr_pct:.1f}% CAGR), surpassing {comp2_name}'s {m2.total_return_pct:+.1f}% gain "
            f"({m2.cagr_pct:.1f}% CAGR) by {diff_cagr:.1f} percentage points in annual compounding."
        )
    else:
        diff_cagr = round(m2.cagr_pct - m1.cagr_pct, 1)
        sentences.append(
            f"{comp2_name} delivered superior total returns of {m2.total_return_pct:+.1f}% "
            f"({m2.cagr_pct:.1f}% CAGR), outpacing {comp1_name}'s {m1.total_return_pct:+.1f}% "
            f"({m1.cagr_pct:.1f}% CAGR) by {diff_cagr:.1f} percentage points annually."
        )

    # Sentence 2: Volatility Comparison (matches prompt's exact example: 'HAL was 34% less volatile than...')
    if m1.annualized_volatility_pct < m2.annualized_volatility_pct:
        pct_less_vol = round(((m2.annualized_volatility_pct - m1.annualized_volatility_pct) / m2.annualized_volatility_pct) * 100.0, 1)
        perf_phrase = "delivered lower total return" if m1.total_return_pct < m2.total_return_pct else "also delivered higher total return"
        sentences.append(
            f"{comp1_name} was {pct_less_vol:.0f}% less volatile than {comp2_name} ({m1.annualized_volatility_pct:.1f}% vs {m2.annualized_volatility_pct:.1f}% annualized) but {perf_phrase}."
        )
    elif m2.annualized_volatility_pct < m1.annualized_volatility_pct:
        pct_less_vol = round(((m1.annualized_volatility_pct - m2.annualized_volatility_pct) / m1.annualized_volatility_pct) * 100.0, 1)
        perf_phrase = "delivered lower total return" if m2.total_return_pct < m1.total_return_pct else "also delivered higher total return"
        sentences.append(
            f"{comp2_name} was {pct_less_vol:.0f}% less volatile than {comp1_name} ({m2.annualized_volatility_pct:.1f}% vs {m1.annualized_volatility_pct:.1f}% annualized) but {perf_phrase}."
        )
    else:
        sentences.append(
            f"Both companies recorded identical annualized volatility of {m1.annualized_volatility_pct:.1f}% over the analysis window."
        )

    # Sentence 3: Drawdown & Capital Preservation
    if m1.max_drawdown_pct < m2.max_drawdown_pct:
        diff_dd = round(m2.max_drawdown_pct - m1.max_drawdown_pct, 1)
        sentences.append(
            f"During major market pullbacks, {comp1_name} preserved capital more effectively with a shallower maximum drawdown of {m1.max_drawdown_pct:.1f}%, versus {comp2_name}'s {m2.max_drawdown_pct:.1f}% peak-to-trough decline (a {diff_dd:.1f}% margin)."
        )
    else:
        diff_dd = round(m1.max_drawdown_pct - m2.max_drawdown_pct, 1)
        sentences.append(
            f"{comp2_name} exhibited stronger downside resilience with a maximum drawdown contained at {m2.max_drawdown_pct:.1f}%, compared to {comp1_name}'s steeper decline of {m1.max_drawdown_pct:.1f}% (saving {diff_dd:.1f}% in downside equity)."
        )

    # Sentence 4: Risk-Adjusted Efficiency (Sharpe Ratio)
    if m1.sharpe_ratio >= m2.sharpe_ratio:
        sentences.append(
            f"On a risk-adjusted basis, {comp1_name} produced a higher Sharpe ratio of {m1.sharpe_ratio:.2f} relative to {comp2_name}'s {m2.sharpe_ratio:.2f}, generating more excess return per unit of volatility above the {RISK_FREE_RATE_PCT:.1f}% risk-free rate."
        )
    else:
        sentences.append(
            f"Evaluating return per unit of volatility, {comp2_name} attained a superior Sharpe ratio of {m2.sharpe_ratio:.2f} compared to {comp1_name}'s {m1.sharpe_ratio:.2f}, indicating superior compensation for risk taken."
        )

    # Sentence 5: Stability Ranking vs Growth Score Trade-off
    sentences.append(
        f"In overall profiling, {stab_win_n} won the Stability Score ({max(m1.stability_score, m2.stability_score):.1f}/100 vs {min(m1.stability_score, m2.stability_score):.1f}/100), whereas {growth_win_n} led the Growth Score ({max(m1.growth_score, m2.growth_score):.1f}/100 vs {min(m1.growth_score, m2.growth_score):.1f}/100)."
    )

    # Sentence 6: 3-Month Moving Average Trend Consistency
    if m1.trend_consistency_pct >= m2.trend_consistency_pct:
        sentences.append(
            f"{comp1_name} sustained greater technical trend consistency, trading above its 3-month moving average in {m1.trend_consistency_pct:.1f}% of observed months compared to {m2.trend_consistency_pct:.1f}% for {comp2_name}."
        )
    else:
        sentences.append(
            f"{comp2_name} showed higher quarterly trend persistence, holding above its 3-month moving average in {m2.trend_consistency_pct:.1f}% of observed months ({comp1_name}: {m1.trend_consistency_pct:.1f}%)."
        )

    # Sentence 7: Short/Medium-Term Trend (50-DMA & 3-Month Momentum)
    d1_str = f"{m1.price_vs_50_dma_pct:+.1f}%" if m1.price_vs_50_dma_pct is not None else "N/A"
    d2_str = f"{m2.price_vs_50_dma_pct:+.1f}%" if m2.price_vs_50_dma_pct is not None else "N/A"
    sentences.append(
        f"Looking at medium-term technical positioning, {comp1_name} is trading {d1_str} relative to its 50-day moving average with {m1.ma_3m_slope.lower()} 3-month slope, while {comp2_name} trades {d2_str} from its 50-DMA with {m2.momentum_3m_pct:+.1f}% 3-month momentum."
    )

    return ComparisonObject(
        stability_winner=stab_win_n,
        stability_winner_ticker=stab_win_t,
        growth_winner=growth_win_n,
        growth_winner_ticker=growth_win_t,
        overall_winner=overall_win_n,
        overall_winner_ticker=overall_win_t,
        metrics=items,
        sentences=sentences
    )


# ---------------------------------------------------------------------------
# Section H: Rebased Overlay & Correlation
# ---------------------------------------------------------------------------

def compute_daily_series(df: pd.DataFrame) -> List[DailyPricePoint]:
    """
    Converts daily dataframe into typed DailyPricePoint objects with daily percentage returns.
    """
    sorted_df = df.copy()
    if not isinstance(sorted_df.index, pd.DatetimeIndex):
        if "Date" in sorted_df.columns:
            sorted_df["Date"] = pd.to_datetime(sorted_df["Date"])
            sorted_df.set_index("Date", inplace=True)
        else:
            sorted_df.index = pd.to_datetime(sorted_df.index)
    sorted_df.sort_index(inplace=True)

    price_col = "Adj Close" if "Adj Close" in sorted_df.columns else "Close"
    sorted_df["daily_return_pct"] = sorted_df[price_col].pct_change() * 100.0

    points: List[DailyPricePoint] = []
    for date, row in sorted_df.iterrows():
        ret = row["daily_return_pct"]
        points.append(
            DailyPricePoint(
                date=date.strftime("%Y-%m-%d"),
                close=float(round(row.get("Close", row[price_col]), 2)),
                adj_close=float(round(row[price_col], 2)),
                volume=int(row.get("Volume", 0)),
                daily_return_pct=float(round(ret, 2)) if pd.notna(ret) else 0.0
            )
        )
    return points


def compute_overlay_and_correlation(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame
) -> Tuple[List[OverlayPoint], float]:
    """
    Aligns both stock histories on common trading dates.
    Rebases both to 100 at the earliest shared date for direct visual overlay comparison.
    Calculates Pearson correlation of daily returns.
    """
    col_a = "Adj Close" if "Adj Close" in df_a.columns else "Close"
    col_b = "Adj Close" if "Adj Close" in df_b.columns else "Close"

    a_prices = df_a[col_a].dropna()
    b_prices = df_b[col_b].dropna()

    combined = pd.DataFrame({"a": a_prices, "b": b_prices}).dropna()
    if combined.empty or len(combined) < 5:
        return [], 0.0

    # Rebase to 100 on start date
    a_base = combined["a"].iloc[0]
    b_base = combined["b"].iloc[0]

    combined["a_norm"] = (combined["a"] / a_base) * 100.0
    combined["b_norm"] = (combined["b"] / b_base) * 100.0

    # Pearson correlation on daily returns
    returns_a = combined["a"].pct_change().dropna()
    returns_b = combined["b"].pct_change().dropna()
    correlation = float(returns_a.corr(returns_b)) if len(returns_a) > 2 else 0.0

    if np.isnan(correlation):
        correlation = 0.0

    # Downsample points for snappy UI rendering if > 300 points
    points: List[OverlayPoint] = []
    step = 1 if len(combined) <= 500 else 2
    sampled = combined.iloc[::step]
    if combined.index[-1] not in sampled.index:
        sampled = pd.concat([sampled, combined.iloc[[-1]]])

    for dt, row in sampled.iterrows():
        date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)
        points.append(
            OverlayPoint(
                date=date_str,
                company_a_rebased=float(round(row["a_norm"], 2)),
                company_b_rebased=float(round(row["b_norm"], 2))
            )
        )

    return points, round(correlation, 3)
