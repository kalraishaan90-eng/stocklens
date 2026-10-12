import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from app.models.schemas import DataQualityReport, DataQualityGap

def clean_price_data(
    df: Optional[pd.DataFrame],
    max_ffill_days: int = 3,
    short_history_threshold_days: int = 350
) -> Tuple[pd.DataFrame, DataQualityReport]:
    """
    Cleans OHLCV financial price data:
    1. Ensures sorted, timezone-naive DatetimeIndex.
    2. Drops rows where all price data is NaN.
    3. Forward-fills missing prices for at most `max_ffill_days` (3 trading days).
    4. Drops any remaining NaN price rows.
    5. Detects and flags date gaps (>3 missing business days).
    6. Produces a DataQualityReport summarizing rows, date bounds, missing days, and gaps.
    """
    if df is None or df.empty:
        empty_report = DataQualityReport(
            rows=0,
            first_date=None,
            last_date=None,
            missing_days=0,
            has_gaps=False,
            gaps=[],
            is_restructured_or_short=True
        )
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"]), empty_report

    df_clean = df.copy()

    # 1. Normalize index to timezone-naive datetime
    if not isinstance(df_clean.index, pd.DatetimeIndex):
        df_clean.index = pd.to_datetime(df_clean.index)

    if getattr(df_clean.index, "tz", None) is not None:
        # Keep the exchange-local wall-clock date. tz_convert(None) would shift
        # IST-midnight timestamps back to the previous UTC calendar day, which
        # mislabels every trading day (and month-end closes) by one day.
        df_clean.index = df_clean.index.tz_localize(None)

    # Sort index chronologically and remove any duplicates
    df_clean = df_clean.sort_index()
    df_clean = df_clean[~df_clean.index.duplicated(keep="first")]

    # Normalize columns
    col_mapping = {c: c.capitalize() for c in df_clean.columns}
    df_clean.rename(columns=col_mapping, inplace=True)

    # If 'Adj close' present, ensure standard column naming
    for col in list(df_clean.columns):
        if col.lower() in ("adj close", "adjclose", "adjusted close"):
            df_clean["Adj Close"] = df_clean[col]

    price_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df_clean.columns]
    if not price_cols:
        # If no standard columns, check if only a single price column exists
        if len(df_clean.columns) >= 1:
            first_col = df_clean.columns[0]
            df_clean["Close"] = df_clean[first_col]
            df_clean["Open"] = df_clean["Close"]
            df_clean["High"] = df_clean["Close"]
            df_clean["Low"] = df_clean["Close"]
            price_cols = ["Open", "High", "Low", "Close"]

    if "Volume" not in df_clean.columns:
        df_clean["Volume"] = 0

    # 2. Forward-fill at most max_ffill_days (3 trading days)
    cols_to_fill = price_cols.copy()
    if "Adj Close" in df_clean.columns:
        cols_to_fill.append("Adj Close")
    df_clean[cols_to_fill] = df_clean[cols_to_fill].ffill(limit=max_ffill_days)

    # 3. Drop rows that still have NaN in Close (e.g. leading NaNs or exceeding 3-day ffill limit)
    df_clean = df_clean.dropna(subset=["Close"])
    for c in price_cols:
        df_clean[c] = df_clean[c].fillna(df_clean["Close"])
    df_clean["Volume"] = df_clean["Volume"].fillna(0).astype(int)

    if df_clean.empty:
        empty_report = DataQualityReport(
            rows=0,
            first_date=None,
            last_date=None,
            missing_days=0,
            has_gaps=False,
            gaps=[],
            is_restructured_or_short=True
        )
        return df_clean, empty_report

    # 4. Detect and flag gaps between consecutive trading days
    gaps: List[DataQualityGap] = []
    dates = df_clean.index

    for i in range(1, len(dates)):
        prev_dt = dates[i - 1]
        curr_dt = dates[i]
        cal_days = (curr_dt - prev_dt).days
        
        # Calculate missing business days between dates (exclusive)
        if cal_days > 1:
            bus_range = pd.bdate_range(prev_dt + pd.Timedelta(days=1), curr_dt - pd.Timedelta(days=1))
            missing_bus_days = len(bus_range)
            # A gap is flagged if 3 or more business days are missing
            if missing_bus_days >= 3:
                gaps.append(
                    DataQualityGap(
                        from_date=prev_dt.strftime("%Y-%m-%d"),
                        to_date=curr_dt.strftime("%Y-%m-%d"),
                        calendar_days=cal_days,
                        business_days_missing=missing_bus_days
                    )
                )

    first_date_str = dates[0].strftime("%Y-%m-%d")
    last_date_str = dates[-1].strftime("%Y-%m-%d")

    # Missing business days over the entire span compared to expected business days
    expected_bus_days = len(pd.bdate_range(dates[0], dates[-1]))
    actual_rows = len(df_clean)
    missing_days_count = max(0, expected_bus_days - actual_rows)

    is_short = actual_rows < short_history_threshold_days

    quality_report = DataQualityReport(
        rows=actual_rows,
        first_date=first_date_str,
        last_date=last_date_str,
        missing_days=missing_days_count,
        has_gaps=len(gaps) > 0,
        gaps=gaps,
        is_restructured_or_short=is_short
    )

    return df_clean, quality_report
