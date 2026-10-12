import time
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from app.config import PRICES_CACHE_DIR, PRICE_CACHE_TTL_SECONDS, SECTOR_INDEX_MAP
from app.services.cache import get_disk_price_cache, set_disk_price_cache
from app.services.stock_data import (
    fetch_ticker_prices,
    fetch_index_series,
    extract_company_info,
    safe_float,
    MIN_INDEX_ROWS
)
from app.models.schemas import PriceResponse, CompanyInfo, DataQualityReport

def test_safe_float_helper():
    """Verify safe_float returns rounded floats or None on invalid numbers."""
    assert safe_float(25.67891) == 25.6789
    assert safe_float("12.34") == 12.34
    assert safe_float(None) is None
    assert safe_float(float("nan")) is None
    assert safe_float(float("inf")) is None
    assert safe_float("invalid_str") is None


def test_extract_company_info_null_safety():
    """Verify company info extraction handles missing, null, and non-numeric fields safely."""
    raw_info = {
        "longName": "Test Aeronautics Ltd",
        "sector": "Industrials",
        "marketCap": None,
        "trailingPE": "NaN",
        "dividendYield": 0.0125,
        "beta": None
    }
    comp_info = extract_company_info("TEST.NS", raw_info)
    assert comp_info.name == "Test Aeronautics Ltd"
    assert comp_info.sector == "Industrials"
    assert comp_info.market_cap is None
    assert comp_info.pe_ratio is None
    assert comp_info.dividend_yield == 0.0125
    assert comp_info.beta is None
    assert comp_info.exchange == "NSE"


def test_disk_cache_ttl_and_stale_detection(tmp_path):
    """Verify cache writes to disk and respects 6-hour TTL."""
    dummy_ticker = "TEST_STOCK_TTL.NS"
    payload = {"sample_key": "sample_val"}

    # 1. Write fresh cache with 10 seconds TTL
    set_disk_price_cache(dummy_ticker, payload, ttl_seconds=10)
    data, is_stale = get_disk_price_cache(dummy_ticker)
    assert data is not None
    assert data["sample_key"] == "sample_val"
    assert is_stale is False

    # 2. Write expired cache (ttl = -10 seconds)
    set_disk_price_cache(dummy_ticker, payload, ttl_seconds=-10)
    data_expired, is_stale_expired = get_disk_price_cache(dummy_ticker)
    assert data_expired is not None
    assert is_stale_expired is True  # Stale data flag is set!


@pytest.mark.asyncio
async def test_stale_cache_served_when_live_fetch_fails():
    """
    Verify that when yfinance live fetch fails (e.g. rate limit, network down),
    the system falls back to serving stale cached data and sets stale_data=True.
    """
    ticker = "TEST_STALE_FALLBACK.NS"
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    
    # Pre-populate disk cache with valid historical records
    sample_response = {
        "ticker": ticker,
        "company_info": {
            "ticker": ticker,
            "name": "Fallback Motors Ltd",
            "sector": "Consumer Cyclical",
            "industry": "Automotive",
            "currency": "INR",
            "exchange": "NSE"
        },
        "data_quality": {
            "rows": 10,
            "first_date": "2024-01-01",
            "last_date": "2024-01-12",
            "missing_days": 0,
            "has_gaps": False,
            "gaps": [],
            "is_restructured_or_short": True
        },
        "stale_data": False,
        "cached": True,
        "warning": None,
        "restructuring_note": None,
        "prices": [
            {"date": d.strftime("%Y-%m-%d"), "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000}
            for d in dates
        ],
        "benchmark": None,
        "sector_index": None
    }
    
    # Store in disk cache with an expired TTL
    set_disk_price_cache(ticker, sample_response, ttl_seconds=-100)

    # Mock yfinance to simulate network or server failure
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.side_effect = RuntimeError("Yahoo Finance 503 Service Unavailable")

        # Fetch prices
        res = await fetch_ticker_prices(ticker, force_live=True)
        assert res.ticker == ticker
        assert res.stale_data is True
        assert res.cached is True
        assert "Live market data fetch failed" in (res.warning or "")
        assert len(res.prices) == 10
        assert res.company_info.name == "Fallback Motors Ltd"


def test_sector_index_config_mapping():
    """Verify sector -> index configuration mapping has expected indices."""
    assert SECTOR_INDEX_MAP["Financial Services"] == "^NSEBANK"
    assert SECTOR_INDEX_MAP["Technology"] == "^CNXIT"
    assert SECTOR_INDEX_MAP["Automobile"] == "^CNXAUTO"
    assert SECTOR_INDEX_MAP["Energy"] == "^CNXENERGY"
    assert SECTOR_INDEX_MAP["Real Estate"] == "^CNXREALTY"
    assert SECTOR_INDEX_MAP["Consumer Defensive"] == "^CNXFMCG"
    assert SECTOR_INDEX_MAP["Basic Materials"] == "^CNXMETAL"
    assert SECTOR_INDEX_MAP["Industrials"] == "^CNXINFRA"


@pytest.mark.asyncio
async def test_degenerate_index_series_not_cached():
    """
    Verify that a truncated index feed (e.g. Yahoo serving a single point for
    ^CNX* sector indices) is treated as unusable: no series returned, nothing
    poisoned into the disk cache, and no stale series served either.
    """
    ticker = "^CNXDEGENERATE"
    degenerate_df = pd.DataFrame(
        {"Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.0], "Volume": [0]},
        index=pd.to_datetime(["2026-10-01"])
    )

    # Ensure no pre-existing cache for this symbol
    cache_file = PRICES_CACHE_DIR / "_IDX_CNXDEGENERATE.json"
    if cache_file.exists():
        cache_file.unlink()

    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = degenerate_df
        series = await fetch_index_series(ticker, days=30)

    assert series is None  # 1-row series must not be served
    cached, _ = get_disk_price_cache(ticker)
    assert cached is None  # and must not be written to disk cache

    # A healthy series (>= MIN_INDEX_ROWS) is still returned and cached
    healthy_df = pd.DataFrame(
        {
            "Open": list(range(100, 120)),
            "High": list(range(101, 121)),
            "Low": list(range(99, 119)),
            "Close": list(range(102, 122)),
            "Volume": [1000] * 20,
        },
        index=pd.bdate_range("2026-09-01", periods=20)
    )
    assert MIN_INDEX_ROWS <= 20
    with patch("yfinance.Ticker") as mock_ticker:
        mock_ticker.return_value.history.return_value = healthy_df
        series_ok = await fetch_index_series(ticker, days=30)
    assert series_ok is not None
    assert len(series_ok.records) == 20
    cached_ok, stale_ok = get_disk_price_cache(ticker)
    assert cached_ok is not None and stale_ok is False
