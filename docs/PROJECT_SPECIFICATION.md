# StockLens — Project Specification & Methodology

## 1. Executive Summary
**StockLens** is an exhibition-grade educational web platform designed for senior secondary school science and technology exhibitions. The platform performs real-time comparative financial time-series analysis between two publicly traded equities (with deep optimization for Indian National Stock Exchange `NSE` stocks, alongside international markets).

The platform eliminates subjective biases by combining:
1. **Dynamic Time-Series Analytics**: A strict, non-hardcoded 730-day temporal baseline ($T_{\text{today}} - 730 \text{ days}$).
2. **Corporate Action Adjustment**: Utilizing exclusively **Adjusted Close** data to neutralize distortion from splits, bonus issues, dividends, and demergers.
3. **Trend Smoothing**: Monthly aggregation and rolling 3-Month Moving Average (MA) modeling.
4. **Multi-Pillar Scoring**: Quantitative rating matrix balancing CAGR, annualized volatility, max drawdown, and Sharpe ratio.
5. **Verified Anomaly Attribution**: Correlating statistical price spikes with authentic contemporaneous news headlines without generative hallucination.

---

## 2. Mathematical Formulations & Metrics

### 2.1 Compound Annual Growth Rate (CAGR)
$$\text{CAGR} = \left(\frac{P_{\text{end}}}{P_{\text{start}}}\right)^{\frac{365.25}{\Delta \text{days}}} - 1$$
Where:
- $P_{\text{start}}$ = First trading day adjusted close in the 730-day window.
- $P_{\text{end}}$ = Latest trading day adjusted close.
- $\Delta \text{days}$ = Total elapsed calendar days.

### 2.2 Annualized Volatility ($\sigma_{\text{ann}}$)
Daily percentage returns are computed as:
$$R_t = \frac{P_t - P_{t-1}}{P_{t-1}}$$
Annualized volatility assumes 252 active trading sessions per calendar year:
$$\sigma_{\text{ann}} = \text{StdDev}(R) \times \sqrt{252}$$

### 2.3 Maximum Drawdown (MDD)
Measures the steepest peak-to-trough capital decline:
$$\text{Drawdown}_t = \frac{P_t - \max_{0 \le \tau \le t}(P_\tau)}{\max_{0 \le \tau \le t}(P_\tau)}$$
$$\text{MDD} = |\min(\text{Drawdown})|$$

### 2.4 Sharpe Ratio
Evaluates return generated per unit of risk against the risk-free rate ($R_f = 6.5\%$ for Indian Sovereign Debt):
$$\text{Sharpe} = \frac{\text{CAGR} - R_f}{\sigma_{\text{ann}}}$$

### 2.5 3-Month Moving Average (MA-3M)
Monthly closing prices are established by taking the final trading session of each calendar month. The 3-month moving average is computed as:
$$\text{MA-3M}_m = \frac{P_m + P_{m-1} + P_{m-2}}{3} \quad (\text{for } m \ge 3)$$

---

## 3. Strict Compliance & Scientific Principles

### 3.1 Hard Rule 1: No Fabrication of News or Reasons
Explanations for price jumps and drops must cite actual indexed headlines and media publications (e.g. Google News RSS, Yahoo Finance). If no verified contemporaneous article is found within the event window, the platform explicitly outputs:
> *"No clear public reason found in indexed news feeds. Trading data indicates broader liquidity, index rebalancing, or systematic sector-wide sentiment shifts."*

### 3.2 Hard Rule 2: Causation Disclaimer
All market movement discussions feature the clear declaration:
> *"Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news."*

### 3.3 Hard Rule 3: Educational Disclaimer
All screens and exported reports carry the mandatory disclaimer:
> *"Educational project. Not financial advice. Historical performance does not guarantee future results."*

### 3.4 Hard Rule 4: Adjusted Close
Raw close prices are susceptible to severe discontinuities caused by stock splits (e.g., a 2:1 split appears as a 50% crash on raw charts). StockLens exclusively feeds adjusted close prices through its calculation pipeline.
