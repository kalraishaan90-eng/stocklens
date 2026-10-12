# StockLens: three-minute exhibition demo

## 30-second elevator pitch

“StockLens is a classroom project that compares two companies using about two years of adjusted share prices. It calculates returns, risk measures, and a three-month moving average, then flags unusual price moves and shows nearby news as context. A transparent scoring rule summarizes the signals as Buy, Hold, or Avoid, but it cannot prove why a price moved or predict what happens next. We built it to make the steps and limitations visible, and it includes clearly labelled offline snapshots so the demonstration still works when the venue network does not.”

## Three-minute spoken walkthrough

Use **HAL vs Mazagon Dock** (`HAL` and `Mazagon Dock`), the first curated pair. The Home page can load its bundled demo snapshot even if the API is unavailable. Start with the offline badge visible if demo mode is on; never describe captured data as live.

| Time | Exact clicks and what to point at | What to say |
|---|---|---|
| 0:00–0:25 | On Home, click the first company field and type `HAL`; click the second and type `Mazagon Dock`; click **Analyse**. If the page is preloaded, click **Home** in the top navigation, then follow those steps. | “I chose two Indian aerospace and shipbuilding companies. StockLens resolves the company names to exchange tickers, then compares their available adjusted-price history. The offline badge tells us when this is a captured snapshot.” |
| 0:25–0:55 | At the top of the analysis, point to the company names, date range, and headline metric cards. | “These values summarize the selected historical window. Return and CAGR describe past performance; volatility and drawdown describe different aspects of past price movement. They are not forecasts.” |
| 0:55–1:25 | Scroll to **Price History**. Point to both series and the moving-average line/legend; hover a month-end point if a pointer is available. | “The chart shows adjusted prices over time. The three-month moving average is the mean of the latest three month-end closes, so it smooths some short-term movement. A smoother line can lag a sudden change.” |
| 1:25–1:55 | Scroll to **Anomalies** or **Notable price movements**. Point to one dated event, its explanation, and any linked source. | “This event crossed our statistical screen. The explanation and source can suggest context around that date, but timing alone cannot prove the headline caused the price move. If no reliable article was found, StockLens says so rather than inventing one.” |
| 1:55–2:25 | Scroll to **Recommendation** / verdict. Point to Buy/Hold/Avoid and the signal breakdown/limitations. | “This label combines six weighted historical signals using fixed rules. It is a compact summary of those rules, not a personalized investment recommendation. Company accounts, future events, liquidity, and your circumstances are outside this score.” |
| 2:25–2:45 | Click **How it works** (or its footer/help control). Let the five steps animate; point to Pick → Fetch → Calculate → Detect → Decide. | “The pipeline is explicit: choose companies, fetch adjusted prices, calculate metrics, detect unusual moves, and summarize the evidence. The visitor can see the sequence rather than treating the result as a black box.” |
| 2:45–3:00 | Close the drawer. Press **P** to start presenter mode, then press **Esc** to exit; or click a judge question and show its highlighted section. | “Presenter mode advances through the six analysis sections and pauses when someone interacts. The judge shortcuts take us directly to relevant evidence. Questions are welcome.” |

## If something fails

- **Live API/network fails:** keep the pair as HAL vs Mazagon Dock and use its bundled snapshot. Point to the badge **“Offline demo data, captured on [date]”** and say: “The venue connection failed, so this is the saved analysis captured on the date shown. It is not live.”
- **A custom pair fails:** return to Home and use the curated HAL/Mazagon Dock pair. Offline snapshots only cover the nine project pairs.
- **Snapshot asset does not load:** use the two screenshots in the README and narrate the calculations; if the live demo is essential, switch to the prepared backup video. Do not claim an unavailable result was generated live.
- **Chart or animation is slow:** wait briefly, then scroll to the relevant heading or use a judge-question shortcut. The table and text summaries remain the fallback explanation.
- **Presenter mode behaves unexpectedly:** press **Esc**. Continue with manual scrolling; pressing any key, clicking, or touching pauses auto-advance.
- **Browser exits full screen:** press **F11** on Windows/Linux or use the browser’s View → Enter Full Screen command. Use the exhibition checklist before restarting.

## Preparation

Run `python scripts/preflight.py`; optionally run `python scripts/warm_cache.py` for live mode. Keep demo mode available, set browser zoom for the display, and have the backup recording ready. See [Exhibition checklist](EXHIBITION_CHECKLIST.md).
