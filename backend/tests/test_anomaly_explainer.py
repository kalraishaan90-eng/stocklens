import pytest
import numpy as np
import pandas as pd
from app.services.anomaly_detector import detect_price_anomalies, detect_recent_change
from app.services.market_classifier import classify_event_market_level
from app.services.gemini_analyzer import (
    validate_ai_explanation,
    generate_rule_based_fallback,
    compute_confidence
)

def create_synthetic_stock_df(days: int = 150, base_price: float = 100.0) -> pd.DataFrame:
    """Creates a predictable time series of daily stock data."""
    dates = pd.date_range(end="2026-03-31", periods=days, freq="B")
    prices = [base_price]
    for _ in range(days - 1):
        prices.append(prices[-1] * (1.0 + np.random.normal(0, 0.01)))
    
    df = pd.DataFrame({
        "Open": prices,
        "High": [p * 1.01 for p in prices],
        "Low": [p * 0.99 for p in prices],
        "Close": prices,
        "Adj Close": prices,
        "Volume": [1000000] * days
    }, index=dates)
    return df

# --- 1. Spike Detection Tests ---

def test_spike_detection_thresholds_and_consecutive_merge():
    """Verify that moves >= 5% or >= 2.5 std are flagged, consecutive days are merged, and top 6 kept."""
    np.random.seed(42)
    df = create_synthetic_stock_df(120, base_price=200.0)
    
    # Inject an isolated 7% spike on day 70 by stepping up all subsequent prices
    df.loc[df.index[70]:, "Adj Close"] *= 1.07
    df.loc[df.index[70]:, "Close"] *= 1.07
    df.loc[df.index[70], "Volume"] = 2500000  # 2.5x volume
    df.loc[df.index[70], "Open"] = df.loc[df.index[69], "Close"] * 1.02  # 2% gap up
    
    # Inject consecutive 2-day drop on days 85 and 86 (-5% then -6%)
    df.loc[df.index[85]:, "Adj Close"] *= 0.95
    df.loc[df.index[85]:, "Close"] *= 0.95
    df.loc[df.index[86]:, "Adj Close"] *= 0.94
    df.loc[df.index[86]:, "Close"] *= 0.94

    
    events = detect_price_anomalies(df, max_events=6)
    assert len(events) >= 2
    assert len(events) <= 6

    # Verify isolated jump
    jump_event = next((e for e in events if e["primary_date"] == df.index[70].strftime("%Y-%m-%d")), None)
    assert jump_event is not None
    assert jump_event["direction"] == "jump"
    assert jump_event["change_pct"] >= 6.0
    assert jump_event["volume_spike_multiplier"] >= 2.0
    assert jump_event["gap_pct"] >= 1.5

    # Verify merged consecutive drop
    merged_event = next((e for e in events if df.index[85].strftime("%Y-%m-%d") in e["date"]), None)
    assert merged_event is not None
    assert merged_event["direction"] == "drop"
    # Cumulative drop of 5% followed by 6% is approx -10.7%
    assert merged_event["change_pct"] <= -9.0
    assert df.index[86].strftime("%Y-%m-%d") in merged_event["end_date"]

# --- 2. Market Classification Tests ---

def test_market_classification_market_wide():
    """If NIFTY moved sharply and residual is small -> 'Market-wide move'."""
    # NIFTY drops -3.0%, Stock drops -3.5%, Beta = 1.0 -> Residual = -0.5%
    ctx = classify_event_market_level(
        stock_return=-3.5,
        nifty_return=-3.0,
        sector_return=-2.0,
        beta_nifty=1.0,
        beta_sector=1.0,
        sector_name="NIFTY Energy"
    )
    assert ctx["classification"] == "Market-wide move"
    assert ctx["stock_return_pct"] == -3.5
    assert ctx["nifty_return_pct"] == -3.0
    assert ctx["sector_return_pct"] == -2.0
    assert abs(ctx["residual_pct"]) <= 1.0
    assert "market-wide" in ctx["explanation_factor"].lower()

def test_market_classification_sector_wide():
    """If Sector moved sharply and residual vs sector is small -> 'Sector-wide move'."""
    # Stock rallies +5.0%, Sector rallies +4.5%, NIFTY only +0.5%, Beta = 1.0
    ctx = classify_event_market_level(
        stock_return=5.0,
        nifty_return=0.5,
        sector_return=4.5,
        beta_nifty=1.0,
        beta_sector=1.0,
        sector_name="NIFTY IT Index"
    )
    assert ctx["classification"] == "Sector-wide move"
    assert ctx["stock_return_pct"] == 5.0
    assert ctx["nifty_return_pct"] == 0.5
    assert ctx["sector_return_pct"] == 4.5
    assert "sector-wide" in ctx["explanation_factor"].lower()

def test_market_classification_company_specific():
    """If neither market nor sector explain the move -> 'Company-specific move'."""
    # Stock moves +8.0% while NIFTY is -0.2% and Sector is +0.1%
    ctx = classify_event_market_level(
        stock_return=8.0,
        nifty_return=-0.2,
        sector_return=0.1,
        beta_nifty=1.0,
        beta_sector=1.0,
        sector_name="NIFTY Consumption"
    )
    assert ctx["classification"] == "Company-specific move"
    assert ctx["residual_pct"] > 7.0
    assert "company-specific" in ctx["explanation_factor"].lower()

# --- 3. JSON Validation & Integrity Tests ---

def test_validate_ai_explanation_valid():
    valid_payload = {
        "summary": "Reliance rose 5.3% due to robust quarterly petrochemical earnings. The move was company-specific with heavy volume.",
        "likely_reasons": ["Quarterly Earnings Beat", "Volume Surge (2.2x)"],
        "confidence": "High",
        "sources_used": ["Economic Times", "NSE Market Trading Data"]
    }
    res = validate_ai_explanation(valid_payload)
    assert res is not None
    assert res["confidence"] == "High"
    assert len(res["likely_reasons"]) == 2
    assert res["is_ai_generated"] is True

def test_validate_ai_explanation_invalid():
    # Missing confidence
    assert validate_ai_explanation({"summary": "Stock went up", "likely_reasons": []}) is None
    # Bad confidence value
    assert validate_ai_explanation({
        "summary": "Stock went up",
        "likely_reasons": ["Reason"],
        "confidence": "SuperHigh",
        "sources_used": ["Reuters"]
    }) is None
    # Missing summary
    assert validate_ai_explanation({
        "summary": "",
        "likely_reasons": ["Reason"],
        "confidence": "Medium",
        "sources_used": ["Reuters"]
    }) is None

# --- 4. Rule-Based Fallback Tests & Confidence Logic ---

def test_fallback_explanation_label_and_confidence():
    """Fallback must be clearly labelled 'Auto-generated without AI' and follow confidence rules."""
    # High confidence: Company-specific + news + volume spike >= 1.5x
    fb_high = generate_rule_based_fallback(
        company_name="Titan Company",
        ticker="TITAN.NS",
        event_date="2025-07-08",
        change_pct=-5.85,
        direction="drop",
        vol_multiplier=3.2,
        gap_pct=-2.3,
        market_context={"classification": "Company-specific move", "nifty_return_pct": 0.2, "residual_pct": -6.0},
        headlines=[{"title": "Titan Q1 jewelry sales growth moderates below estimates", "source": "CNBC-TV18"}],
        corporate_events=[]
    )
    assert "[Auto-generated without AI]" in fb_high["summary"]
    assert fb_high["confidence"] == "High"
    assert fb_high["is_ai_generated"] is False
    assert any("Titan Q1 jewelry" in r for r in fb_high["likely_reasons"])

    # Low confidence: No news found
    fb_low = generate_rule_based_fallback(
        company_name="Test Company",
        ticker="TEST.NS",
        event_date="2025-01-10",
        change_pct=6.5,
        direction="jump",
        vol_multiplier=1.1,
        gap_pct=0.5,
        market_context={"classification": "Company-specific move", "nifty_return_pct": 0.1, "residual_pct": 6.4},
        headlines=[],
        corporate_events=[]
    )
    assert "[Auto-generated without AI]" in fb_low["summary"]
    assert fb_low["confidence"] == "Low"
    assert "headlines do not explain" in fb_low["summary"].lower()

# --- 5. Recent Change Mode Tests ---

def test_recent_change_mode_notable():
    np.random.seed(123)
    df = create_synthetic_stock_df(50, base_price=100.0)
    # Inject a 4% move over the last 5 days
    df.loc[df.index[-1], "Adj Close"] = df.loc[df.index[-5], "Adj Close"] * 1.045
    df.loc[df.index[-1], "Close"] = df.loc[df.index[-1], "Adj Close"]
    
    recent = detect_recent_change(df, threshold_pct=2.5)
    assert recent is not None
    assert recent["is_recent"] is True
    assert recent["change_pct"] >= 4.0
    assert "Last 5 Days" in recent["date"]

def test_recent_change_mode_flat():
    df = create_synthetic_stock_df(50, base_price=100.0)
    # Make the last 8 days flat (0% change)
    for i in range(-8, 0):
        df.loc[df.index[i], "Adj Close"] = 100.0
        df.loc[df.index[i], "Close"] = 100.0
    
    recent = detect_recent_change(df, threshold_pct=2.5)
    assert recent is None


# --- 6. Grounding / Hallucination Rejection (Hard Rule 1) ---

def _facts(headlines=None, corp_events=None):
    return {
        "company_name": "Reliance Industries Limited",
        "ticker": "RELIANCE.NS",
        "event_date": "2026-06-10",
        "price_change_pct": 7.3,
        "stock_return_pct": 7.3,
        "nifty_50_return_pct": 0.4,
        "sector_return_pct": 1.1,
        "residual_move_pct": 6.5,
        "gap_at_open_pct": 0.8,
        "headlines": headlines if headlines is not None else [
            {"title": "Reliance Industries shares rise on stake sale in petrochemical arm",
             "source": "Moneycontrol", "date": "2026-06-10"}
        ],
        "corporate_events": corp_events or [],
    }


def _candidate(summary, reasons=None, confidence="Medium", sources=None):
    return {
        "summary": summary,
        "likely_reasons": reasons if reasons is not None else ["Stock gained on the supplied headlines"],
        "confidence": confidence,
        "sources_used": sources if sources is not None else ["Moneycontrol"],
    }


def test_validator_accepts_fully_grounded_explanation():
    """A summary whose numbers and sources all come from the facts passes."""
    res = validate_ai_explanation(
        _candidate(
            "Reliance Industries gained 7.3% versus a 0.4% NIFTY 50 move, following the reported stake sale.",
            reasons=["Stock gained 7.3% while NIFTY 50 moved 0.4%"],
        ),
        _facts(),
    )
    assert res is not None
    assert res["is_ai_generated"] is True


def test_validator_rejects_fabricated_percentage():
    """Any percentage not present in the facts payload must be rejected."""
    res = validate_ai_explanation(
        _candidate("Reliance Industries shares surged 15.2% in early trade."),
        _facts(),
    )
    assert res is None


def test_validator_rejects_percentage_in_likely_reasons():
    """Grounding applies to likely_reasons too, not just the summary."""
    res = validate_ai_explanation(
        _candidate(
            "Reliance Industries gained 7.3% following the reported stake sale.",
            reasons=["Sector peers also rose around 9%"],
        ),
        _facts(),
    )
    assert res is None


def test_validator_rejects_unmentioned_corporate_action():
    """An earnings/dividend/order claim is rejected when no supplied headline mentions it."""
    no_earnings_headline = [
        {"title": "Reliance Industries shares edge higher in weak market", "source": "Economic Times"}
    ]
    res = validate_ai_explanation(
        _candidate("Reliance Industries jumped after announcing strong quarterly earnings.",
                   sources=["Economic Times"]),
        _facts(headlines=no_earnings_headline),
    )
    assert res is None


def test_validator_rejects_fabricated_news_source():
    """sources_used must come from the supplied headlines."""
    res = validate_ai_explanation(
        _candidate("Reliance Industries gained 7.3% following the reported stake sale.",
                   sources=["Bloomberg Terminal"]),
        _facts(),
    )
    assert res is None


def test_validator_rejects_fabricated_currency_amount():
    """Currency amounts absent from the facts are rejected (summary and reasons)."""
    res = validate_ai_explanation(
        _candidate("Reliance Industries bagged a Rs 2,500 crore order, driving the stock higher."),
        _facts(),
    )
    assert res is None
    res2 = validate_ai_explanation(
        _candidate(
            "Reliance Industries gained 7.3% following the reported stake sale.",
            reasons=["Company won a Rs 500 crore contract"],
        ),
        _facts(),
    )
    assert res2 is None

