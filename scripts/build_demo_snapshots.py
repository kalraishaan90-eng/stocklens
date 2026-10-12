#!/usr/bin/env python3
"""
scripts/build_demo_snapshots.py

Generates pre-fetched, fully analysed snapshots (price data, analytics, 
anomalies WITH their explanations and sources, recommendations, and verdicts) 
for all 9 exhibition project pairs from live market data, saving them in:
  backend/demo_data/<pair_key>.json

This ensures StockLens is completely exhibition-proof even with ZERO internet connection.
"""

import os
import sys
import json
import shutil
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.snapshot_service import ASSIGNED_PAIRS, save_demo_snapshot, DEMO_DATA_DIR
from app.services.ticker_resolver import resolve_ticker
from app.services.stock_data import fetch_stock_history_with_retry, fetch_benchmark_history
from app.services.analytics import (
    build_monthly_table,
    compute_monthly_series,
    compute_daily_series,
    compute_performance_metrics,
    compute_overlay_and_correlation,
    build_comparison_object,
)
from app.services.anomaly_detector import detect_price_anomalies, detect_recent_change
from app.services.news_fetcher import fetch_news_for_event
from app.services.gemini_analyzer import explain_price_movement, generate_event_explanation
from app.services.recommendation import generate_recommendation, compare_head_to_head
from app.services.market_classifier import analyze_market_context_for_events
from app.models.schemas import (
    CompanyInfo,
    CompanyAnalysis,
    ResolvedTickers,
    CompanyTickerInfo,
    MonthlyTableRow,
    MovingAverageRow,
    CompanyMetrics,
    MetricsPerCompany,
    RebasedOverlayPoint,
    ComparisonResult,
    RecommendationItem,
    RecommendationsPerCompany,
    AnomalyEvent,
    AnalysisMetadata,
    AnalysisResponse,
    MarketContext,
    NewsItem,
    PriceMovementEvent
)
from app.config import settings, GEMINI_API_KEY

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

async def build_snapshot_for_pair(pair: dict) -> AnalysisResponse:
    key = pair["key"]
    q1 = pair["query1"]
    q2 = pair["query2"]
    t1_expected = pair["ticker1"]
    t2_expected = pair["ticker2"]

    print(f"\n[{key.upper()}] Processing pair: {q1} ({t1_expected}) vs {q2} ({t2_expected})...")

    # 1. Resolve tickers
    t1, name1 = await resolve_ticker(q1)
    t2, name2 = await resolve_ticker(q2)
    print(f"  -> Resolved to: {name1} ({t1}) & {name2} ({t2})")

    # 2. Fetch price histories
    print("  -> Fetching historical 730-day price series...")
    (df1, meta1), (df2, meta2) = await asyncio.gather(
        fetch_stock_history_with_retry(t1),
        fetch_stock_history_with_retry(t2)
    )

    info1 = CompanyInfo(
        ticker=t1,
        name=meta1.get("longName", name1),
        sector=meta1.get("sector", pair.get("sector", "Diversified")),
        industry=meta1.get("industry", "General"),
        currency=meta1.get("currency", "INR"),
        exchange=meta1.get("exchange", "NSE")
    )
    info2 = CompanyInfo(
        ticker=t2,
        name=meta2.get("longName", name2),
        sector=meta2.get("sector", pair.get("sector", "Diversified")),
        industry=meta2.get("industry", "General"),
        currency=meta2.get("currency", "INR"),
        exchange=meta2.get("exchange", "NSE")
    )

    # 3. Analytics
    print("  -> Computing monthly resampling, 3M moving averages, and metrics...")
    bench_df = await fetch_benchmark_history()
    monthly1, monthly2, project_table = build_monthly_table(df1, df2)
    daily1 = compute_daily_series(df1)
    daily2 = compute_daily_series(df2)

    metrics1 = compute_performance_metrics(df1, benchmark_df=bench_df, risk_free_rate_pct=settings.RISK_FREE_RATE_PCT)
    metrics2 = compute_performance_metrics(df2, benchmark_df=bench_df, risk_free_rate_pct=settings.RISK_FREE_RATE_PCT)
    overlay_pts, correlation = compute_overlay_and_correlation(df1, df2)

    comp_obj = build_comparison_object(
        comp1_name=info1.name, comp1_ticker=info1.ticker, m1=metrics1,
        comp2_name=info2.name, comp2_ticker=info2.ticker, m2=metrics2
    )

    # 4. Recommendations & Head to Head
    print("  -> Evaluating transparent 6-signal scorecards and head-to-head verdict...")
    rec1 = generate_recommendation(metrics1, info1.name, df=df1, meta=meta1)
    rec2 = generate_recommendation(metrics2, info2.name, df=df2, meta=meta2)
    h2h = compare_head_to_head(info1, metrics1, rec1, info2, metrics2, rec2, df_a=df1, df_b=df2, meta_a=meta1, meta_b=meta2)

    # 5. Anomalies & Verified News Attribution
    print("  -> Detecting price anomalies & retrieving verified news...")
    anom1 = detect_price_anomalies(df1, max_events=4)
    anom2 = detect_price_anomalies(df2, max_events=4)
    rec_ev1 = detect_recent_change(df1)
    rec_ev2 = detect_recent_change(df2)

    items_to_eval1 = list(anom1) + ([rec_ev1] if rec_ev1 else [])
    items_to_eval2 = list(anom2) + ([rec_ev2] if rec_ev2 else [])

    enr1 = await analyze_market_context_for_events(df1, items_to_eval1, sector_str=info1.sector)
    enr2 = await analyze_market_context_for_events(df2, items_to_eval2, sector_str=info2.sector)

    async def _process_events(enriched_list, t_sym, c_name):
        events_list = []
        for it in enriched_list:
            dt = it["primary_date"]
            end_dt = it.get("end_date")
            chg = it["change_pct"]
            direct = it["direction"]
            vol_mult = it.get("volume_spike_multiplier", 1.0)
            gap = it.get("gap_pct", 0.0)
            m_ctx = it.get("market_context", {})

            news_res = await fetch_news_for_event(t_sym, c_name, dt, end_date_str=end_dt)
            expl = await explain_price_movement(
                company_name=c_name,
                ticker=t_sym,
                event_date=it["date"],
                change_pct=chg,
                direction=direct,
                vol_multiplier=vol_mult,
                gap_pct=gap,
                market_context=m_ctx,
                news_res=news_res
            )

            m_ctx_obj = None
            if m_ctx:
                m_ctx_obj = MarketContext(
                    stock_return_pct=m_ctx.get("stock_return_pct", chg),
                    nifty_return_pct=m_ctx.get("nifty_return_pct", 0.0),
                    sector_return_pct=m_ctx.get("sector_return_pct"),
                    residual_pct=m_ctx.get("residual_pct", 0.0),
                    classification=m_ctx.get("classification", "Company-specific move"),
                    sector_name=m_ctx.get("sector_name"),
                    explanation_factor=m_ctx.get("explanation_factor", "")
                )

            news_items = [
                NewsItem(title=h.get("title", ""), source=h.get("source", ""), url=h.get("url"), date=h.get("date"))
                for h in news_res.get("headlines", [])
            ]

            ev_obj = PriceMovementEvent(
                date=it["date"],
                start_date=it.get("start_date"),
                end_date=it.get("end_date"),
                change_pct=chg,
                direction=direct,
                volume_spike_multiplier=vol_mult,
                gap_pct=gap,
                market_context=m_ctx_obj,
                headlines=news_items,
                corporate_events=news_res.get("corporate_events", []),
                explanation=expl.get("summary", ""),
                likely_reasons=expl.get("likely_reasons", []),
                confidence=expl.get("confidence", "Medium"),
                sources_used=expl.get("sources_used", []),
                is_recent=it.get("is_recent", False),
                is_ai_generated=expl.get("is_ai_generated", False),
                headline=news_res.get("headline", "No specific corporate headline indexed for this session"),
                source=news_res.get("source", "Market Trading Data"),
                url=news_res.get("url")
            )
            events_list.append(ev_obj)
        return events_list

    evs1, evs2 = await asyncio.gather(
        _process_events(enr1, t1, info1.name),
        _process_events(enr2, t2, info2.name)
    )

    capture_date_str = datetime.now().strftime("%B %d, %Y")
    fetch_ts = datetime.now(timezone.utc).isoformat()

    # 6. Package modern contract fields
    resolved_tickers_contract = ResolvedTickers(
        company1=CompanyTickerInfo(query=q1, ticker=t1, name=info1.name, exchange=info1.exchange, currency=info1.currency),
        company2=CompanyTickerInfo(query=q2, ticker=t2, name=info2.name, exchange=info2.exchange, currency=info2.currency)
    )

    monthly_table_contract = [
        MonthlyTableRow(
            date=p1.date,
            month_label=p1.month_label,
            company1_adj_close=p1.adj_close,
            company2_adj_close=monthly2[idx].adj_close if idx < len(monthly2) else 0.0
        )
        for idx, p1 in enumerate(monthly1)
    ]

    moving_averages_contract = [
        MovingAverageRow(
            date=p1.date,
            month_label=p1.month_label,
            company1_ma_3m=p1.ma_3m,
            company2_ma_3m=monthly2[idx].ma_3m if idx < len(monthly2) else None
        )
        for idx, p1 in enumerate(monthly1)
    ]

    metrics_contract = MetricsPerCompany(
        company1=CompanyMetrics(
            ticker=t1, name=info1.name, current_price=metrics1.current_price,
            cagr_pct=metrics1.cagr_pct, annualized_volatility_pct=metrics1.annualized_volatility_pct,
            max_drawdown_pct=metrics1.max_drawdown_pct, sharpe_ratio=metrics1.sharpe_ratio,
            high_52w=metrics1.high_52w, low_52w=metrics1.low_52w,
            total_return_pct=metrics1.total_return_pct, positive_days_pct=metrics1.positive_days_pct
        ),
        company2=CompanyMetrics(
            ticker=t2, name=info2.name, current_price=metrics2.current_price,
            cagr_pct=metrics2.cagr_pct, annualized_volatility_pct=metrics2.annualized_volatility_pct,
            max_drawdown_pct=metrics2.max_drawdown_pct, sharpe_ratio=metrics2.sharpe_ratio,
            high_52w=metrics2.high_52w, low_52w=metrics2.low_52w,
            total_return_pct=metrics2.total_return_pct, positive_days_pct=metrics2.positive_days_pct
        )
    )

    rebased_points = [
        RebasedOverlayPoint(
            date=pt.date,
            company1_rebased=pt.company_a_rebased,
            company2_rebased=pt.company_b_rebased
        )
        for pt in overlay_pts
    ]

    comparison_contract = ComparisonResult(
        winner_ticker=h2h.winner_ticker,
        winner_name=h2h.winner_name,
        margin=h2h.margin,
        score_diff=h2h.score_diff,
        correlation_2y=correlation,
        verdict_text=h2h.verdict_text,
        rebased_overlay=rebased_points
    )

    recommendations_contract = RecommendationsPerCompany(
        company1=RecommendationItem(
            action=rec1.action,
            score=rec1.score,
            risk_level=rec1.risk_level,
            signals=rec1.signals,
            key_drivers=rec1.key_drivers,
            summary=rec1.summary,
            limitations=rec1.limitations
        ),
        company2=RecommendationItem(
            action=rec2.action,
            score=rec2.score,
            risk_level=rec2.risk_level,
            signals=rec2.signals,
            key_drivers=rec2.key_drivers,
            summary=rec2.summary,
            limitations=rec2.limitations
        )
    )

    anomalies_contract = []
    for ev in evs1:
        anomalies_contract.append(
            AnomalyEvent(
                **ev.model_dump(),
                company_key="company1",
                ticker=t1,
                company_name=info1.name
            )
        )
    for ev in evs2:
        anomalies_contract.append(
            AnomalyEvent(
                **ev.model_dump(),
                company_key="company2",
                ticker=t2,
                company_name=info2.name
            )
        )

    metadata_contract = AnalysisMetadata(
        data_source="Verified Historical Snapshot (Yahoo Finance & Google News Archive)",
        fetched_at=fetch_ts,
        is_offline_demo=True,
        demo_captured_at=capture_date_str,
        disclaimer="Educational project. Not financial advice. Historical performance does not guarantee future results.",
        causation_warning="Important Notice: Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news."
    )

    comp_a = CompanyAnalysis(
        info=info1,
        metrics=metrics1,
        monthly_series=monthly1,
        daily_series=daily1,
        recommendation=rec1,
        movement_events=evs1,
        anomalies=evs1
    )
    comp_b = CompanyAnalysis(
        info=info2,
        metrics=metrics2,
        monthly_series=monthly2,
        daily_series=daily2,
        recommendation=rec2,
        movement_events=evs2,
        anomalies=evs2
    )

    response = AnalysisResponse(
        resolved_tickers=resolved_tickers_contract,
        monthly_table=monthly_table_contract,
        moving_averages=moving_averages_contract,
        metrics=metrics_contract,
        comparison=comparison_contract,
        recommendations=recommendations_contract,
        anomalies=anomalies_contract,
        metadata=metadata_contract,
        company_a=comp_a,
        company_b=comp_b,
        correlation_2y=correlation,
        overlay_series=overlay_pts,
        head_to_head=h2h,
        is_offline_demo=True,
        demo_captured_at=capture_date_str,
        ai_engine="Google Gemini 1.5 Flash (Synthesized Context)" if GEMINI_API_KEY else "Deterministic Rule-Based Intelligence Engine",
        disclaimer="Educational project. Not financial advice. Historical performance does not guarantee future results.",
        causation_warning="Important Notice: Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news.",
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        project_template_table=project_table,
        comparison_object=comp_obj
    )

    return response

async def main():
    print("=" * 70)
    print("StockLens — Building Offline Demo Snapshots for All 9 Project Pairs")
    print("=" * 70)

    DEMO_DATA_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DEMO_DIR = PROJECT_ROOT / "frontend" / "public" / "demo-data"
    PUBLIC_DEMO_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for i, pair in enumerate(ASSIGNED_PAIRS, 1):
        key = pair["key"]
        print(f"\n[{i}/9] Generating snapshot for {pair['query1']} vs {pair['query2']} ({key})...")
        try:
            resp = await build_snapshot_for_pair(pair)
            save_path = save_demo_snapshot(key, resp.model_dump())
            shutil.copy2(save_path, PUBLIC_DEMO_DIR / save_path.name)
            size_kb = round(save_path.stat().st_size / 1024, 1)
            print(f"  ✓ SUCCESS: Saved snapshot '{save_path.name}' ({size_kb} KB)")
            manifest.append({
                "pair_key": key,
                "file": save_path.name,
                "company1": pair["name1"],
                "ticker1": pair["ticker1"],
                "company2": pair["name2"],
                "ticker2": pair["ticker2"],
                "captured_at": resp.demo_captured_at,
                "size_kb": size_kb,
                "status": "ready"
            })
        except Exception as exc:
            print(f"  ✗ FAILED to generate snapshot for '{key}': {exc}")
            import traceback
            traceback.print_exc()

    # Save manifest
    manifest_path = DEMO_DATA_DIR / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_pairs": len(ASSIGNED_PAIRS),
            "snapshots_built": len(manifest),
            "pairs": manifest
        }, f, indent=2)
    print(f"\nManifest written to: {manifest_path}")
    print(f"Completed: {len(manifest)}/{len(ASSIGNED_PAIRS)} demo snapshots generated successfully.")

if __name__ == "__main__":
    asyncio.run(main())
