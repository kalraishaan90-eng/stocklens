import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from app.services.data_cleaner import clean_price_data

def test_timezone_naive_and_sorted():
    """Verify clean_price_data converts tz-aware index to tz-naive and sorts chronologically."""
    # Create unsorted, timezone-aware DatetimeIndex
    dates = pd.to_datetime(["2024-03-05 09:15:00+05:30", "2024-03-01 09:15:00+05:30", "2024-03-04 09:15:00+05:30"])
    df = pd.DataFrame({
        "Open": [100.0, 95.0, 98.0],
        "High": [105.0, 99.0, 102.0],
        "Low": [98.0, 94.0, 97.0],
        "Close": [103.0, 97.0, 100.0],
        "Volume": [1000, 2000, 1500]
    }, index=dates)

    cleaned_df, report = clean_price_data(df)
    
    # Assert index is timezone-naive
    assert cleaned_df.index.tz is None
    # Assert index is strictly sorted
    assert list(cleaned_df.index) == sorted(list(cleaned_df.index))
    assert report.rows == 3
    assert report.first_date == "2024-03-01"
    assert report.last_date == "2024-03-05"


def test_ffill_at_most_3_days_and_drop_excess_nans():
    """Verify forward-fill is bounded at 3 trading days, and remaining NaNs are dropped."""
    # 7 consecutive business days
    dates = pd.date_range("2024-01-01", periods=7, freq="B")
    # Day 0: valid (100)
    # Day 1: NaN (fill 1)
    # Day 2: NaN (fill 2)
    # Day 3: NaN (fill 3)
    # Day 4: NaN (exceeds limit 3, should be dropped)
    # Day 5: NaN (exceeds limit 3, should be dropped)
    # Day 6: valid (110)
    df = pd.DataFrame({
        "Open": [100.0, np.nan, np.nan, np.nan, np.nan, np.nan, 110.0],
        "High": [102.0, np.nan, np.nan, np.nan, np.nan, np.nan, 112.0],
        "Low": [99.0, np.nan, np.nan, np.nan, np.nan, np.nan, 109.0],
        "Close": [101.0, np.nan, np.nan, np.nan, np.nan, np.nan, 111.0],
        "Volume": [5000, 0, 0, 0, 0, 0, 8000]
    }, index=dates)

    cleaned_df, report = clean_price_data(df, max_ffill_days=3)

    # Days 0, 1, 2, 3 should be present (filled with day 0 value 101.0)
    # Days 4 and 5 should be dropped
    # Day 6 should be present
    assert len(cleaned_df) == 5
    assert cleaned_df.loc[dates[1], "Close"] == 101.0
    assert cleaned_df.loc[dates[2], "Close"] == 101.0
    assert cleaned_df.loc[dates[3], "Close"] == 101.0
    assert dates[4] not in cleaned_df.index
    assert dates[5] not in cleaned_df.index
    assert cleaned_df.loc[dates[6], "Close"] == 111.0


def test_detect_and_flag_gaps():
    """Verify date gaps exceeding 3 missing business days are flagged in the report."""
    # Create two dates separated by 2 weeks (10 missing business days)
    d1 = pd.Timestamp("2024-02-01")
    d2 = pd.Timestamp("2024-02-15")
    df = pd.DataFrame({
        "Open": [100.0, 120.0],
        "High": [105.0, 125.0],
        "Low": [95.0, 115.0],
        "Close": [102.0, 122.0],
        "Volume": [1000, 2000]
    }, index=[d1, d2])

    cleaned_df, report = clean_price_data(df)

    assert report.has_gaps is True
    assert len(report.gaps) >= 1
    gap = report.gaps[0]
    assert gap.from_date == "2024-02-01"
    assert gap.to_date == "2024-02-15"
    assert gap.business_days_missing >= 3
    assert gap.calendar_days == 14


def test_short_history_detection():
    """Verify that datasets under short history threshold are flagged."""
    dates = pd.date_range("2024-01-01", periods=150, freq="B")
    df = pd.DataFrame({
        "Open": np.linspace(100, 150, 150),
        "High": np.linspace(105, 155, 150),
        "Low": np.linspace(95, 145, 150),
        "Close": np.linspace(102, 152, 150),
        "Volume": 1000
    }, index=dates)

    cleaned_df, report = clean_price_data(df, short_history_threshold_days=350)
    assert report.is_restructured_or_short is True
    assert report.rows == 150


def test_empty_dataframe_handling():
    """Verify empty or None DataFrame is handled gracefully without crashing."""
    df_empty, rep_empty = clean_price_data(None)
    assert rep_empty.rows == 0
    assert rep_empty.first_date is None
    assert df_empty.empty


def test_ist_midnight_keeps_calendar_date():
    """Regression: NSE timestamps are IST midnight. Removing the timezone must
    keep the exchange-local calendar date; converting to UTC first would shift
    every trading day (and month-end closes) back by one calendar day."""
    dates = pd.to_datetime([
        "2026-09-29 00:00:00+05:30",
        "2026-09-30 00:00:00+05:30",
        "2026-10-01 00:00:00+05:30",
    ])
    df = pd.DataFrame({
        "Open": [100.0, 101.0, 99.0],
        "High": [102.0, 103.0, 101.0],
        "Low": [99.0, 100.0, 98.0],
        "Close": [101.0, 102.0, 100.0],
        "Volume": [1000, 1100, 1200],
    }, index=dates)

    cleaned, report = clean_price_data(df)

    got = [d.strftime("%Y-%m-%d") for d in cleaned.index]
    assert got == ["2026-09-29", "2026-09-30", "2026-10-01"]
    assert report.last_date == "2026-10-01"
    assert cleaned.index.tz is None
