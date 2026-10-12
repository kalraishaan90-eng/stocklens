import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


from app.main import analyze_stocks

from app.models.schemas import AnalyzeRequest


async def verify_company_anomalies(company_a: str, company_b: str):
    print(f"\n================================================================================")
    print(f"TESTING LIVE ANALYZE: {company_a} vs {company_b}")
    print(f"================================================================================")
    
    req = AnalyzeRequest(company_a=company_a, company_b=company_b, use_offline_demo=False)
    
    t0 = time.time()
    res = await analyze_stocks(req)
    t1 = time.time()
    print(f"Execution Time (First run): {t1 - t0:.2f}s")
    
    for comp_label, comp in [("Company A", res.company_a), ("Company B", res.company_b)]:
        print(f"\n--- {comp_label}: {comp.info.name} ({comp.info.ticker}) ---")
        print(f"Total Anomalies Detected: {len(comp.anomalies)}")
        
        # Verify chronological order
        dates = [a.date for a in comp.anomalies]
        print(f"Anomaly Dates: {dates}")
        
        if comp.recent_change:
            print(f"Recent Change (5-Day): {comp.recent_change.date} | Return: {comp.recent_change.change_pct:+.2f}%")
        
        for idx, anom in enumerate(comp.anomalies):
            print(f"\n  [Event {idx+1}] Date: {anom.date} | Return: {anom.change_pct:+.2f}% ({anom.direction})")
            print(f"    Volume Multiplier: {anom.volume_spike_multiplier}x | Gap: {anom.gap_pct:+.2f}%")
            
            if anom.market_context:
                mc = anom.market_context
                sec_str = f"{mc.sector_return_pct:+.2f}%" if mc.sector_return_pct is not None else "N/A"
                print(f"    Market Context -> Classification: [{mc.classification}]")
                print(f"    Three Numbers -> Stock: {mc.stock_return_pct:+.2f}%, NIFTY: {mc.nifty_return_pct:+.2f}%, Sector ({mc.sector_name}): {sec_str}")
                print(f"    Residual Move vs NIFTY: {mc.residual_pct:+.2f}%")
            
            print(f"    Confidence: {anom.confidence} | AI Generated: {anom.is_ai_generated}")
            print(f"    Corporate Events: {anom.corporate_events}")
            print(f"    Headlines Count: {len(anom.headlines)}")
            for h in anom.headlines[:2]:
                print(f"      - [{h.source}] {h.title}")
            print(f"    Explanation: {anom.explanation}")
            print(f"    Likely Reasons: {anom.likely_reasons}")
            print(f"    Sources Used: {anom.sources_used}")
            
            # Critical validation check:
            # If no headlines and no corporate events, explanation must not assert fake facts
            if not anom.headlines and not anom.corporate_events:
                assert ("not explain" in anom.explanation.lower() or "no specific" in anom.explanation.lower() or "no clear" in anom.explanation.lower() or "market-wide" in anom.explanation.lower() or "sector-wide" in anom.explanation.lower()), \
                    f"Violation of Hard Rule 1: Hallucinated reason for empty news on {anom.date}!"

    # Test cache performance: second run should be much faster
    t2 = time.time()
    res_cached = await analyze_stocks(req)
    t3 = time.time()
    print(f"\nExecution Time (Second run - Cached): {t3 - t2:.2f}s (Speedup: {(t1 - t0)/(t3 - t2 + 0.001):.1f}x)")
    assert len(res_cached.company_a.anomalies) == len(res.company_a.anomalies)

async def main():
    # 1. Test Reliance vs Titan
    await verify_company_anomalies("Reliance", "Titan")
    # 2. Test Adani Power vs Reliance
    await verify_company_anomalies("Adani Power", "Reliance")

if __name__ == "__main__":
    asyncio.run(main())
