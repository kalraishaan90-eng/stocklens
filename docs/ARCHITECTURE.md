# StockLens — System Architecture & Data Pipeline

```
+-----------------------------------------------------------------------------------+
|                                 USER BROWSER                                      |
|                                                                                   |
|  [Search / Presets]   [Rebased Overlay Chart]   [Side-by-Side Monthly 3M-MA Chart]|
|  [H2H Verdict Banner] [Growth/Risk Matrix]      [Why Did Price Move (Cited News)] |
|                               [Download PDF Report]                               |
+-----------------------------------------+-----------------------------------------+
                                          | JSON over HTTP
                                          v
+-----------------------------------------------------------------------------------+
|                            FASTAPI BACKEND (Python 3.12)                          |
|                                                                                   |
|  1. /api/analyze                                                                  |
|     +---> TickerResolver                                                          |
|     |     - Curated Indian Alias Dictionary (0ms instant resolution)              |
|     |     - Yahoo Finance Autocomplete API (dynamic fallback)                     |
|     |                                                                             |
|     +---> StockDataService                                                        |
|     |     - Dynamic 730-day window (today - 730 days)                             |
|     |     - Adjusted Close enforcement                                            |
|     |     - Timeout & Exponential Backoff Retry                                   |
|     |     - SQLite Persistent Cache Layer (TTL = 3600s)                           |
|     |                                                                             |
|     +---> Analytics Engine                                                        |
|     |     - Monthly Resampling (calendar month-end Adj Close)                     |
|     |     - 3-Month Moving Average (rolling 3 periods)                            |
|     |     - CAGR, Annualized Volatility, Sharpe Ratio, Max Drawdown               |
|     |     - 100-Indexed Rebased Overlay & Pearson Correlation                     |
|     |                                                                             |
|     +---> AnomalyDetector & NewsAttribution                                       |
|     |     - >3.2% single-day volatility trigger & volume surges                   |
|     |     - Google News RSS & Yahoo Finance contemporaneous queries               |
|     |     - Hard Rule 1 Zero-Hallucination verification                           |
|     |                                                                             |
|     +---> Gemini AI & Deterministic Rule-Based Analyzer                           |
|     |     - Google Gemini 1.5 Flash (when GEMINI_API_KEY configured)              |
|     |     - Deterministic Financial Rule-Based Synthesis (graceful fallback)      |
|     |                                                                             |
|     +---> Recommendation & Head-to-Head Arbiter                                   |
|           - 4-pillar quantitative scoring model (0-100)                           |
|           - Objective BUY / HOLD / AVOID stance & winner verdict                  |
+-----------------------------------------------------------------------------------+
```

## Resilience & Fail-Safe Architecture
1. **Network Interruptions**: The backend incorporates exponential backoff retries. If the live Yahoo Finance endpoint is unavailable or rate-limited, the system automatically falls back to curated offline datasets or cached responses.
2. **Offline Demo Mode**: Dedicated offline toggle allows presentation booths with zero Wi-Fi to run full dynamic analytics over authentic baseline series.
3. **AI Graceful Degradation**: If the Gemini API key is missing or encounters a timeout, the deterministic rule-based intelligence engine automatically activates, ensuring the application never stalls.
