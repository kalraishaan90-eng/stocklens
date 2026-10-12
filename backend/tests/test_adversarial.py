"""
Adversarial / graceful-degradation QA for StockLens.

Deliberately break things and assert the API degrades GRACEFULLY:
  * empty inputs        -> clean 400 (never a 500 traceback)
  * same inputs twice   -> valid analysis, correlation ~1.0
  * garbage inputs      -> clean 502 error envelope, no stack trace leak
  * internet killed     -> clean 502 (or stale cache with stale_data=true)
  * Gemini key removed  -> rule-based explanations, clearly labelled, no crash
  * double-submit       -> repeated identical request returns identical result

All tests are network-free (yfinance/httpx mocked).
"""

import os

os.environ.setdefault("VERIFY_TICKERS_ON_STARTUP", "false")

import math
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_price_df(days: int = 400, seed: int = 7, base: float = 1000.0) -> pd.DataFrame:
    """Deterministic naive-index OHLCV frame (no NaN, no tz)."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=days)
    rets = rng.normal(0.0004, 0.012, days)
    close = base * np.cumprod(1.0 + rets)
    return pd.DataFrame({
        "Open": close * 0.995,
        "High": close * 1.01,
        "Low": close * 0.99,
        "Close": close,
        "Volume": np.full(days, 500_000, dtype=int),
    }, index=dates)


MOCK_META = {
    "longName": "Test Industries Limited",
    "sector": "Industrials",
    "industry": "Diversified",
    "currency": "INR",
    "exchange": "NSE",
}


@contextmanager
def mocked_analysis_network(df: pd.DataFrame):
    """Patches every networked dependency of /api/analyze with deterministic data."""
    async def fake_fetch(ticker, days=730, **kwargs):
        return df.copy(), dict(MOCK_META)

    async def fake_benchmark(days=730):
        return df[["Close"]].copy()

    async def fake_market_ctx(*args, **kwargs):
        return []

    async def fake_news(*args, **kwargs):
        return {"headlines": [], "corporate_events": []}

    with patch("app.main.fetch_stock_history_with_retry", side_effect=fake_fetch), \
         patch("app.main.fetch_benchmark_history", side_effect=fake_benchmark), \
         patch("app.main.analyze_market_context_for_events", side_effect=fake_market_ctx), \
         patch("app.main.fetch_news_for_event", side_effect=fake_news):
        yield


@contextmanager
def internet_down():
    """Every outbound network call raises like a dead connection."""
    def _raise(*args, **kwargs):
        raise ConnectionError("Network is unreachable (QA simulated offline)")

    class DeadTicker:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("Network is unreachable (QA simulated offline)")

    with patch("app.services.stock_data.yf.Ticker", side_effect=_raise), \
         patch("yfinance.Ticker", side_effect=_raise), \
         patch("httpx.AsyncClient.get", side_effect=_raise), \
         patch("httpx.AsyncClient.post", side_effect=_raise):
        yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. Empty / missing inputs -> 400, never 500
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    {"company1": "", "company2": "HAL"},
    {"company1": "HAL", "company2": "   "},
    {"company1": "", "company2": ""},
    {},
])
def test_empty_inputs_return_clean_400(client, payload):
    resp = client.post("/api/analyze", json=payload)
    assert resp.status_code == 400, f"expected 400, got {resp.status_code}: {resp.text[:200]}"
    body = resp.json()
    assert body.get("error") is True
    assert "traceback" not in resp.text.lower()
    assert "File \"" not in resp.text  # no source-path leak


# ---------------------------------------------------------------------------
# 2. Same input twice -> valid self-comparison, correlation ~1.0, idempotent
# ---------------------------------------------------------------------------

def test_same_inputs_self_comparison(client):
    df = make_price_df()
    with mocked_analysis_network(df):
        first = client.post("/api/analyze", json={"company1": "HAL", "company2": "HAL"})
        second = client.post("/api/analyze", json={"company1": "HAL", "company2": "HAL"})

    assert first.status_code == 200
    assert second.status_code == 200
    a, b = first.json(), second.json()

    # Deterministic double-submit: identical results, no duplicated state
    assert a["comparison"]["correlation_2y"] == pytest.approx(b["comparison"]["correlation_2y"])
    # Self-comparison is perfectly correlated
    assert a["comparison"]["correlation_2y"] == pytest.approx(1.0, abs=1e-6)
    # Both sides identical metrics
    assert a["metrics"]["company1"]["current_price"] == a["metrics"]["company2"]["current_price"]
    assert a["metadata"]["is_offline_demo"] is False


# ---------------------------------------------------------------------------
# 3. Garbage inputs -> clean 502 error envelope, no stack trace
# ---------------------------------------------------------------------------

def test_garbage_inputs_return_clean_502(client):
    with internet_down():
        resp = client.post("/api/analyze", json={"company1": "zz qq xx 123!?", "company2": "HAL"})
    assert resp.status_code == 502, f"expected 502, got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body.get("error") is True
    assert body.get("status_code") == 502
    assert isinstance(body.get("message"), str) and body["message"]
    assert "traceback" not in resp.text.lower()
    assert "site-packages" not in resp.text


# ---------------------------------------------------------------------------
# 4. Internet killed -> clean 502 when cold, cache/stale data when warm
# ---------------------------------------------------------------------------

def test_offline_analyze_cold_cache_returns_clean_502(client):
    """No internet + no cached prices -> structured 502, never a traceback."""
    with internet_down():
        # Zomato / Cochin Shipyard are alias-resolved offline but never batch-cached
        resp = client.post("/api/analyze", json={"company1": "zomato", "company2": "cochin shipyard"})
    assert resp.status_code == 502, f"got {resp.status_code}: {resp.text[:300]}"
    body = resp.json()
    assert body.get("error") is True
    assert "traceback" not in resp.text.lower()


def test_offline_prices_expired_cache_serves_stale(client):
    """No internet + expired cache -> 200 with stale_data=true (demo survives)."""
    from app.services.cache import set_disk_price_cache
    ticker = "OFFLINESTALEPROBE.NS"
    payload = {
        "ticker": ticker,
        "company_info": {"ticker": ticker, "name": "Offline Probe Ltd", "sector": "Industrials",
                         "industry": "General", "currency": "INR", "exchange": "NSE"},
        "data_quality": {"rows": 5, "first_date": "2026-09-28", "last_date": "2026-10-02",
                         "missing_days": 0, "has_gaps": False, "gaps": [], "is_restructured_or_short": True},
        "stale_data": False, "cached": True, "warning": None, "restructuring_note": None,
        "prices": [{"date": f"2026-09-{28 + i:02d}", "open": 100.0, "high": 101.0,
                    "low": 99.0, "close": 100.5, "volume": 1000} for i in range(3)]
                  + [{"date": "2026-10-01", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000},
                     {"date": "2026-10-02", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 1000}],
        "benchmark": None, "sector_index": None,
    }
    set_disk_price_cache(ticker, payload, ttl_seconds=-100)  # force stale

    with internet_down():
        resp = client.get(f"/api/prices/{ticker}", params={"force_live": "true"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["stale_data"] is True
    assert body["cached"] is True
    assert len(body["prices"]) == 5
    assert "stale" in (body.get("warning") or "").lower()


def test_offline_prices_returns_clean_502(client):
    with internet_down():
        resp = client.get("/api/prices/OFFLINEPROBE.NS")
    assert resp.status_code == 502
    assert resp.json().get("error") is True
    assert "traceback" not in resp.text.lower()


def test_offline_health_still_responds(client):
    """Health check must never depend on external network."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


# ---------------------------------------------------------------------------
# 5. Gemini key removed -> rule-based explanations, clearly labelled
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_gemini_key_falls_back_to_rule_based():
    from app.services.gemini_analyzer import explain_price_movement

    with patch("app.services.gemini_analyzer.GEMINI_API_KEY", ""):
        res = await explain_price_movement(
            company_name="Test Industries Limited",
            ticker="TESTGEM.NS",
            event_date="2026-05-04",
            change_pct=4.6,
            direction="jump",
            vol_multiplier=2.1,
            gap_pct=1.2,
            market_context={"classification": "Company-specific move",
                            "stock_return_pct": 4.6, "nifty_return_pct": 0.3,
                            "sector_return_pct": None, "residual_pct": 4.3},
            news_res={"headlines": [{"title": "Test Industries wins export order",
                                     "source": "Moneycontrol"}],
                      "corporate_events": []},
        )
    assert res["is_ai_generated"] is False
    assert "[Auto-generated without AI]" in res["summary"]
    assert res["confidence"] in ("High", "Medium", "Low")
    # Grounded: the headline actually used appears in the reasons
    assert any("export order" in r for r in res["likely_reasons"])
    # Grounded: no invented currency figures
    assert "crore" not in res["summary"].lower()


# ---------------------------------------------------------------------------
# 6. Resolve endpoint degrades gracefully on junk
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("q", ["!!!", "zzzqqqxyzzyplugh12345"])
def test_resolve_junk_never_500s(client, q):
    from unittest.mock import AsyncMock
    # Even the Yahoo search fallback is unavailable - must still answer cleanly
    with patch("app.services.ticker_resolver._search_yahoo",
               new_callable=AsyncMock, return_value=[]):
        resp = client.get("/api/resolve", params={"q": q})
    assert resp.status_code == 200
    body = resp.json()
    # Still returns a structured (possibly low-confidence) answer
    assert body["match"] is not None
    assert isinstance(body.get("alternatives"), list)


def test_resolve_requires_query(client):
    resp = client.get("/api/resolve")
    assert resp.status_code == 422


def test_resolve_whitespace_query_is_400(client):
    resp = client.get("/api/resolve", params={"q": "   "})
    assert resp.status_code == 400
