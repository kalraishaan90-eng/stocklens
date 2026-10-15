from typing import List, Tuple, Dict, Optional, Any
import numpy as np
import pandas as pd

from app.config import (
    DEFAULT_RECOMMENDATION_WEIGHTS,
    INVESTOR_PROFILE_WEIGHTS,
    NIFTY_BENCHMARK,
    SECTOR_PE_MEDIANS
)
from app.models.schemas import (
    PerformanceMetrics,
    Recommendation,
    HeadToHeadVerdict,
    CompanyInfo,
    SignalScore,
    InvestorProfileVerdict
)

# Mandatory Limitations Block (Always included)
LIMITATIONS: List[str] = [
    "Only price-based analysis: Evaluation is derived purely from historical market prices, trading volume, and mathematical indicator models.",
    "Excludes financial statements: Does not analyze balance sheets, cash flow statements, profit margins, or revenue quality.",
    "Excludes management quality: Does not account for promoter integrity, corporate governance standards, or execution capability.",
    "Excludes debt & solvency: Does not review debt-to-equity levels, interest coverage, or credit rating solvency.",
    "Excludes post-fetch developments: Breaking corporate news, regulatory announcements, or macroeconomic shocks after the data fetch timestamp are not incorporated.",
    "Excludes taxes & personal goals: Does not take into account individual tax brackets, transaction costs, liquidity needs, or investment horizon.",
    "Past performance disclaimer: Historical performance and return trends do not guarantee or predict future financial returns.",
    "Not SEBI-registered: StockLens is built strictly for computational equity research and analytical comparison and does not constitute SEBI-registered investment advice. Consult a licensed financial adviser before investing."
]

def compute_rsi(prices: pd.Series, period: int = 14) -> float:
    """Computes 14-period Relative Strength Index (RSI)."""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = prices.diff().dropna()
    gains = deltas.clip(lower=0)
    losses = -deltas.clip(upper=0)
    
    avg_gain = gains.rolling(window=period, min_periods=period).mean()
    avg_loss = losses.rolling(window=period, min_periods=period).mean()
    
    last_gain = avg_gain.iloc[-1]
    last_loss = avg_loss.iloc[-1]
    
    if pd.isna(last_gain) or pd.isna(last_loss):
        return 50.0
    if last_loss == 0:
        return 100.0 if last_gain > 0 else 50.0
        
    rs = last_gain / last_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return float(round(rsi, 1))

def evaluate_trend_signal(
    df: Optional[pd.DataFrame],
    current_price: float
) -> Tuple[int, str]:
    """
    Evaluates Trend: price vs 50-DMA and 200-DMA, and 3-month MA direction.
    Scores from -2 to +2. Stronger signals strictly never lower the score.
    """
    if df is not None and not df.empty and "Adj Close" in df.columns and len(df) >= 30:
        prices = df["Adj Close"].dropna()
        curr = float(prices.iloc[-1]) if current_price <= 0 else current_price
        
        # 50-DMA & 200-DMA (using available window if < 200 days)
        w50 = min(len(prices), 50)
        w200 = min(len(prices), 200)
        dma_50 = float(prices.rolling(w50).mean().iloc[-1])
        dma_200 = float(prices.rolling(w200).mean().iloc[-1])
        
        # 3-Month Moving Average (approx 63 trading days) direction
        w_ma3 = min(len(prices), 63)
        ma_3m_series = prices.rolling(w_ma3).mean()
        ma_3m_now = float(ma_3m_series.iloc[-1])
        # Compare to 21 trading days ago
        idx_prev = max(0, len(ma_3m_series) - 22)
        ma_3m_prev = float(ma_3m_series.iloc[idx_prev])
        ma_3m_direction = "rising" if ma_3m_now >= ma_3m_prev else "falling"
        
        price_above_50 = curr >= dma_50
        price_above_200 = curr >= dma_200
        golden_cross = dma_50 >= dma_200
        ma_rising = ma_3m_direction == "rising"
        
        if price_above_50 and price_above_200 and golden_cross and ma_rising:
            score = 2
            reason = (
                f"The data suggests strong upward trend: Price (₹{curr:,.1f}) is above rising 50-DMA "
                f"(₹{dma_50:,.1f}) and 200-DMA (₹{dma_200:,.1f}) with upward 3-month MA direction."
            )
        elif price_above_200 and (price_above_50 or ma_rising):
            score = 1
            reason = (
                f"The data suggests constructive trend: Price (₹{curr:,.1f}) holds above the 200-DMA "
                f"(₹{dma_200:,.1f}) with positive medium-term moving average support."
            )
        elif price_above_200 and not price_above_50 and not ma_rising:
            score = 0
            reason = (
                f"The data suggests consolidating trend: Price has pulled below 50-DMA (₹{dma_50:,.1f}) "
                f"while maintaining support above long-term 200-DMA (₹{dma_200:,.1f})."
            )
        elif not price_above_200 and (price_above_50 or ma_rising):
            score = -1
            reason = (
                f"The data suggests vulnerable trend: Price has broken below 200-DMA (₹{dma_200:,.1f}) "
                f"despite short-term counter-trend attempts."
            )
        else:
            score = -2
            reason = (
                f"The data suggests persistent downward trend: Price trades below declining 50-DMA "
                f"(₹{dma_50:,.1f}) and 200-DMA (₹{dma_200:,.1f}) with falling 3-month MA."
            )
    else:
        # Fallback if raw dataframe is minimal
        score = 1 if current_price > 0 else 0
        reason = "The data suggests moderate price stability over available trading sessions."
        
    return score, reason

def evaluate_momentum_signal(
    df: Optional[pd.DataFrame],
    metrics: PerformanceMetrics
) -> Tuple[int, str]:
    """
    Evaluates Momentum: 3-month and 6-month return, RSI zone
    (overbought >70 is a caution, oversold <30 is a potential opportunity).
    Scores from -2 to +2.
    """
    if df is not None and not df.empty and "Adj Close" in df.columns and len(df) >= 20:
        prices = df["Adj Close"].dropna()
        rsi = compute_rsi(prices, 14)
        
        # 3-month return (~63 trading days)
        idx_3m = max(0, len(prices) - 64)
        p_3m = float(prices.iloc[idx_3m])
        curr = float(prices.iloc[-1])
        ret_3m = ((curr - p_3m) / p_3m) * 100.0 if p_3m > 0 else 0.0
        
        # 6-month return (~126 trading days)
        idx_6m = max(0, len(prices) - 127)
        p_6m = float(prices.iloc[idx_6m])
        ret_6m = ((curr - p_6m) / p_6m) * 100.0 if p_6m > 0 else 0.0
    else:
        # Approximate using CAGR and positive days
        ret_3m = metrics.cagr_pct / 4.0
        ret_6m = metrics.cagr_pct / 2.0
        rsi = 55.0

    # Overbought > 70 is a caution
    if rsi >= 70.0:
        if ret_3m >= 0.0:
            score = 1  # Capped at +1 because overbought is a caution
            reason = (
                f"The data suggests strong momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%), "
                f"though an RSI of {rsi:.1f} (>70) signals short-term overbought caution."
            )
        else:
            score = 0
            reason = f"The data suggests mixed momentum with overbought RSI ({rsi:.1f}) and muted 3M return ({ret_3m:+.1f}%)."
            
    # Oversold < 30 is a potential opportunity
    elif rsi <= 30.0:
        score = 1
        reason = (
            f"The data suggests potential mean-reversion opportunity: RSI is deeply oversold at {rsi:.1f} (<30) "
            f"despite recent 3M lag ({ret_3m:+.1f}%)."
        )
        
    # Healthy RSI zone (30 to 70)
    else:
        if ret_3m >= 10.0 and ret_6m >= 15.0:
            score = 2
            reason = (
                f"The data suggests powerful multi-month momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%) "
                f"with RSI at {rsi:.1f} in healthy expansion territory."
            )
        elif ret_3m >= 0.0 or ret_6m >= 5.0:
            score = 1
            reason = (
                f"The data suggests positive momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%) "
                f"with balanced RSI at {rsi:.1f}."
            )
        elif ret_3m >= -10.0 and ret_6m >= -10.0:
            score = 0
            reason = (
                f"The data suggests neutral momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%) "
                f"with RSI stable at {rsi:.1f}."
            )
        elif ret_3m >= -20.0 or ret_6m >= -20.0:
            score = -1
            reason = (
                f"The data suggests decelerating momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%) "
                f"with RSI softening to {rsi:.1f}."
            )
        else:
            score = -2
            reason = (
                f"The data suggests severe negative momentum (3M: {ret_3m:+.1f}%, 6M: {ret_6m:+.1f}%) "
                f"indicating sustained selling velocity."
            )
            
    return score, reason

def evaluate_risk_signal(
    metrics: PerformanceMetrics
) -> Tuple[int, str]:
    """
    Evaluates Risk: volatility and max drawdown relative to NIFTY 50.
    Scores from -2 to +2. Lower risk = higher positive score.
    """
    nifty_vol = NIFTY_BENCHMARK.get("annualized_volatility_pct", 14.5)
    nifty_mdd = NIFTY_BENCHMARK.get("max_drawdown_pct", 12.0)
    
    vol = metrics.annualized_volatility_pct
    mdd = metrics.max_drawdown_pct
    
    vol_rel = vol / nifty_vol if nifty_vol > 0 else 1.0
    mdd_rel = mdd / nifty_mdd if nifty_mdd > 0 else 1.0
    
    if vol_rel <= 1.25 and mdd_rel <= 1.35:
        score = 2
        reason = (
            f"The data suggests exceptional capital stability: Volatility ({vol:.1f}%) and max drawdown ({mdd:.1f}%) "
            f"are on par with NIFTY 50 benchmark (Vol: ~{nifty_vol:.1f}%, MDD: ~{nifty_mdd:.1f}%)."
        )
    elif vol_rel <= 1.75 and mdd_rel <= 1.85:
        score = 1
        reason = (
            f"The data suggests moderate risk relative to benchmark: Volatility ({vol:.1f}%) is {vol_rel:.1f}x NIFTY 50 "
            f"with drawdown contained at {mdd:.1f}%."
        )
    elif vol_rel <= 2.30 and mdd_rel <= 2.30:
        score = 0
        reason = (
            f"The data suggests elevated market beta: Volatility ({vol:.1f}%) is {vol_rel:.1f}x and drawdown ({mdd:.1f}%) "
            f"is {mdd_rel:.1f}x broader index levels."
        )
    elif vol_rel <= 2.90 and mdd_rel <= 2.90:
        score = -1
        reason = (
            f"The data suggests high downside vulnerability: Max drawdown of {mdd:.1f}% is {mdd_rel:.1f}x "
            f"the NIFTY 50 baseline."
        )
    else:
        score = -2
        reason = (
            f"The data suggests aggressive risk exposure: Extreme volatility ({vol:.1f}%) and drawdown ({mdd:.1f}%) "
            f"exceed 3x index norms."
        )
        
    return score, reason

def evaluate_quality_signal(
    metrics: PerformanceMetrics
) -> Tuple[int, str]:
    """
    Evaluates Quality of returns: Sharpe-style ratio, trend consistency (% positive trading days).
    Scores from -2 to +2.
    """
    sharpe = metrics.sharpe_ratio
    pos_days = metrics.positive_days_pct
    
    if sharpe >= 1.2 and pos_days >= 51.5:
        score = 2
        reason = (
            f"The data suggests superior return efficiency: Sharpe ratio of {sharpe:.2f} paired with "
            f"strong session win consistency ({pos_days:.1f}% positive days)."
        )
    elif sharpe >= 0.70 and pos_days >= 49.0:
        score = 1
        reason = (
            f"The data suggests healthy risk-adjusted quality: Sharpe ratio of {sharpe:.2f} comfortably clears "
            f"the 6.5% risk-free hurdle."
        )
    elif sharpe >= 0.0:
        score = 0
        reason = (
            f"The data suggests acceptable return quality: Sharpe ratio of {sharpe:.2f} provides modest excess "
            f"return over cash benchmarks."
        )
    elif sharpe >= -0.60:
        score = -1
        reason = (
            f"The data suggests sub-optimal efficiency: Sharpe ratio of {sharpe:.2f} indicates returns fail to "
            f"adequately compensate for volatility."
        )
    else:
        score = -2
        reason = (
            f"The data suggests poor return quality: Negative Sharpe ratio ({sharpe:.2f}) with persistent daily session drag."
        )
        
    return score, reason

def evaluate_valuation_signal(
    pe_ratio: Optional[float],
    sector: Optional[str]
) -> Tuple[Optional[int], str, bool]:
    """
    Evaluates Valuation sanity (only if data exists): P/E vs its sector median.
    If missing or <= 0, skips and returns 'not available'.
    Scores from -2 to +2 when available.
    """
    if pe_ratio is None or pe_ratio <= 0.0 or np.isnan(pe_ratio):
        return (
            None,
            "Valuation sanity check not available: P/E data is not reported or negative for this symbol.",
            False
        )
        
    # Match sector median
    sec_key = (sector or "general").lower().strip()
    median_pe = 25.0
    for s_name, med in SECTOR_PE_MEDIANS.items():
        if s_name in sec_key:
            median_pe = med
            break
            
    if pe_ratio <= 0.85 * median_pe and pe_ratio >= 6.0:
        score = 2
        reason = (
            f"The data suggests attractive relative valuation: P/E of {pe_ratio:.1f} trades at a discount "
            f"to sector median (~{median_pe:.1f})."
        )
    elif pe_ratio <= 1.25 * median_pe:
        score = 1
        reason = (
            f"The data suggests fair valuation: P/E of {pe_ratio:.1f} aligns reasonably with sector median (~{median_pe:.1f})."
        )
    elif pe_ratio <= 1.65 * median_pe:
        score = 0
        reason = (
            f"The data suggests mild premium valuation: P/E of {pe_ratio:.1f} reflects an elevated multiple over "
            f"sector median (~{median_pe:.1f})."
        )
    elif pe_ratio <= 2.10 * median_pe and pe_ratio <= 85.0:
        score = -1
        reason = (
            f"The data suggests stretched valuation: P/E of {pe_ratio:.1f} trades well above sector median (~{median_pe:.1f})."
        )
    else:
        score = -2
        reason = (
            f"The data suggests severe multiple expansion risk: P/E of {pe_ratio:.1f} is more than double "
            f"sector median (~{median_pe:.1f})."
        )
        
    return score, reason, True

def evaluate_distance_52w_signal(
    metrics: PerformanceMetrics
) -> Tuple[int, str]:
    """
    Evaluates Distance from 52-week high/low.
    Scores from -2 to +2.
    """
    curr = metrics.current_price
    high = metrics.high_52w
    low = metrics.low_52w
    
    if high <= low or high <= 0:
        return 0, "The data suggests price holding within established 52-week boundary levels."
        
    pct_from_high = ((curr - high) / high) * 100.0
    range_pos = (curr - low) / (high - low)
    
    if pct_from_high >= -8.0 and range_pos >= 0.80:
        score = 2
        reason = (
            f"The data suggests strong price leadership: Trading within {abs(pct_from_high):.1f}% of 52-week high "
            f"(₹{high:,.1f}) at {range_pos*100:.0f}% of yearly range."
        )
    elif range_pos >= 0.60:
        score = 1
        reason = (
            f"The data suggests upper-range resilience: Operating at {range_pos*100:.0f}% of 52-week envelope "
            f"({abs(pct_from_high):.1f}% off peak)."
        )
    elif range_pos >= 0.40:
        score = 0
        reason = (
            f"The data suggests mid-envelope consolidation: Situated at {range_pos*100:.0f}% of its 52-week price range."
        )
    elif range_pos >= 0.20:
        score = -1
        reason = (
            f"The data suggests lower-range lag: Trading {abs(pct_from_high):.1f}% below 52-week high, near lower support."
        )
    else:
        dist_low_pct = ((curr - low) / low) * 100.0
        score = -2
        reason = (
            f"The data suggests structural price lag: Trading within {dist_low_pct:.1f}% of 52-week low (₹{low:,.1f})."
        )
        
    return score, reason

def map_action(score: float) -> str:
    """
    Maps weighted total score to recommendation stance:
    >= +4: BUY
    between -3 and +3 (or -4 to +4): HOLD
    <= -4: AVOID
    """
    if score >= 4.0:
        return "BUY"
    elif score <= -4.0:
        return "AVOID"
    else:
        return "HOLD"

def determine_risk_level(volatility_pct: float, max_drawdown_pct: float) -> str:
    """
    Assigns Risk Level: Low / Medium / High from volatility and drawdown.
    """
    if volatility_pct < 22.0 and max_drawdown_pct < 20.0:
        return "Low"
    elif volatility_pct >= 35.0 or max_drawdown_pct >= 35.0:
        return "High"
    else:
        return "Medium"

def calculate_scorecard(
    metrics: PerformanceMetrics,
    df: Optional[pd.DataFrame] = None,
    meta: Optional[Dict[str, Any]] = None,
    weights_config: Optional[Dict[str, float]] = None,
    target_scale: float = 5.0
) -> Tuple[float, List[SignalScore]]:
    """
    Computes all 6 signals (-2..+2), transparently applies configured weights,
    normalizes active weights to target_scale (default 5.0, resulting in score -10..+10),
    and returns (weighted_total, signals).
    """
    weights = dict(weights_config or DEFAULT_RECOMMENDATION_WEIGHTS)
    
    # 1. Trend
    s_trend, r_trend = evaluate_trend_signal(df, metrics.current_price)
    
    # 2. Momentum
    s_mom, r_mom = evaluate_momentum_signal(df, metrics)
    
    # 3. Risk vs NIFTY 50
    s_risk, r_risk = evaluate_risk_signal(metrics)
    
    # 4. Quality of Returns
    s_qual, r_qual = evaluate_quality_signal(metrics)
    
    # 5. Valuation Sanity
    pe_val = metrics.pe_ratio
    if pe_val is None and meta:
        pe_val = meta.get("trailingPE") or meta.get("pe_ratio") or meta.get("trailing_pe")
    sector_str = meta.get("sector", "Diversified") if meta else "Diversified"
    s_val, r_val, val_available = evaluate_valuation_signal(pe_val, sector_str)
    
    # 6. Distance from 52W High/Low
    s_dist, r_dist = evaluate_distance_52w_signal(metrics)
    
    raw_signals = [
        {"cat": "trend", "name": "Trend Structure (Price vs 50/200-DMA & 3M MA)", "score": s_trend, "reason": r_trend, "avail": True},
        {"cat": "momentum", "name": "Multi-Month Momentum & RSI Zone", "score": s_mom, "reason": r_mom, "avail": True},
        {"cat": "risk", "name": "Downside Risk & Drawdown vs NIFTY 50", "score": s_risk, "reason": r_risk, "avail": True},
        {"cat": "quality_of_returns", "name": "Return Quality & Consistency (Sharpe)", "score": s_qual, "reason": r_qual, "avail": True},
        {"cat": "valuation", "name": "Valuation Sanity (P/E vs Sector Median)", "score": s_val, "reason": r_val, "avail": val_available},
        {"cat": "distance_52w", "name": "52-Week Range Envelope Positioning", "score": s_dist, "reason": r_dist, "avail": True},
    ]
    
    # Calculate active weight sum for normalization
    active_weight_sum = sum(weights.get(item["cat"], 1.0) for item in raw_signals if item["avail"])
    if active_weight_sum <= 0:
        active_weight_sum = 1.0
        
    norm_factor = target_scale / active_weight_sum
    
    signals: List[SignalScore] = []
    total_weighted_score = 0.0
    
    for item in raw_signals:
        cat = item["cat"]
        is_avail = item["avail"]
        base_w = weights.get(cat, 1.0) if is_avail else 0.0
        effective_w = round(base_w * norm_factor, 3)
        
        if is_avail and item["score"] is not None:
            contrib = round(effective_w * item["score"], 2)
            total_weighted_score += contrib
            sig_score = item["score"]
        else:
            contrib = 0.0
            sig_score = None
            
        signals.append(
            SignalScore(
                name=item["name"],
                category=cat,
                score=sig_score,
                weight=effective_w,
                weighted_score=contrib,
                reason=item["reason"],
                is_available=is_avail
            )
        )
        
    final_score = round(total_weighted_score, 1)
    # Clip between -10.0 and +10.0
    final_score = max(-10.0, min(10.0, final_score))
    return final_score, signals

def generate_recommendation(
    metrics: PerformanceMetrics,
    company_name: str,
    df: Optional[pd.DataFrame] = None,
    meta: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None
) -> Recommendation:
    """
    Generates a fully transparent, rule-based recommendation scorecard for a company:
    - 6 signals scored -2..+2 with individual one-line reasons
    - Weighted score mapping: >= +4 BUY, between -3 and +3 HOLD, <= -4 AVOID
    - Risk Level: Low / Medium / High
    - Key Drivers and summary in careful language ("The data suggests...")
    - Limitations block included
    """
    score, signals = calculate_scorecard(metrics, df=df, meta=meta, weights_config=weights)
    action = map_action(score)
    risk_level = determine_risk_level(metrics.annualized_volatility_pct, metrics.max_drawdown_pct)
    
    # Extract top positive / negative drivers
    active_signals = [s for s in signals if s.is_available and s.score is not None]
    sorted_by_impact = sorted(active_signals, key=lambda s: s.weighted_score, reverse=True)
    
    drivers: List[str] = []
    if sorted_by_impact:
        top_pos = sorted_by_impact[0]
        if top_pos.score is not None and top_pos.score > 0:
            drivers.append(f"Primary Support ({top_pos.name}): {top_pos.reason}")
    if len(sorted_by_impact) >= 2:
        second_pos = sorted_by_impact[1]
        if second_pos.score is not None and second_pos.score > 0:
            drivers.append(f"Secondary Strength: {second_pos.reason}")
    if sorted_by_impact:
        worst = sorted_by_impact[-1]
        if worst.score is not None and worst.score < 0:
            drivers.append(f"Key Headwind/Risk Factor: {worst.reason}")
            
    if not drivers:
        drivers = [
            f"The data suggests balanced metrics with 2Y CAGR of {metrics.cagr_pct:+.1f}%.",
            f"Annualized volatility stands at {metrics.annualized_volatility_pct:.1f}% with max drawdown of {metrics.max_drawdown_pct:.1f}%.",
            f"Sharpe ratio is {metrics.sharpe_ratio:.2f} relative to 6.5% benchmark."
        ]
        
    score_sign = "+" if score > 0 else ""
    summary = (
        f"The data suggests a composite rating score of {score_sign}{score:.1f} "
        f"(scale -10 to +10), indicating a '{action}' stance for {company_name}. "
        f"With annualized volatility of {metrics.annualized_volatility_pct:.1f}% and max drawdown of "
        f"{metrics.max_drawdown_pct:.1f}%, the risk classification is '{risk_level}'."
    )
    
    return Recommendation(
        action=action,
        score=score,
        risk_level=risk_level,
        signals=signals,
        key_drivers=drivers,
        summary=summary,
        limitations=LIMITATIONS
    )

def evaluate_profile_pick(
    profile_name: str,
    weights: Dict[str, float],
    info_a: CompanyInfo,
    metrics_a: PerformanceMetrics,
    df_a: Optional[pd.DataFrame],
    meta_a: Optional[Dict[str, Any]],
    info_b: CompanyInfo,
    metrics_b: PerformanceMetrics,
    df_b: Optional[pd.DataFrame],
    meta_b: Optional[Dict[str, Any]]
) -> InvestorProfileVerdict:
    """
    Evaluates both companies under a specific investor profile weighting regime
    (Conservative, Balanced, Aggressive) and assigns the profile pick and rationale.
    """
    score_a, _ = calculate_scorecard(metrics_a, df=df_a, meta=meta_a, weights_config=weights)
    score_b, _ = calculate_scorecard(metrics_b, df=df_b, meta=meta_b, weights_config=weights)
    
    if score_a > score_b:
        winner_ticker = info_a.ticker
        winner_name = info_a.name
    elif score_b > score_a:
        winner_ticker = info_b.ticker
        winner_name = info_b.name
    else:
        # Tie breaker: Sharpe for Conservative/Balanced, CAGR for Aggressive
        if profile_name == "Aggressive":
            winner_ticker = info_a.ticker if metrics_a.cagr_pct >= metrics_b.cagr_pct else info_b.ticker
            winner_name = info_a.name if winner_ticker == info_a.ticker else info_b.name
        else:
            winner_ticker = info_a.ticker if metrics_a.sharpe_ratio >= metrics_b.sharpe_ratio else info_b.ticker
            winner_name = info_a.name if winner_ticker == info_a.ticker else info_b.name

    if profile_name == "Conservative":
        rationale = (
            f"The data suggests that for a Conservative investor prioritizing capital preservation and low drawdown, "
            f"{winner_name} emerges ahead (Score: {score_a if winner_ticker == info_a.ticker else score_b:+.1f} vs "
            f"{score_b if winner_ticker == info_a.ticker else score_a:+.1f}) due to superior downside resilience."
        )
    elif profile_name == "Aggressive":
        rationale = (
            f"The data suggests that for an Aggressive investor targeting maximum capital growth and momentum, "
            f"{winner_name} takes the lead (Score: {score_a if winner_ticker == info_a.ticker else score_b:+.1f} vs "
            f"{score_b if winner_ticker == info_a.ticker else score_a:+.1f}) based on superior price momentum and CAGR."
        )
    else:
        rationale = (
            f"The data suggests that under a Balanced risk-return mandate, {winner_name} achieves a higher composite "
            f"score ({score_a if winner_ticker == info_a.ticker else score_b:+.1f} vs "
            f"{score_b if winner_ticker == info_a.ticker else score_a:+.1f}) across trend, momentum, and risk efficiency."
        )

    return InvestorProfileVerdict(
        profile=profile_name,
        winner_ticker=winner_ticker,
        winner_name=winner_name,
        score_a=score_a,
        score_b=score_b,
        rationale=rationale
    )

def compare_head_to_head(
    info_a: CompanyInfo,
    metrics_a: PerformanceMetrics,
    rec_a: Recommendation,
    info_b: CompanyInfo,
    metrics_b: PerformanceMetrics,
    rec_b: Recommendation,
    df_a: Optional[pd.DataFrame] = None,
    df_b: Optional[pd.DataFrame] = None,
    meta_a: Optional[Dict[str, Any]] = None,
    meta_b: Optional[Dict[str, Any]] = None
) -> HeadToHeadVerdict:
    """
    Compares two companies side by side:
    - Picks the winner with clear "why" (exactly 3 bullet reasons)
    - Provides a "when the other might be better" caveat
    - Computes investor-profile views: Conservative / Balanced / Aggressive
    - Includes the required limitations block
    """
    score_diff = round(rec_a.score - rec_b.score, 1)
    abs_diff = abs(score_diff)
    
    if score_diff > 0.0:
        winner_ticker = info_a.ticker
        winner_name = info_a.name
        loser_name = info_b.name
        loser_ticker = info_b.ticker
        margin = "Dominant Outperformance" if score_diff >= 4.0 else "Slight Edge"
        if score_diff < 2.0:
            margin = "Balanced / Tie"
    elif score_diff < 0.0:
        winner_ticker = info_b.ticker
        winner_name = info_b.name
        loser_name = info_a.name
        loser_ticker = info_a.ticker
        margin = "Dominant Outperformance" if score_diff <= -4.0 else "Slight Edge"
        if score_diff > -2.0:
            margin = "Balanced / Tie"
    else:
        # Tie or neck-and-neck: use Sharpe as tie breaker
        if metrics_a.sharpe_ratio >= metrics_b.sharpe_ratio:
            winner_ticker = info_a.ticker
            winner_name = info_a.name
            loser_name = info_b.name
            loser_ticker = info_b.ticker
        else:
            winner_ticker = info_b.ticker
            winner_name = info_b.name
            loser_name = info_a.name
            loser_ticker = info_a.ticker
        margin = "Balanced / Tie"
        
    is_a_winner = (winner_ticker == info_a.ticker)
    win_metrics = metrics_a if is_a_winner else metrics_b
    lose_metrics = metrics_b if is_a_winner else metrics_a
    win_rec = rec_a if is_a_winner else rec_b
    lose_rec = rec_b if is_a_winner else rec_a

    # Keep comparison claims tied to observed values; a score winner need not
    # also have lower risk or higher Sharpe.
    why_bullets = [
        (
            f"Composite score: {winner_name} scored {win_rec.score:+.1f} versus {lose_rec.score:+.1f} "
            f"for {loser_name}; the scorecard weights trend, momentum, risk, return quality, valuation when available, and 52-week position."
        ),
        (
            f"Risk comparison: {winner_name} had {win_metrics.annualized_volatility_pct:.1f}% annualized volatility "
            f"and {win_metrics.max_drawdown_pct:.1f}% max drawdown; {loser_name} had "
            f"{lose_metrics.annualized_volatility_pct:.1f}% and {lose_metrics.max_drawdown_pct:.1f}%, respectively."
        ),
        (
            f"Return quality and growth: {winner_name} had a Sharpe-style ratio of {win_metrics.sharpe_ratio:.2f} "
            f"and CAGR of {win_metrics.cagr_pct:+.1f}%; {loser_name} had {lose_metrics.sharpe_ratio:.2f} "
            f"and {lose_metrics.cagr_pct:+.1f}%, respectively."
        )
    ]

    # "When the other might be better" Caveat
    if lose_metrics.cagr_pct > win_metrics.cagr_pct:
        when_other_better = (
            f"When {loser_name} ({loser_ticker}) might be better: The data suggests {loser_name} delivered a higher "
            f"compound growth rate (CAGR of {lose_metrics.cagr_pct:+.1f}% vs {win_metrics.cagr_pct:+.1f}%). It may better "
            f"suit an aggressive, risk-tolerant investor seeking higher cyclical upside and willing to absorb steeper drawdowns."
        )
    elif lose_metrics.annualized_volatility_pct < win_metrics.annualized_volatility_pct:
        when_other_better = (
            f"When {loser_name} ({loser_ticker}) might be better: The data suggests {loser_name} exhibited lower annualized "
            f"volatility ({lose_metrics.annualized_volatility_pct:.1f}% vs {win_metrics.annualized_volatility_pct:.1f}%). It may "
            f"suit a defensive investor prioritizing minimal daily price fluctuation over pure growth."
        )
    else:
        when_other_better = (
            f"When {loser_name} ({loser_ticker}) might be better: The data suggests {loser_name} could be considered during "
            f"broader sector rallies where high-beta assets tend to outperform, or by investors with an extended multi-year "
            f"horizon comfortable with temporary consolidation."
        )

    # Investor profile evaluations
    profile_verdicts: Dict[str, InvestorProfileVerdict] = {}
    for prof_name, p_weights in INVESTOR_PROFILE_WEIGHTS.items():
        profile_verdicts[prof_name] = evaluate_profile_pick(
            prof_name,
            p_weights,
            info_a,
            metrics_a,
            df_a,
            meta_a,
            info_b,
            metrics_b,
            df_b,
            meta_b
        )

    verdict_text = (
        f"The data suggests that {winner_name} holds the quantitative advantage over {loser_name} with a {margin.lower()} "
        f"({abs_diff:.1f} point margin). Over the observed 2-year cycle, the data indicates a more favorable balance of "
        f"trend stability, risk-adjusted returns, and capital preservation."
    )

    comparison_summary = [
        f"Compound Growth (CAGR): {info_a.name} generated {metrics_a.cagr_pct:+.1f}% vs {info_b.name}'s {metrics_b.cagr_pct:+.1f}%.",
        f"Risk-Adjusted Efficiency: {info_a.name} Sharpe ratio is {metrics_a.sharpe_ratio:.2f} compared to {info_b.name}'s {metrics_b.sharpe_ratio:.2f}.",
        f"Downside Drawdown: Maximum drawdown was {metrics_a.max_drawdown_pct:.1f}% ({info_a.name}) vs {metrics_b.max_drawdown_pct:.1f}% ({info_b.name}).",
        f"Annualized Volatility: {metrics_a.annualized_volatility_pct:.1f}% ({info_a.name}) vs {metrics_b.annualized_volatility_pct:.1f}% ({info_b.name})."
    ]

    return HeadToHeadVerdict(
        winner_ticker=winner_ticker,
        winner_name=winner_name,
        margin=margin,
        verdict_text=verdict_text,
        score_diff=abs_diff,
        why_bullets=why_bullets,
        when_other_better=when_other_better,
        investor_profiles=profile_verdicts,
        comparison_summary=comparison_summary,
        limitations=LIMITATIONS
    )
