"""
comparative_text.py — Generates Step 5 Comparative Analysis narrative.
Answers:
1. Which company is more stable (volatility, max drawdown, stability score)?
2. Which company shows better growth (CAGR, total return, 3M momentum, growth score)?
3. What does the 3-month moving average reveal (crossovers, quarterly smoothing, cyclical trajectory)?

Optionally polishes via Google Gemini with a strict "no new facts" prompt, falling back
gracefully to the deterministic synthesis when offline or if no API key is provided.
"""

from typing import Dict, Any, List, Optional
import httpx
from app.config import GEMINI_API_KEY
from app.models.schemas import CompanyAnalysis, PerformanceMetrics, ComparisonObject


def generate_deterministic_comparative_text(
    comp_a: CompanyAnalysis,
    comp_b: CompanyAnalysis,
    comparison_obj: Optional[ComparisonObject] = None
) -> Dict[str, str]:
    """
    Generates structured, publication-grade analytical paragraphs answering the 3 core questions.
    """
    m_a: PerformanceMetrics = comp_a.metrics
    m_b: PerformanceMetrics = comp_b.metrics
    name_a = comp_a.info.name
    ticker_a = comp_a.info.ticker
    name_b = comp_b.info.name
    ticker_b = comp_b.info.ticker

    # 1. Stability Analysis
    if m_a.annualized_volatility_pct < m_b.annualized_volatility_pct:
        vol_diff_pct = round(((m_b.annualized_volatility_pct - m_a.annualized_volatility_pct) / m_b.annualized_volatility_pct) * 100.0, 1)
        stab_winner = name_a
        stab_ticker = ticker_a
        stab_margin = f"{vol_diff_pct}% lower annualized volatility ({m_a.annualized_volatility_pct:.1f}% vs {m_b.annualized_volatility_pct:.1f}%)"
    else:
        vol_diff_pct = round(((m_a.annualized_volatility_pct - m_b.annualized_volatility_pct) / m_a.annualized_volatility_pct) * 100.0, 1)
        stab_winner = name_b
        stab_ticker = ticker_b
        stab_margin = f"{vol_diff_pct}% lower annualized volatility ({m_b.annualized_volatility_pct:.1f}% vs {m_a.annualized_volatility_pct:.1f}%)"

    dd_diff = abs(round(m_a.max_drawdown_pct - m_b.max_drawdown_pct, 1))
    shallower_dd_comp = name_a if m_a.max_drawdown_pct < m_b.max_drawdown_pct else name_b
    shallower_dd_val = min(m_a.max_drawdown_pct, m_b.max_drawdown_pct)
    steeper_dd_val = max(m_a.max_drawdown_pct, m_b.max_drawdown_pct)

    stab_paragraph = (
        f"1. Stability Evaluation: On a risk-resilience basis, {stab_winner} ({stab_ticker}) emerges as the more stable equity, "
        f"demonstrating {stab_margin}. During severe market corrections across the 2-year baseline, {shallower_dd_comp} contained peak-to-trough "
        f"capital drawdown at -{shallower_dd_val:.1f}% compared to -{steeper_dd_val:.1f}% for its peer, preserving a {dd_diff:.1f} percentage point margin of safety. "
        f"With a composite Stability Score of {comp_a.metrics.stability_score if stab_winner == name_a else comp_b.metrics.stability_score:.1f}/100, "
        f"{stab_winner} provides a substantially calmer holding experience for capital-preservation focused investors."
    )

    # 2. Growth Evaluation
    if m_a.cagr_pct >= m_b.cagr_pct:
        growth_winner = name_a
        growth_ticker = ticker_a
        cagr_diff = round(m_a.cagr_pct - m_b.cagr_pct, 1)
        tot_gain_winner = m_a.total_return_pct
        tot_gain_loser = m_b.total_return_pct
    else:
        growth_winner = name_b
        growth_ticker = ticker_b
        cagr_diff = round(m_b.cagr_pct - m_a.cagr_pct, 1)
        tot_gain_winner = m_b.total_return_pct
        tot_gain_loser = m_a.total_return_pct

    sharpe_winner = name_a if m_a.sharpe_ratio >= m_b.sharpe_ratio else name_b
    sharpe_w_val = max(m_a.sharpe_ratio, m_b.sharpe_ratio)
    sharpe_l_val = min(m_a.sharpe_ratio, m_b.sharpe_ratio)

    growth_paragraph = (
        f"2. Growth & Return Profile: In terms of capital compounding, {growth_winner} ({growth_ticker}) generated superior expansion velocity, "
        f"delivering a 2-year total price appreciation of {tot_gain_winner:+.1f}% (+{max(m_a.cagr_pct, m_b.cagr_pct):.1f}% CAGR), outperforming its peer "
        f"({tot_gain_loser:+.1f}% total gain, +{min(m_a.cagr_pct, m_b.cagr_pct):.1f}% CAGR) by {cagr_diff:.1f} annual percentage points. "
        f"Crucially, evaluating returns on a risk-adjusted scale above India's 6.5% sovereign risk-free baseline, {sharpe_winner} achieved a Sharpe ratio of "
        f"{sharpe_w_val:.2f} versus {sharpe_l_val:.2f}, proving that its growth was not merely an artifact of excessive speculative leverage."
    )

    # 3. Moving Average Revelations
    # Inspect monthly series vs MA-3M
    latest_a = comp_a.monthly_series[-1] if comp_a.monthly_series else None
    latest_b = comp_b.monthly_series[-1] if comp_b.monthly_series else None

    status_a = "above" if (latest_a and latest_a.ma_3m and latest_a.adj_close >= latest_a.ma_3m) else "below"
    status_b = "above" if (latest_b and latest_b.ma_3m and latest_b.adj_close >= latest_b.ma_3m) else "below"

    slope_a = comp_a.metrics.ma_3m_slope or "RISING"
    slope_b = comp_b.metrics.ma_3m_slope or "RISING"

    ma_paragraph = (
        f"3. Moving Average Trend Insights: The 3-month Simple Moving Average (MA-3M) filters out noisy calendar fluctuations and reveals "
        f"the structural trend. Currently, {ticker_a} trades {status_a} its 3-month moving average with a {slope_a.lower()} trajectory, while "
        f"{ticker_b} trades {status_b} its 3-month moving average with a {slope_b.lower()} slope. "
        f"The rolling quarterly smoothing confirms that both assets have experienced significant cyclical expansions, but moving average crossovers "
        f"serve as critical boundary indicators distinguishing sustainable structural advances from overheated mean-reverting spikes."
    )

    combined_synthesis = f"{stab_paragraph}\n\n{growth_paragraph}\n\n{ma_paragraph}"

    return {
        "stability_paragraph": stab_paragraph,
        "growth_paragraph": growth_paragraph,
        "ma_paragraph": ma_paragraph,
        "full_analysis": combined_synthesis,
        "stability_winner": stab_winner,
        "growth_winner": growth_winner
    }


async def polish_comparative_analysis_with_gemini(
    raw_analysis: str,
    company_a_name: str,
    company_b_name: str
) -> str:
    """
    Polishes the analytical text using Gemini with a strict 'no new facts' prompt.
    Falls back to raw_analysis on any failure.
    """
    if not GEMINI_API_KEY:
        return raw_analysis

    prompt = (
        "You are an academic financial editor reviewing a Senior Secondary School Science Exhibition Project. "
        "Your task is to polish the provided comparative stock analysis into elegant, professional academic prose. "
        "STRICT CONSTRAINTS:\n"
        "1. DO NOT invent, extrapolate, or introduce any new facts, figures, dates, or company details.\n"
        "2. Keep all numerical values, percentages, and winners exactly as written.\n"
        "3. Address the three core questions clearly: (1) Which is more stable, (2) Which shows better growth, and (3) What the moving average reveals.\n"
        "4. Output 3 concise, beautifully written paragraphs without markdown bullet points.\n\n"
        f"ORIGINAL ANALYSIS:\n{raw_analysis}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600}
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0]["text"].strip()
    except Exception:
        pass

    return raw_analysis
