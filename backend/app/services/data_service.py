"""
Data Service Stub for StockLens.
Responsible for fetching historical daily adjusted close and volume data from financial APIs (Yahoo Finance/NSE).
"""
from typing import Dict, Any

async def fetch_stock_data(ticker: str, days: int = 730) -> Dict[str, Any]:
    """
    Stub function to fetch historical adjusted close prices.
    Returns placeholder metadata and price series.
    """
    return {
        "ticker": ticker,
        "days": days,
        "data_points": 500,
        "source": "Yahoo Finance (Adjusted Close)"
    }
