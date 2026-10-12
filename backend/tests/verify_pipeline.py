import asyncio
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.schemas import AnalyzeRequest
from app.main import analyze_stocks

async def main():
    print("Testing /api/analyze pipeline with HAL vs Mazagon Dock (Offline Mode)...")
    req = AnalyzeRequest(company_a="HAL", company_b="Mazagon Dock", use_offline_demo=True)
    res = await analyze_stocks(req)
    print("Pipeline Execution Succeeded!")
    print(f"Company A: {res.company_a.info.name} ({res.company_a.info.ticker})")
    print(f"Company B: {res.company_b.info.name} ({res.company_b.info.ticker})")
    print(f"CAGR A: {res.company_a.metrics.cagr_pct}% | CAGR B: {res.company_b.metrics.cagr_pct}%")
    print(f"Annualized Volatility A: {res.company_a.metrics.annualized_volatility_pct}% | B: {res.company_b.metrics.annualized_volatility_pct}%")
    print(f"Sharpe Ratio A: {res.company_a.metrics.sharpe_ratio:.2f} | B: {res.company_b.metrics.sharpe_ratio:.2f}")
    print(f"Monthly Datapoints: A={len(res.company_a.monthly_series)}, B={len(res.company_b.monthly_series)}")
    print(f"Head-to-Head Winner: {res.head_to_head.winner_name} [{res.head_to_head.margin}]")
    print(f"Anomaly Events Count: A={len(res.company_a.movement_events)}, B={len(res.company_b.movement_events)}")
    if res.company_a.movement_events:
        ev = res.company_a.movement_events[0]
        print(f"Sample Anomaly Event: {ev.date} | {ev.change_pct}% | Headline: '{ev.headline[:45]}...' | Source: {ev.source}")
    print(f"Causation Warning: {res.causation_warning}")
    print(f"Disclaimer: {res.disclaimer}")

if __name__ == "__main__":
    asyncio.run(main())
