import pytest
import pandas as pd
import numpy as np

from app.models.schemas import (
    PerformanceMetrics,
    CompanyInfo,
    SignalScore,
    Recommendation,
    RecommendationItem,
    HeadToHeadVerdict
)
from app.services.recommendation import (
    evaluate_trend_signal,
    evaluate_momentum_signal,
    evaluate_risk_signal,
    evaluate_quality_signal,
    evaluate_valuation_signal,
    evaluate_distance_52w_signal,
    calculate_scorecard,
    generate_recommendation,
    compare_head_to_head,
    map_action,
    determine_risk_level,
    LIMITATIONS
)

def create_mock_df(prices_list):
    """Helper to create mock daily dataframe with business day index."""
    dates = pd.date_range(end="2026-10-01", periods=len(prices_list), freq="B")
    return pd.DataFrame({
        "Adj Close": prices_list,
        "Close": prices_list,
        "Volume": [100000] * len(prices_list)
    }, index=dates)

def create_base_metrics(
    cagr=40.0,
    vol=20.0,
    mdd=15.0,
    sharpe=1.5,
    pos_days=53.0,
    curr=4000.0,
    high=4200.0,
    low=2000.0,
    pe=None
):
    return PerformanceMetrics(
        current_price=curr,
        cagr_pct=cagr,
        annualized_volatility_pct=vol,
        max_drawdown_pct=mdd,
        sharpe_ratio=sharpe,
        high_52w=high,
        low_52w=low,
        total_return_pct=100.0,
        positive_days_pct=pos_days,
        pe_ratio=pe
    )

# ---------------------------------------------------------------------------
# 1. Monotonic Checks: Stronger signals never lower the score
# ---------------------------------------------------------------------------

def test_monotonic_trend_signal():
    """Verify that improving trend position (above 200-DMA, above 50-DMA, golden cross) never lowers the score."""
    # Scenario A: Deep downtrend (prices crashing below both 50 and 200 DMA)
    prices_down = np.linspace(500, 100, 250)
    df_down = create_mock_df(prices_down)
    score_down, _ = evaluate_trend_signal(df_down, 100.0)

    # Scenario B: Consolidating (price bouncing above 200-DMA)
    prices_cons = np.array([200] * 150 + [250] * 50 + [220] * 50)
    df_cons = create_mock_df(prices_cons)
    score_cons, _ = evaluate_trend_signal(df_cons, 220.0)

    # Scenario C: Strong uptrend (prices rising monotonically above 50 & 200 DMA)
    prices_up = np.linspace(100, 500, 250)
    df_up = create_mock_df(prices_up)
    score_up, _ = evaluate_trend_signal(df_up, 500.0)

    assert score_down <= score_cons <= score_up
    assert score_up == 2
    assert score_down == -2

def test_monotonic_quality_signal():
    """Verify that increasing Sharpe ratio and positive days never lowers the quality score."""
    m_poor = create_base_metrics(sharpe=-0.8, pos_days=42.0)
    m_med = create_base_metrics(sharpe=0.3, pos_days=48.0)
    m_good = create_base_metrics(sharpe=0.9, pos_days=50.0)
    m_excellent = create_base_metrics(sharpe=1.6, pos_days=55.0)

    s_poor, _ = evaluate_quality_signal(m_poor)
    s_med, _ = evaluate_quality_signal(m_med)
    s_good, _ = evaluate_quality_signal(m_good)
    s_excellent, _ = evaluate_quality_signal(m_excellent)

    assert s_poor <= s_med <= s_good <= s_excellent
    assert s_poor == -2
    assert s_excellent == 2

def test_monotonic_risk_signal():
    """Verify that lower volatility and shallower drawdown never lower the risk score."""
    m_extreme = create_base_metrics(vol=48.0, mdd=45.0)
    m_elevated = create_base_metrics(vol=30.0, mdd=25.0)
    m_benchmark = create_base_metrics(vol=15.0, mdd=13.0)

    s_extreme, _ = evaluate_risk_signal(m_extreme)
    s_elevated, _ = evaluate_risk_signal(m_elevated)
    s_benchmark, _ = evaluate_risk_signal(m_benchmark)

    assert s_extreme <= s_elevated <= s_benchmark
    assert s_extreme == -2
    assert s_benchmark == 2

def test_monotonic_distance_52w_signal():
    """Verify that trading closer to 52-week high strictly never lowers the score."""
    # Near 52W low
    m_low = create_base_metrics(curr=2050.0, high=4000.0, low=2000.0)
    # Mid 52W range
    m_mid = create_base_metrics(curr=3000.0, high=4000.0, low=2000.0)
    # Near 52W high
    m_high = create_base_metrics(curr=3950.0, high=4000.0, low=2000.0)

    s_low, _ = evaluate_distance_52w_signal(m_low)
    s_mid, _ = evaluate_distance_52w_signal(m_mid)
    s_high, _ = evaluate_distance_52w_signal(m_high)

    assert s_low <= s_mid <= s_high
    assert s_low == -2
    assert s_high == 2

def test_composite_scorecard_monotonicity():
    """Verify that if every signal improves or stays equal, total score is non-decreasing."""
    df_bear = create_mock_df(np.linspace(400, 100, 200))
    df_bull = create_mock_df(np.linspace(100, 400, 200))

    m_bear = create_base_metrics(cagr=-20.0, vol=42.0, mdd=40.0, sharpe=-0.7, pos_days=43.0, curr=105.0, high=400.0, low=100.0)
    m_bull = create_base_metrics(cagr=65.0, vol=18.0, mdd=12.0, sharpe=2.1, pos_days=56.0, curr=395.0, high=400.0, low=100.0)

    score_bear, _ = calculate_scorecard(m_bear, df=df_bear)
    score_bull, _ = calculate_scorecard(m_bull, df=df_bull)

    assert score_bull > score_bear
    assert score_bull >= 4.0
    assert score_bear <= -4.0

# ---------------------------------------------------------------------------
# 2. Boundary Mapping Tests: >= +4 BUY, between -3 and +3 HOLD, <= -4 AVOID
# ---------------------------------------------------------------------------

def test_boundary_mapping_actions():
    """Verify strict threshold mapping for BUY, HOLD, and AVOID."""
    assert map_action(10.0) == "BUY"
    assert map_action(4.1) == "BUY"
    assert map_action(4.0) == "BUY"

    # Between -3 and +3 (and boundaries) must map to HOLD
    assert map_action(3.9) == "HOLD"
    assert map_action(3.0) == "HOLD"
    assert map_action(0.0) == "HOLD"
    assert map_action(-3.0) == "HOLD"
    assert map_action(-3.9) == "HOLD"

    # <= -4 must map to AVOID
    assert map_action(-4.0) == "AVOID"
    assert map_action(-4.1) == "AVOID"
    assert map_action(-10.0) == "AVOID"

def test_risk_level_boundaries():
    """Verify Low / Medium / High mapping based on volatility and drawdown."""
    # Low: Vol < 22 and MDD < 20
    assert determine_risk_level(18.0, 15.0) == "Low"
    assert determine_risk_level(21.9, 19.9) == "Low"

    # High: Vol >= 35 or MDD >= 35
    assert determine_risk_level(35.0, 15.0) == "High"
    assert determine_risk_level(20.0, 35.0) == "High"
    assert determine_risk_level(40.0, 40.0) == "High"

    # Medium: between Low and High
    assert determine_risk_level(25.0, 22.0) == "Medium"
    assert determine_risk_level(22.0, 15.0) == "Medium"
    assert determine_risk_level(18.0, 25.0) == "Medium"

# ---------------------------------------------------------------------------
# 3. Valuation Sanity: Missing vs Available
# ---------------------------------------------------------------------------

def test_valuation_missing_gracefully_skipped():
    """Verify that missing/None/0 P/E is marked not available and does not bias score."""
    s_none, r_none, avail_none = evaluate_valuation_signal(None, "Defence")
    assert s_none is None
    assert avail_none is False
    assert "not available" in r_none.lower()

    s_zero, r_zero, avail_zero = evaluate_valuation_signal(0.0, "Defence")
    assert s_zero is None
    assert avail_zero is False

def test_valuation_available_scoring():
    """Verify that available P/E evaluates against sector median."""
    # Defence sector median is ~42.0
    # P/E of 25 is attractive discount (< 0.85 * 42 = 35.7) -> +2
    s_cheap, r_cheap, avail_cheap = evaluate_valuation_signal(25.0, "Defence")
    assert s_cheap == 2
    assert avail_cheap is True

    # P/E of 95 is > 2.4x sector median -> -2
    s_expensive, r_exp, avail_exp = evaluate_valuation_signal(95.0, "Defence")
    assert s_expensive == -2
    assert avail_exp is True

# ---------------------------------------------------------------------------
# 4. Momentum & RSI Overbought / Oversold Zones
# ---------------------------------------------------------------------------

def test_momentum_rsi_caution_and_opportunity():
    """Verify overbought >70 is a caution and oversold <30 is an opportunity."""
    # Prices rising steeply (RSI > 70)
    prices_surge = [100.0] * 30 + list(np.linspace(100, 300, 30))
    df_surge = create_mock_df(prices_surge)
    m = create_base_metrics(cagr=80.0)
    s_surge, r_surge = evaluate_momentum_signal(df_surge, m)
    # Caution limits score to +1 despite massive returns
    assert s_surge == 1
    assert "overbought caution" in r_surge.lower()

    # Prices falling steeply (RSI < 30)
    prices_plummet = [300.0] * 30 + list(np.linspace(300, 100, 30))
    df_plummet = create_mock_df(prices_plummet)
    s_plumm, r_plumm = evaluate_momentum_signal(df_plummet, m)
    # Oversold recognized as potential mean-reversion opportunity
    assert s_plumm == 1
    assert "oversold" in r_plumm.lower()
    assert "opportunity" in r_plumm.lower()

# ---------------------------------------------------------------------------
# 5. Head-to-Head Winner, 3 Why Bullets, and Caveat
# ---------------------------------------------------------------------------

def test_head_to_head_winner_and_caveat():
    """Verify head-to-head generates 3 why bullets and a 'when other might be better' caveat."""
    info_a = CompanyInfo(ticker="HAL.NS", name="Hindustan Aeronautics Limited")
    info_b = CompanyInfo(ticker="MAZDOCK.NS", name="Mazagon Dock Shipbuilders Limited")

    m_a = create_base_metrics(cagr=50.0, vol=21.0, mdd=14.0, sharpe=2.1, curr=4500.0, high=4700.0, low=2000.0)
    m_b = create_base_metrics(cagr=75.0, vol=32.0, mdd=24.0, sharpe=2.1, curr=4200.0, high=4800.0, low=1500.0)

    df_a = create_mock_df(np.linspace(2000, 4500, 250))
    df_b = create_mock_df(np.linspace(1500, 4200, 250))

    rec_a = generate_recommendation(m_a, info_a.name, df=df_a)
    rec_b = generate_recommendation(m_b, info_b.name, df=df_b)

    h2h = compare_head_to_head(info_a, m_a, rec_a, info_b, m_b, rec_b, df_a=df_a, df_b=df_b)

    # Must have exactly 3 why bullets
    assert len(h2h.why_bullets) == 3
    # Must have caveat
    assert len(h2h.when_other_better) > 20
    assert "When" in h2h.when_other_better
    assert "might be better" in h2h.when_other_better

    # The score leader must be the winner even when its margin is small.
    assert h2h.winner_ticker == (info_a.ticker if rec_a.score >= rec_b.score else info_b.ticker)
    assert all("risk comparison" not in reason.lower() or "had" in reason.lower() for reason in h2h.why_bullets)


def test_api_recommendation_item_preserves_full_scorecard():
    """The compact /api/analyze recommendation objects expose the same audit data."""
    rec = generate_recommendation(
        create_base_metrics(),
        "Test Co",
        df=create_mock_df(np.linspace(100, 200, 200)),
    )
    item = RecommendationItem(
        action=rec.action,
        score=rec.score,
        risk_level=rec.risk_level,
        signals=rec.signals,
        key_drivers=rec.key_drivers,
        summary=rec.summary,
        limitations=rec.limitations,
    )

    assert len(item.signals) == 6
    assert all(signal.reason for signal in item.signals)
    assert any(not signal.is_available and "not available" in signal.reason.lower() for signal in item.signals)
    assert item.limitations == LIMITATIONS

# ---------------------------------------------------------------------------
# 6. Investor Profile Views (Conservative, Balanced, Aggressive)
# ---------------------------------------------------------------------------

def test_investor_profile_views():
    """Verify that Conservative, Balanced, and Aggressive profiles evaluate properly."""
    info_a = CompanyInfo(ticker="STABLE.NS", name="Stable Low-Vol Co")
    info_b = CompanyInfo(ticker="ROCKET.NS", name="High-Beta Growth Co")

    # Stock A: Low volatility, low drawdown, modest growth (Defensive utility profile)
    m_a = create_base_metrics(cagr=8.0, vol=11.0, mdd=7.0, sharpe=0.6, curr=102.0, high=105.0, low=95.0)
    df_a = create_mock_df(np.linspace(96, 102, 250))

    # Stock B: High CAGR, high momentum, elevated beta/drawdown (Rocket growth profile)
    m_b = create_base_metrics(cagr=90.0, vol=34.0, mdd=26.0, sharpe=2.4, curr=380.0, high=400.0, low=100.0)
    df_b = create_mock_df(np.linspace(100, 380, 250))

    rec_a = generate_recommendation(m_a, info_a.name, df=df_a)
    rec_b = generate_recommendation(m_b, info_b.name, df=df_b)

    h2h = compare_head_to_head(info_a, m_a, rec_a, info_b, m_b, rec_b, df_a=df_a, df_b=df_b)

    assert h2h.investor_profiles is not None
    assert "Conservative" in h2h.investor_profiles
    assert "Balanced" in h2h.investor_profiles
    assert "Aggressive" in h2h.investor_profiles

    cons = h2h.investor_profiles["Conservative"]
    aggr = h2h.investor_profiles["Aggressive"]

    # Conservative penalizes Stock B's high vol & drawdown -> Stable Co should win
    assert cons.winner_ticker == "STABLE.NS"
    # Aggressive prioritizes high CAGR & momentum -> High-Beta Co should win
    assert aggr.winner_ticker == "ROCKET.NS"

# ---------------------------------------------------------------------------
# 7. Limitations Block & Careful Language
# ---------------------------------------------------------------------------

def test_limitations_block_and_careful_language():
    """Verify that limitations block is always populated with mandatory clauses and phrasing is non-prescriptive."""
    m = create_base_metrics()
    df = create_mock_df(np.linspace(100, 200, 200))
    rec = generate_recommendation(m, "Test Co", df=df)

    # Check limitations block
    assert len(rec.limitations) >= 7
    combined_limits = " ".join(rec.limitations).lower()
    assert "price-based analysis" in combined_limits
    assert "financial statements" in combined_limits
    assert "management quality" in combined_limits
    assert "debt" in combined_limits
    assert "past performance" in combined_limits
    assert "sebi-registered" in combined_limits

    # Check language compliance
    assert "the data suggests" in rec.summary.lower()
    assert "you should definitely buy" not in rec.summary.lower()
    assert "definitely buy" not in rec.summary.lower()
