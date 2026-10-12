# Judge Q&A

1. **How do you decide Buy or Hold?**  Six historical signals—trend, momentum, risk, return quality, distance from the 52-week range, and a valuation proxy—are combined with configured weights. Thresholds map the score to Buy, Hold, or Avoid. It is a rule-based educational summary, not personal advice.

2. **How do you know why the price moved?**  We do not know causation from price data. We flag an unusual move and show date-nearby news as possible context with links. The headline may be unrelated or incomplete.

3. **Can the analysis be wrong?**  Yes. Providers can have missing, revised, or delayed prices; news matching and anomaly thresholds can mislead; and our calculations and rules have limits. Verify important values independently.

4. **What is a moving average, and why three months?**  It is the average of the latest three month-end adjusted closes. Three months is the project's chosen short smoothing window: easy to explain, while still responsive. It is not a universal investing standard and it lags sudden changes.

5. **What are the main limitations?**  The model uses a short historical window and a small set of price-based signals. It does not model financial statements, governance, liquidity in depth, taxes, fees, investor goals, or future events. Offline snapshots are fixed at their capture date.

6. **What is the difference between volatility and risk?**  Volatility measures how widely returns varied. Risk is broader and includes permanent loss, liquidity, concentration, business, provider, and model risks that this one number cannot capture.

7. **How is StockLens different from Google Finance?**  Google Finance is a general market information product. StockLens is a small educational comparison workflow that exposes its moving-average calculation, anomaly context, scoring signals, and offline-demo provenance. It is not a replacement for a market data or research service.

8. **What did you build, and what comes from libraries?**  We built the comparison workflow, analysis orchestration, scoring and anomaly rules, snapshot fallback, exhibition modes, and report assembly. Libraries provide the web framework, data manipulation, charts, UI components, and file formats; Yahoo Finance, news publishers, and optional Gemini provide external data/services.

9. **What would you add next?**  Add tests against independently calculated reference cases, richer financial-statement data with provenance, and a shared rate limiter for multi-worker deployments. We would also improve accessibility and validate the scoring with domain experts before changing its use.

10. **Where does the price data come from?**  Historical adjusted closes are fetched through yfinance from Yahoo Finance. The provider can change or restrict data, so results include dates and are not guaranteed exchange-grade data.

11. **Why use adjusted closes?**  Adjusted closes account for corporate actions such as splits and dividends as represented by the provider, making long-window price comparisons more meaningful. They remain provider-calculated values.

12. **What period does the analysis cover?**  The live flow requests up to 730 calendar days of history. Actual observations can cover less if the ticker is new, data is unavailable, or the provider returns gaps. The snapshot shows the period captured.

13. **What is beta?**  Beta estimates how the stock's daily returns moved with a selected benchmark over their overlapping history: covariance divided by benchmark return variance. It is historical, window-dependent, and not a complete measure of risk.

14. **What does correlation tell you?**  It measures the direction and strength of linear co-movement over overlapping observations, from -1 to +1. It does not show that one company caused the other's movement or that the relationship will persist.

15. **What does the Sharpe-style value mean?**  It compares annualized CAGR above a configured risk-free rate with annualized volatility. This app uses annual metrics for a simplified ratio, not the canonical daily excess-return Sharpe calculation, so treat it as an approximate comparison aid.

16. **How is annualized volatility calculated?**  We take the sample standard deviation of daily percentage returns and multiply by the square root of 252 trading days. The annualization assumes a conventional trading-year scale and summarizes the selected past window.

17. **How fresh is the displayed information?**  Live analyses may use fresh or stale caches, and provider data is not guaranteed real time. Demo snapshots are fixed and explicitly labelled with their capture date. Check that label and the displayed date range.

18. **What happens when internet or the API is unavailable?**  For the nine curated pairs, the app can load prebuilt analyses from the frontend bundle and marks them as offline demo data with a capture date. Arbitrary pairs need a working backend/data source.

19. **Why might an anomaly have no article or explanation?**  A news source may not publish a relevant item, feeds can be unavailable, and the evidence may not support a confident explanation. We show the gap instead of fabricating a cause.

20. **Does a high volatility score mean a company is unsafe?**  No. It means the observed returns varied more over the measured period. A stable price can still carry business or liquidity risk, and a volatile company may have other strengths. No single score defines safety.
