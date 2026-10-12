"""
AI Explainer Stub for StockLens.
Synthesizes clear explanations for price movements using verified news or falls back to
deterministic macroeconomic context if no news is found.
"""
from typing import Dict, Any, Optional

def generate_explanation(company_name: str, event_date: str, change_pct: float, headline_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Stub returning placeholder anomaly explanation.
    """
    if headline_data and headline_data.get("headline"):
        return {
            "explanation": f"Move correlated with reported public news: {headline_data['headline']}",
            "confidence": "High"
        }
    return {
        "explanation": "No clear public reason found in indexed news feeds. Trading data indicates broader liquidity, index rebalancing, or systematic sector-wide sentiment shifts.",
        "confidence": "Estimated / Market Context"
    }
