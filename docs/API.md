# StockLens — Shared API Contract Specification

This document defines the formal shared HTTP API contract between the **StockLens Frontend (Vite + React + TS)** and the **FastAPI Backend**.

---

## Base URL

- Local Development Backend: `http://localhost:8000` (or `http://127.0.0.1:8000`)
- Frontend Dev Server: `http://localhost:5173`

---

## 1. System Health Check

### Endpoint
`GET /api/health`

### Description
Validates backend availability, active version, Gemini AI availability, and offline demo status.

### Response
- **Status Code:** `200 OK`
- **Content-Type:** `application/json`

```json
{
  "status": "healthy",
  "timestamp": "2026-10-03T01:25:00.000000+00:00",
  "version": "1.0.0",
  "service": "StockLens API",
  "gemini_enabled": false,
  "offline_demo_enabled": true
}
```

---

## 2. Dual Equity Analysis Engine

### Endpoint
`POST /api/analyze`

### Description
Main analytical orchestrator endpoint. Accepts two company queries or tickers, resolves company identities to validated exchange symbols, aggregates monthly adjusted close price series, computes 3-month rolling moving averages, computes performance & risk metrics (CAGR, Annualized Volatility, Max Drawdown, Sharpe ratio), calculates head-to-head comparison and scoring, attributes detected price anomalies with verified contemporaneous news, and attaches project metadata.

### Request Body (`application/json`)
```json
{
  "company1": "HAL",
  "company2": "Mazagon Dock",
  "use_offline_demo": false
}
```

#### Request Schema
| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `company1` | `string` | Yes | First company name, common alias, or ticker symbol | `"HAL"` |
| `company2` | `string` | Yes | Second company name, common alias, or ticker symbol | `"Mazagon Dock"` |
| `use_offline_demo` | `boolean` | No | Flag to force local verified offline dataset (useful for exhibition booths with no Wi-Fi) | `false` |

---

### Response Body (`application/json`)
- **Status Code:** `200 OK`

```json
{
  "resolved_tickers": {
    "company1": {
      "query": "HAL",
      "ticker": "HAL.NS",
      "name": "Hindustan Aeronautics Limited",
      "exchange": "NSE",
      "currency": "INR"
    },
    "company2": {
      "query": "Mazagon Dock",
      "ticker": "MAZDOCK.NS",
      "name": "Mazagon Dock Shipbuilders Limited",
      "exchange": "NSE",
      "currency": "INR"
    }
  },
  "monthly_table": [
    {
      "date": "2024-01-31",
      "month_label": "Jan 2024",
      "company1_adj_close": 2980.50,
      "company2_adj_close": 2150.00
    },
    {
      "date": "2024-02-29",
      "month_label": "Feb 2024",
      "company1_adj_close": 3040.20,
      "company2_adj_close": 2280.40
    },
    {
      "date": "2024-03-31",
      "month_label": "Mar 2024",
      "company1_adj_close": 3130.00,
      "company2_adj_close": 2202.10
    }
  ],
  "moving_averages": [
    {
      "date": "2024-01-31",
      "month_label": "Jan 2024",
      "company1_ma_3m": null,
      "company2_ma_3m": null
    },
    {
      "date": "2024-02-29",
      "month_label": "Feb 2024",
      "company1_ma_3m": null,
      "company2_ma_3m": null
    },
    {
      "date": "2024-03-31",
      "month_label": "Mar 2024",
      "company1_ma_3m": 3050.23,
      "company2_ma_3m": 2210.83
    }
  ],
  "metrics": {
    "company1": {
      "ticker": "HAL.NS",
      "name": "Hindustan Aeronautics Limited",
      "current_price": 4450.00,
      "cagr_pct": 52.40,
      "annualized_volatility_pct": 28.60,
      "max_drawdown_pct": 14.20,
      "sharpe_ratio": 1.62,
      "high_52w": 5675.00,
      "low_52w": 2890.00,
      "total_return_pct": 128.50,
      "positive_days_pct": 54.80
    },
    "company2": {
      "ticker": "MAZDOCK.NS",
      "name": "Mazagon Dock Shipbuilders Limited",
      "current_price": 4120.00,
      "cagr_pct": 74.20,
      "annualized_volatility_pct": 36.10,
      "max_drawdown_pct": 19.80,
      "sharpe_ratio": 1.88,
      "high_52w": 5860.00,
      "low_52w": 1920.00,
      "total_return_pct": 182.30,
      "positive_days_pct": 53.20
    }
  },
  "comparison": {
    "winner_ticker": "MAZDOCK.NS",
    "winner_name": "Mazagon Dock Shipbuilders Limited",
    "margin": "Slight Edge",
    "score_diff": 4.50,
    "correlation_2y": 0.78,
    "verdict_text": "Mazagon Dock demonstrates superior momentum and higher risk-adjusted return (Sharpe 1.88 vs 1.62) over the 2-year analysis window, despite higher annualized volatility.",
    "rebased_overlay": [
      {
        "date": "2024-01-31",
        "company1_rebased": 100.0,
        "company2_rebased": 100.0
      },
      {
        "date": "2024-03-31",
        "company1_rebased": 105.0,
        "company2_rebased": 102.4
      }
    ]
  },
  "recommendations": {
    "company1": {
      "action": "BUY",
      "score": 82.5,
      "risk_level": "Moderate",
      "key_drivers": [
        "Predictable multi-year order book visibility",
        "Lower peak-to-trough drawdown (14.2%)",
        "Stable operating margins across cycles"
      ],
      "summary": "HAL demonstrates stable compounding with resilient defense order visibility and lower downside volatility."
    },
    "company2": {
      "action": "BUY",
      "score": 87.0,
      "risk_level": "High",
      "key_drivers": [
        "Exceptional 2-year CAGR (74.2%)",
        "Superior risk-adjusted return (Sharpe 1.88)",
        "Expanding submarine and warship export pipeline"
      ],
      "summary": "Mazagon Dock shows exceptional momentum and higher capital appreciation potential, suited for growth-oriented profiles."
    }
  },
  "anomalies": [
    {
      "company_key": "company1",
      "ticker": "HAL.NS",
      "company_name": "Hindustan Aeronautics Limited",
      "date": "2024-06-04",
      "change_pct": -8.50,
      "direction": "drop",
      "headline": "Public sector and capital goods equities witness sharp profit-booking",
      "source": "The Economic Times",
      "url": "https://economictimes.indiatimes.com",
      "explanation": "Broad-based market correction across PSU counters coinciding with general election tally announcements.",
      "confidence": "High"
    },
    {
      "company_key": "company2",
      "ticker": "MAZDOCK.NS",
      "company_name": "Mazagon Dock Shipbuilders Limited",
      "date": "2024-07-10",
      "change_pct": 9.20,
      "direction": "jump",
      "headline": "Naval defense procurement boost spurs major shipyard order inflows",
      "source": "Reuters",
      "url": "https://reuters.com",
      "explanation": "Official notification of expanded defense allocation and multi-year vessel overhaul contracts.",
      "confidence": "High"
    }
  ],
  "metadata": {
    "data_source": "Yahoo Finance (Adjusted Close)",
    "fetched_at": "2026-10-03T01:25:00.000000+00:00",
    "is_offline_demo": false,
    "disclaimer": "Educational project. Not financial advice. Historical performance does not guarantee future results.",
    "causation_warning": "Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news."
  }
}
```

---

## 3. Symbol Resolver

### Endpoint
`GET /api/resolve?q={query}`

### Description
Resolves a free-text company name (e.g. `HAL`, `hindustan aeronautics`, `Bajaj Finserv`, `HDFC Bank`) to a Yahoo Finance ticker. Prefers NSE (`.NS`), then BSE (`.BO`). Uses a built-in alias map with rapidfuzz fuzzy matching for typos, falling back to Yahoo Finance search. Returns the top match plus up to 3 alternatives so the UI can ask the user to confirm when the query is ambiguous (`is_ambiguous: true`).

### Query Parameters
| Name | Type | Required | Description |
|---|---|---|---|
| `q` | string | Yes | Free-text company name or ticker symbol |

### Response Body (`application/json`)
```json
{
  "query": "HAL",
  "match": {
    "ticker": "HAL.NS",
    "name": "Hindustan Aeronautics Limited",
    "exchange": "NSE",
    "sector": "Industrials",
    "is_ambiguous": false,
    "restructuring_note": null,
    "confidence_score": 100.0
  },
  "alternatives": [
    { "ticker": "HAL.BO", "name": "Hindustan Aeronautics Limited", "exchange": "BSE", "sector": "Industrials", "is_ambiguous": false, "restructuring_note": null, "confidence_score": 90.0 }
  ],
  "is_ambiguous": false,
  "restructuring_note": null
}
```

Notes:
- Restructured companies (e.g. Tata Motors demerger → `TMPV.NS` / `TMCV.NS`, Siemens Energy split) carry `restructuring_note` and `is_ambiguous: true`.

---

## 4. Price Fetcher

### Endpoint
`GET /api/prices/{ticker}?days=730&force_live=false`

### Description
Fetches daily OHLCV for the last `days` days (default 730) via yfinance with `auto_adjust=True` (adjusted closes), plus the NIFTY 50 benchmark (`^NSEI`) and the mapped sector index when available. Data is cleaned (NaN rows dropped, forward-fill bounded to 3 trading days, gap detection, timezone-naive sorted `DatetimeIndex`) and returned with a data-quality report and null-safe company fundamentals. Responses are disk-cached with a 6-hour TTL; when the live fetch fails, stale cache is served with `stale_data: true`.

### Query Parameters
| Name | Type | Default | Description |
|---|---|---|---|
| `days` | int | 730 | Lookback window in calendar days (30–730) |
| `force_live` | bool | false | Bypass the fresh disk cache and force a live fetch |

### Response Body (`application/json`)
```json
{
  "ticker": "RELIANCE.NS",
  "company_info": {
    "name": "Reliance Industries Limited",
    "sector": "Energy",
    "industry": "Oil & Gas Refining & Marketing",
    "exchange": "NSE",
    "market_cap": 15801867304960.0,
    "fifty_two_week_high": 1611.8,
    "fifty_two_week_low": 1160.8,
    "pe_ratio": 21.14,
    "dividend_yield": 0.51,
    "beta": 0.15
  },
  "data_quality": { "rows": 500, "first_date": "2024-10-02", "last_date": "2026-09-30", "missing_days": 21, "has_gaps": false, "gaps": [], "is_restructured_or_short": false },
  "stale_data": false,
  "cached": false,
  "warning": null,
  "restructuring_note": null,
  "prices": [ { "date": "2026-09-30", "open": 1180.1, "high": 1183.9, "low": 1160.8, "close": 1167.7, "volume": 16771221 } ],
  "benchmark": { "ticker": "^NSEI", "records": ["..."] },
  "sector_index": null
}
```

Notes:
- `warning` surfaces startup verification results (short/restructured ticker history) so the UI can display a note.
- `sector_index` may be `null` when the mapped sector index is unavailable or its history is truncated upstream; `benchmark` remains populated.

---

## 5. Global Error Responses

All API errors return consistent JSON structures:

### Client / Not Found / Bad Request Error (`4xx`)
```json
{
  "error": true,
  "status_code": 400,
  "message": "Failed to resolve company name: 'INVALID_STOCK_NAME'",
  "timestamp": "2026-10-03T01:25:00.000000+00:00"
}
```

### Validation Error (`422 Unprocessable Entity`)
```json
{
  "error": true,
  "status_code": 422,
  "message": "Validation Error: Invalid request payload",
  "details": [
    {
      "loc": ["body", "company1"],
      "msg": "Field required",
      "type": "missing"
    }
  ],
  "timestamp": "2026-10-03T01:25:00.000000+00:00"
}
```

### Internal Server Error (`500`)
```json
{
  "error": true,
  "status_code": 500,
  "message": "An internal server error occurred.",
  "detail": "Underlying connection timeout while contacting quote provider.",
  "timestamp": "2026-10-03T01:25:00.000000+00:00"
}
```
