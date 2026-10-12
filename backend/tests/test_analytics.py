import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.services.analytics import (
    compute_monthly_series,
    build_monthly_table,
    compute_max_drawdown_details,
    compute_daily_mas,
    compute_performance_metrics,
    build_comparison_object,
    compute_overlay_and_correlation
)
from app.services.recommendation import generate_recommendation, compare_head_to_head
from app.models.schemas import CompanyInfo

def test_monthly_series_and_3m_ma():
    """Verify that monthly resampling selects month-end Adj Close and calculates 3M MA correctly."""
    dates = pd.date_range(start="2024-01-01", end="2024-06-30", freq="B")
    # Monotonically increasing prices
    prices = np.linspace(100, 200, len(dates))
    df = pd.DataFrame({"Adj Close": prices, "Close": prices}, index=dates)

    monthly = compute_monthly_series(df)
    assert len(monthly) == 6
    # First 2 months don't have enough history for 3M MA
    assert monthly[0].ma_3m is None
    assert monthly[1].ma_3m is None
    # 3rd month must have 3M MA equal to average of first 3 months
    expected_ma3 = round((monthly[0].adj_close + monthly[1].adj_close + monthly[2].adj_close) / 3.0, 2)
    assert abs(monthly[2].ma_3m - expected_ma3) < 0.05


def test_aligned_monthly_template_matches_manual_first_six_months():
    """Check aligned last-month closes and moving averages against hand arithmetic."""
    dates = pd.to_datetime([
        "2024-01-30", "2024-01-31", "2024-02-28", "2024-03-28",
        "2024-04-30", "2024-05-31", "2024-06-28",
    ])
    df_a = pd.DataFrame({"Adj Close": [10, 11, 12, 15, 18, 20, 24]}, index=dates)
    # Different last trading dates still align by YYYY-MM calendar month.
    df_b = pd.DataFrame(
        {"Adj Close": [20, 21, 19, 21, 25, 26, 30]},
        index=pd.to_datetime([
            "2024-01-29", "2024-01-31", "2024-02-27", "2024-03-29",
            "2024-04-29", "2024-05-30", "2024-06-27",
        ]),
    )

    points_a, points_b, table = build_monthly_table(df_a, df_b)

    expected_months = [f"2024-{month:02d}" for month in range(1, 7)]
    closes_a = [11.0, 12.0, 15.0, 18.0, 20.0, 24.0]
    closes_b = [21.0, 19.0, 21.0, 25.0, 26.0, 30.0]
    assert [row.month_year for row in table] == expected_months
    assert [row.company1_close for row in table] == closes_a
    assert [row.company2_close for row in table] == closes_b
    assert [row.company1_ma for row in table[:2]] == [None, None]
    assert [row.company2_ma for row in table[:2]] == [None, None]
    assert [row.company1_ma for row in table[2:]] == [12.67, 15.0, 17.67, 20.67]
    assert [row.company2_ma for row in table[2:]] == [20.33, 21.67, 24.0, 27.0]
    assert table[5].company1_ma_6m == 16.67
    assert table[5].company2_ma_6m == 23.67
    assert [point.month_year for point in points_a] == [point.month_year for point in points_b]


def test_volatility_and_drawdown_match_known_daily_returns():
    """Verify sample daily-return volatility and a 20% peak-to-trough drawdown."""
    dates = pd.date_range("2024-01-01", periods=4, freq="D")
    prices = pd.Series([100.0, 110.0, 88.0, 110.0], index=dates)
    returns = prices.pct_change().dropna()
    expected_volatility = float(returns.std(ddof=1) * np.sqrt(252) * 100.0)

    df = pd.DataFrame({"Adj Close": prices}, index=dates)
    metrics = compute_performance_metrics(df, risk_free_rate_pct=6.5)

    assert metrics.annualized_volatility_pct == round(expected_volatility, 2)
    assert metrics.max_drawdown_pct == 20.0
    assert metrics.drawdown_peak_date == "2024-01-02"
    assert metrics.drawdown_trough_date == "2024-01-03"
    assert metrics.drawdown_recovery_date == "2024-01-04"
    assert compute_max_drawdown_details(prices) == (
        20.0, "2024-01-02", "2024-01-03", "2024-01-04"
    )


def test_daily_moving_averages_require_full_windows():
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    prices = pd.Series(np.arange(1.0, 201.0), index=dates)
    assert compute_daily_mas(pd.DataFrame({"Adj Close": prices.iloc[:49]}))["dma_50"] is None
    assert compute_daily_mas(pd.DataFrame({"Adj Close": prices.iloc[:199]}))["dma_200"] is None
    assert compute_daily_mas(pd.DataFrame({"Adj Close": prices})) == {
        "dma_50": 175.5,
        "price_vs_50_dma_status": "ABOVE",
        "price_vs_50_dma_pct": round((200.0 - 175.5) / 175.5 * 100.0, 2),
        "dma_200": 100.5,
        "price_vs_200_dma_status": "ABOVE",
        "price_vs_200_dma_pct": round((200.0 - 100.5) / 100.5 * 100.0, 2),
    }

def test_performance_metrics_cagr_and_volatility():
    """Verify CAGR, Annualized Volatility, and Max Drawdown calculations."""
    dates = pd.date_range(start="2022-01-01", end="2024-01-01", freq="B")
    # Base price 100 growing to 200 over exactly 2 years (total return 100%, CAGR ~ 41.4%)
    prices = np.linspace(100, 200, len(dates))
    df = pd.DataFrame({"Adj Close": prices, "Close": prices, "Volume": 1000}, index=dates)

    metrics = compute_performance_metrics(df, risk_free_rate_pct=6.5)
    assert metrics.current_price == 200.0
    assert metrics.total_return_pct > 99.0
    assert metrics.cagr_pct > 35.0  # Approx 41%
    assert metrics.max_drawdown_pct == 0.0  # Monotonically rising has zero drawdown

def test_overlay_and_correlation():
    """Verify that both stocks are rebased to 100 on start date and correlation is computed."""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="B")
    df_a = pd.DataFrame({"Adj Close": np.linspace(100, 200, 100)}, index=dates)
    df_b = pd.DataFrame({"Adj Close": np.linspace(500, 1000, 100)}, index=dates)

    overlay, corr = compute_overlay_and_correlation(df_a, df_b)
    assert len(overlay) > 0
    # Both start at 100
    assert overlay[0].company_a_rebased == 100.0
    assert overlay[0].company_b_rebased == 100.0
    # Perfect linear correlation
    assert corr == 1.0

def test_recommendation_and_head_to_head():
    """Verify that scoring assigns BUY/HOLD/AVOID and produces a head-to-head winner."""
    dates = pd.date_range(start="2024-01-01", periods=150, freq="B")
    df_high = pd.DataFrame({"Adj Close": np.linspace(100, 250, 150), "Close": np.linspace(100, 250, 150)}, index=dates)
    df_low = pd.DataFrame({"Adj Close": np.linspace(100, 80, 150), "Close": np.linspace(100, 80, 150)}, index=dates)

    m_high = compute_performance_metrics(df_high)
    m_low = compute_performance_metrics(df_low)

    rec_high = generate_recommendation(m_high, "High Performer")
    rec_low = generate_recommendation(m_low, "Low Performer")

    assert rec_high.action in ["BUY", "HOLD"]
    assert rec_low.action in ["HOLD", "AVOID"]
    assert rec_high.score > rec_low.score

    info_a = CompanyInfo(ticker="HIGH", name="High Performer")
    info_b = CompanyInfo(ticker="LOW", name="Low Performer")

    h2h = compare_head_to_head(info_a, m_high, rec_high, info_b, m_low, rec_low)
    assert h2h.winner_ticker == "HIGH"

    comparison = build_comparison_object(
        info_a.name, info_a.ticker, m_high,
        info_b.name, info_b.ticker, m_low,
    )
    keys = {metric.metric_key for metric in comparison.metrics}
    assert {"monthly_return_std_pct", "best_day_return_pct", "beta_nifty", "price_vs_200_dma_pct"} <= keys
    assert 5 <= len(comparison.sentences) <= 8
