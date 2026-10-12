import os
import json
import re
import asyncio
from typing import Dict, Any, List, Optional
import httpx
from app.config import GEMINI_API_KEY
from app.services.cache import get_cached, set_cached

SYSTEM_PROMPT = (
    "Explain in 2-3 simple sentences for a school audience why the stock likely moved. "
    "Use ONLY the supplied headlines and data. Do not invent any fact, figure, or reason. "
    "Every number you state must appear verbatim in the supplied facts payload. "
    "Only mention a corporate event (earnings, results, dividend, split, order, rating change) "
    "if a supplied headline or corporate event mentions it. "
    "Only name news sources that appear in the supplied headlines. "
    "If the headlines do not explain the move, say so. Mention if the move was market-wide or sector-wide."
)

# Stems for corporate-action claims the model may only make when a supplied
# headline or corporate event actually mentions them.
_CORPORATE_ACTION_STEMS = (
    "earnings", "quarterly result", "quarterly report", "q1", "q2", "q3", "q4",
    "dividend", "bonus", "stock split", "buyback", "buy-back", "rights issue",
    "merger", "amalgamation", "acquisition", "takeover",
    "order win", "won the order", "contract win", "big order", "bagged",
    "price target", "upgrade", "downgrade", "outlook", "guidance",
    "credit rating", "stake sale", "open offer", "delisting", "fpo", "ipo",
)

_NEWS_SOURCES_ALLOWED = {
    "nse market trading data", "market trading data", "trading data",
    "exchange corporate filings", "exchange filings", "corporate filings",
    "financial press", "indexed news archives", "indexed news feeds",
}


def _pct_claims(text: str) -> List[float]:
    """Extracts numeric percentage claims (e.g. '5.2%', '-12.75%') from text."""
    return [float(m) for m in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", text)]


def _allowed_pct_values(facts_payload: Dict[str, Any]) -> List[float]:
    """Percentage figures that are present in the supplied facts payload."""
    allowed = []
    for key in ("price_change_pct", "stock_return_pct", "nifty_50_return_pct",
                "sector_return_pct", "residual_move_pct", "gap_at_open_pct"):
        val = facts_payload.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            allowed.append(float(val))
    return allowed

def compute_confidence(
    classification: str,
    has_news: bool,
    vol_multiplier: float,
    has_corporate_events: bool = False
) -> str:
    """
    Confidence logic (Requirement 6):
    - High = company-specific + matching news + volume spike (>= 1.5x)
    - Medium = partial evidence (market/sector move with news, or news without volume spike, or corporate event)
    - Low = no matching news and no corporate event
    """
    if not has_news and not has_corporate_events:
        return "Low"
    
    if classification == "Company-specific move" and has_news and (vol_multiplier >= 1.5):
        return "High"
    
    return "Medium"

def generate_rule_based_fallback(
    company_name: str,
    ticker: str,
    event_date: str,
    change_pct: float,
    direction: str,
    vol_multiplier: float,
    gap_pct: float,
    market_context: Dict[str, Any],
    headlines: List[Dict[str, Any]],
    corporate_events: List[str]
) -> Dict[str, Any]:
    """
    Builds a templated explanation from classification, volume spike, corporate events,
    and top headlines, clearly labelled 'Auto-generated without AI'.
    """
    classification = market_context.get("classification", "Company-specific move")
    nifty_ret = market_context.get("nifty_return_pct", 0.0)
    sector_ret = market_context.get("sector_return_pct")
    sector_name = market_context.get("sector_name", "Sector Index")

    has_news = len(headlines) > 0
    top_headline = headlines[0] if has_news else None

    likely_reasons: List[str] = []
    sources_used: List[str] = ["NSE Market Trading Data"]

    # Corporate events (earnings releases, dividends, filings, etc.)
    if corporate_events:
        for ce in corporate_events[:2]:
            likely_reasons.append(f"Corporate event: {ce}")
        sources_used.append("Exchange Corporate Filings")

    # Volume context
    vol_desc = f"Heavy trading volume ({vol_multiplier:.1f}x 20-day average)" if vol_multiplier >= 1.5 else f"Standard volume ({vol_multiplier:.1f}x 20-day average)"
    likely_reasons.append(vol_desc)

    # Classification details
    if classification == "Market-wide move":
        likely_reasons.append(f"Market-wide move: NIFTY 50 moved {nifty_ret:+.2f}% on the same date")
        if top_headline:
            sources_used.append(top_headline.get("source", "Financial Press"))
            summary = (
                f"[Auto-generated without AI] {company_name} experienced a {direction} of {change_pct:+.1f}% "
                f"largely driven by a market-wide move, with the NIFTY 50 shifting {nifty_ret:+.2f}%. "
                f"Contemporaneous headlines reported: \"{top_headline['title']}\" ({top_headline['source']})."
            )
        else:
            summary = (
                f"[Auto-generated without AI] {company_name} experienced a {direction} of {change_pct:+.1f}% "
                f"as part of a broader market-wide move, with the benchmark NIFTY 50 shifting {nifty_ret:+.2f}%. "
                f"Indexed news archives report no single isolated corporate catalyst."
            )
    elif classification == "Sector-wide move":
        sec_str = f"{sector_ret:+.2f}%" if sector_ret is not None else "significant shift"
        likely_reasons.append(f"Sector-wide move: {sector_name} moved {sec_str}")
        if top_headline:
            sources_used.append(top_headline.get("source", "Financial Press"))
            summary = (
                f"[Auto-generated without AI] {company_name} {direction} of {change_pct:+.1f}% aligned with a "
                f"sector-wide move across {sector_name} ({sec_str}). "
                f"Media coverage noted: \"{top_headline['title']}\" ({top_headline['source']})."
            )
        else:
            summary = (
                f"[Auto-generated without AI] {company_name} recorded a {direction} of {change_pct:+.1f}% "
                f"in tandem with a sector-wide move in {sector_name} ({sec_str}). "
                f"No specific company-specific press release was identified."
            )
    else:
        # Company specific move
        likely_reasons.append("Company-specific price movement diverging from broader index trends")
        if top_headline:
            sources_used.append(top_headline.get("source", "Financial Press"))
            likely_reasons.append(f"Media catalyst: \"{top_headline['title']}\"")
            summary = (
                f"[Auto-generated without AI] {company_name} moved {change_pct:+.1f}% in an isolated company-specific move "
                f"accompanied by {vol_multiplier:.1f}x average volume. "
                f"The move coincided with reporting from {top_headline['source']}: \"{top_headline['title']}\"."
            )
        elif corporate_events:
            summary = (
                f"[Auto-generated without AI] {company_name} moved {change_pct:+.1f}% alongside a scheduled corporate event "
                f"({corporate_events[0]}). The price change was primarily company-specific."
            )
        else:
            summary = (
                f"[Auto-generated without AI] {company_name} recorded a company-specific {direction} of {change_pct:+.1f}%. "
                f"The indexed news headlines do not explain the move, suggesting internal portfolio rebalancing or liquidity flow."
            )

    confidence = compute_confidence(
        classification=classification,
        has_news=has_news,
        vol_multiplier=vol_multiplier,
        has_corporate_events=bool(corporate_events)
    )

    return {
        "summary": summary,
        "likely_reasons": likely_reasons[:4],
        "confidence": confidence,
        "sources_used": list(dict.fromkeys(sources_used)),
        "is_ai_generated": False
    }

def validate_ai_explanation(data: Any, facts_payload: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Validates that the Gemini response strictly conforms to:
    {summary: str, likely_reasons: list[str], confidence: 'High'|'Medium'|'Low', sources_used: list[str]}
    
    CRITICAL GROUNDING CHECK (Hard Rule 1 Zero-Hallucination):
    Flags and rejects any claim containing financial metrics, currency amounts, or corporate actions
    that were NOT present in the supplied headlines or facts payload.
    """
    if not isinstance(data, dict):
        return None
    
    summary = data.get("summary")
    likely_reasons = data.get("likely_reasons")
    confidence = data.get("confidence")
    sources_used = data.get("sources_used")

    if not isinstance(summary, str) or not summary.strip():
        return None

    if not isinstance(likely_reasons, list) or not all(isinstance(r, str) for r in likely_reasons):
        return None

    if confidence not in ("High", "Medium", "Low"):
        return None

    if not isinstance(sources_used, list) or not all(isinstance(s, str) for s in sources_used):
        return None

    # Strict Grounding Verification if facts_payload provided
    if facts_payload:
        headlines = facts_payload.get("headlines", [])
        corp_events = facts_payload.get("corporate_events", [])
        has_news = len(headlines) > 0 or len(corp_events) > 0
        
        # Build reference corpus of all valid tokens from headlines and known facts
        reference_text = " ".join([
            h.get("title", "") for h in headlines
        ] + corp_events + [
            facts_payload.get("company_name", ""),
            facts_payload.get("ticker", ""),
            str(facts_payload.get("price_change_pct", "")),
            str(facts_payload.get("nifty_50_return_pct", "")),
            str(facts_payload.get("sector_return_pct", ""))
        ]).lower()

        # All text that makes factual claims: summary + each likely_reason
        claim_texts = [summary] + [r for r in likely_reasons if isinstance(r, str)]
        joined_claims = " ".join(claim_texts).lower()

        # Check 1: If NO news exists, verify AI doesn't invent a catalyst
        if not has_news:
            # Must mention lack of news, broader market, or sector/liquidity flow
            allowed_keywords = ["headline", "news", "not explain", "no clear", "market", "sector", "liquidity", "rebalancing", "profit-booking", "demand", "sentiment"]
            if not any(kw in summary.lower() for kw in allowed_keywords):
                # AI invented a specific reason when no news existed!
                return None

        # Check 2: Check for fabricated currency numbers / specific large figures in ALL claims
        # Detect patterns like "₹500 crore", "$2 billion" in summary AND likely_reasons
        for claim in claim_texts:
            financial_numbers = re.findall(
                r"(?:₹|\$|rs\.?|inr|usd)\s*[\d,]+(?:\.\d+)?(?:\s*(?:crore|lakh|billion|million))?",
                claim, re.IGNORECASE)
            for fn in financial_numbers:
                fn_clean = re.sub(r"[^\d.]", "", fn)
                if fn_clean and fn_clean not in reference_text:
                    # Fabricated financial number detected!
                    return None

        # Check 3: Every percentage claimed must match a percentage in the facts
        # payload (price change, NIFTY, sector, residual, gap). Magnitude must
        # match within rounding tolerance; unlisted percentages are fabricated.
        allowed_pcts = _allowed_pct_values(facts_payload)
        for claim in claim_texts:
            for claimed in _pct_claims(claim):
                if not any(abs(abs(claimed) - abs(allowed)) <= 0.06 for allowed in allowed_pcts):
                    return None

        # Check 4: Corporate-action claims (earnings, dividend, order, rating...)
        # may only appear when a supplied headline or corporate event mentions them.
        for stem in _CORPORATE_ACTION_STEMS:
            if stem in joined_claims and stem not in reference_text:
                return None

        # Check 5: sources_used must come from the supplied headlines' sources
        # (plus generic market-data attributions).
        supplied_sources = {h.get("source", "").strip().lower() for h in headlines if h.get("source")}
        valid_sources = supplied_sources | _NEWS_SOURCES_ALLOWED
        for src in sources_used:
            s = src.strip().lower()
            if not s:
                continue
            if not any(s in v or v in s for v in valid_sources):
                return None

    return {
        "summary": summary.strip(),
        "likely_reasons": [r.strip() for r in likely_reasons if r.strip()],
        "confidence": confidence,
        "sources_used": [s.strip() for s in sources_used if s.strip()],
        "is_ai_generated": True
    }

def _clean_json_text(text: str) -> str:
    """Removes markdown backticks and extra text surrounding JSON."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()

async def explain_price_movement(
    company_name: str,
    ticker: str,
    event_date: str,
    change_pct: float,
    direction: str,
    vol_multiplier: float,
    gap_pct: float,
    market_context: Dict[str, Any],
    news_res: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Main explainer orchestrator:
    1. Checks cache for instant exhibition demo speed.
    2. Constructs strict structured facts payload.
    3. If GEMINI_API_KEY present: calls Gemini with strict system prompt & requests JSON.
       Validates JSON output, retries once on failure, falls back to rule-based engine.
    4. If no key / API down: generates rule-based fallback clearly labelled 'Auto-generated without AI'.
    5. Caches and returns structured explanation.
    """
    cache_key = f"expl_v2:{ticker}:{event_date}"
    cached = get_cached(cache_key)
    if cached:
        return cached

    headlines = news_res.get("headlines", [])
    corporate_events = news_res.get("corporate_events", [])

    # Default fallback object
    fallback = generate_rule_based_fallback(
        company_name=company_name,
        ticker=ticker,
        event_date=event_date,
        change_pct=change_pct,
        direction=direction,
        vol_multiplier=vol_multiplier,
        gap_pct=gap_pct,
        market_context=market_context,
        headlines=headlines,
        corporate_events=corporate_events
    )

    if not GEMINI_API_KEY:
        set_cached(cache_key, fallback, ttl_seconds=86400 * 30)
        return fallback

    # Structured facts payload ONLY
    facts_payload = {
        "company_name": company_name,
        "ticker": ticker,
        "event_date": event_date,
        "price_change_pct": change_pct,
        "direction": direction,
        "volume_spike_multiplier": vol_multiplier,
        "gap_at_open_pct": gap_pct,
        "market_classification": market_context.get("classification", "Company-specific move"),
        "stock_return_pct": market_context.get("stock_return_pct", change_pct),
        "nifty_50_return_pct": market_context.get("nifty_return_pct", 0.0),
        "sector_return_pct": market_context.get("sector_return_pct"),
        "residual_move_pct": market_context.get("residual_pct", 0.0),
        "headlines": [
            {"title": h["title"], "source": h["source"], "date": h.get("date")}
            for h in headlines
        ],
        "corporate_events": corporate_events
    }

    user_prompt = (
        f"STRUCTURED FACTS DATA:\n{json.dumps(facts_payload, indent=2)}\n\n"
        "TASK:\n"
        "Return a valid JSON object matching this exact schema:\n"
        "{\n"
        '  "summary": "2-3 simple sentences explaining why the stock moved using ONLY supplied facts.",\n'
        '  "likely_reasons": ["short bullet reason 1", "short bullet reason 2"],\n'
        '  "confidence": "High" | "Medium" | "Low",\n'
        '  "sources_used": ["source 1", "source 2"]\n'
        "}\n"
        "CRITICAL RULES:\n"
        "- Do NOT invent any fact, figure, or reason.\n"
        "- Every number (including every percentage) must appear verbatim in the STRUCTURED FACTS DATA.\n"
        "- Only mention a corporate event (earnings, results, dividend, split, order, rating) if a supplied headline or corporate_events entry mentions it.\n"
        "- Only list sources that appear in the supplied headlines; otherwise use 'NSE Market Trading Data'.\n"
        "- If headlines do not explain the move, say so.\n"
        "- Mention if the move was market-wide or sector-wide.\n"
        "- High confidence requires company-specific classification + matching news + volume spike.\n"
        "- Respond with ONLY the raw JSON string."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    # Attempt with 1 retry
    for attempt in range(2):
        try:
            curr_prompt = user_prompt
            if attempt == 1:
                curr_prompt += "\nNOTE: Previous attempt did not validate. Ensure strict JSON conforming to schema."

            request_body = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"SYSTEM INSTRUCTION: {SYSTEM_PROMPT}\n\n{curr_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json"
                }
            }

            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, headers=headers, json=request_body)
                if res.status_code == 200:
                    res_json = res.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        clean_text = _clean_json_text(text_part)
                        parsed = json.loads(clean_text)
                        validated = validate_ai_explanation(parsed, facts_payload)
                        if validated:
                            set_cached(cache_key, validated, ttl_seconds=86400 * 30)
                            return validated
        except Exception:
            pass

    # If Gemini failed or was invalid, cache and return truthful rule-based fallback
    set_cached(cache_key, fallback, ttl_seconds=86400 * 30)
    return fallback

async def generate_event_explanation(
    company_name: str,
    ticker: str,
    event_date: str,
    change_pct: float,
    direction: str,
    news_res: Dict[str, Any]
) -> str:
    """
    Convenience wrapper for generating a plain-English explanation string for a price event.
    """
    try:
        res = await explain_price_movement(
            company_name=company_name,
            ticker=ticker,
            event_date=event_date,
            change_pct=change_pct,
            direction=direction,
            vol_multiplier=news_res.get("volume_spike_multiplier", 1.0),
            gap_pct=news_res.get("gap_pct", 0.0),
            market_context=news_res.get("market_context", {}),
            news_res=news_res
        )
        if isinstance(res, dict):
            return res.get("summary") or res.get("explanation") or str(res.get("details", ""))
        return str(res)
    except Exception:
        headline = news_res.get("headline", "")
        if headline:
            return f"Trading session on {event_date} saw {company_name} move {change_pct:+.1f}% amid reporting: '{headline}'."
        return f"Trading session on {event_date} saw {company_name} move {change_pct:+.1f}%. Market trading data suggests systematic liquidity and sector-wide sentiment shifts."
