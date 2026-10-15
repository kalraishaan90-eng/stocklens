import asyncio
import sys
if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass
import os
import re
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from math import ceil
from threading import Lock
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Query, status, Response, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings, GEMINI_API_KEY, OFFLINE_DEMO_ENABLED
from app.logger import logger
from app.models.schemas import (
    AnalyzeRequest,
    AnalysisResponse,
    HealthResponse,
    CompanyInfo,
    CompanyAnalysis,
    NewsItem,
    ResolveResponse,
    PriceResponse,
    ResolvedTickers,
    CompanyTickerInfo,
    MetricsPerCompany,
    CompanyMetrics,
    ComparisonResult,
    RecommendationsPerCompany,
    RecommendationItem,
    AnalysisMetadata,
    MonthlyPricePoint,
    DailyPricePoint,
    MonthlyTableRow,
    MovingAverageRow,
    ProjectTemplateTableRow,
    PriceMovementEvent,
    AnomalyEvent,
    PerformanceMetrics,
    ComparisonObject,
    RebasedOverlayPoint,
    ReportRequest,
    MarketContext
)
from app.services.report_service import (
    generate_report_html,
    generate_pdf_report,
    generate_template_table_csv,
    generate_google_sheets_csv
)
from app.services.ticker_resolver import (
    resolve_ticker,
    resolve_symbol,
    verify_assigned_tickers,
    COMMON_TICKER_MAP,
)
from app.services.stock_data import (
    fetch_stock_history_with_retry,
    fetch_benchmark_history,
    fetch_ticker_prices,
)
from app.services.analytics import (
    build_monthly_table,
    compute_daily_series,
    compute_performance_metrics,
    compute_overlay_and_correlation,
    build_comparison_object
)
from app.services.anomaly_detector import detect_price_anomalies, detect_recent_change
from app.services.market_classifier import analyze_market_context_for_events
from app.services.news_fetcher import fetch_news_for_event
from app.services.gemini_analyzer import explain_price_movement
from app.services.recommendation import generate_recommendation, compare_head_to_head
from app.services.snapshot_service import get_pair_key, load_demo_snapshot

_ANALYSIS_CACHE: dict[str, tuple[float, AnalysisResponse]] = {}
_ANALYSIS_CACHE_TTL_SECONDS = 600
_RATE_WINDOW_SECONDS = 60.0
_ANALYZE_REQUESTS: dict[str, deque[float]] = {}
_ANALYZE_RATE_LOCK = Lock()


def enforce_analyze_rate_limit(request: Request) -> None:
    """Apply a bounded per-process sliding-window limit using the socket peer IP."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    limit = max(1, settings.ANALYZE_RATE_LIMIT_PER_MINUTE)
    with _ANALYZE_RATE_LOCK:
        recent = _ANALYZE_REQUESTS.setdefault(client_ip, deque())
        while recent and now - recent[0] >= _RATE_WINDOW_SECONDS:
            recent.popleft()
        if len(recent) >= limit:
            retry_after = max(1, ceil(_RATE_WINDOW_SECONDS - (now - recent[0])))
            raise HTTPException(status_code=429, detail="Analysis rate limit exceeded. Try again shortly.", headers={"Retry-After": str(retry_after)})
        recent.append(now)
        if len(_ANALYZE_REQUESTS) > 10_000:
            expired = [ip for ip, timestamps in _ANALYZE_REQUESTS.items() if not timestamps or now - timestamps[-1] >= _RATE_WINDOW_SECONDS]
            for ip in expired:
                _ANALYZE_REQUESTS.pop(ip, None)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup hook: pre-load alias maps (done at module import) and verify the
    18 assigned tickers via live Yahoo Finance lookup. Warnings for missing,
    short, or restructured ticker histories are logged and stored in
    STARTUP_VERIFIED_STATUS so /api/resolve and /api/prices can surface
    them as UI notes. Runs in the background so boot is not blocked.
    """
    verify_enabled = os.getenv("VERIFY_TICKERS_ON_STARTUP", "true").lower() in ("true", "1", "yes")
    if verify_enabled:
        app.state.ticker_verification_task = asyncio.create_task(verify_assigned_tickers(live=True))
    else:
        app.state.ticker_verification_task = None
    yield
    task = getattr(app.state, "ticker_verification_task", None)
    if task and not task.done():
        task.cancel()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Dual Stock Comparative Analytics, Moving Averages, Volatility & AI Narrative Engine",
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Accept", "Content-Type"],
)

# 2. Structured Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Completed {request.method} {request.url.path} with status {response.status_code} in {duration_ms}ms")
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(f"Unhandled exception during {request.method} {request.url.path} after {duration_ms}ms: {str(exc)}", exc_info=True)
        raise

# 3. Global Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTPException on {request.url.path}: status={exc.status_code} detail={exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": True, "status_code": exc.status_code, "message": exc.detail, "timestamp": datetime.now(timezone.utc).isoformat()},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    status_code = 400 if request.url.path == "/api/analyze" else status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse(
        status_code=status_code,
        content={"error": True, "status_code": status_code, "message": "Validation Error: Invalid request payload", "timestamp": datetime.now(timezone.utc).isoformat()}
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception intercepted on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": True, "status_code": 500, "message": "An internal server error occurred.", "timestamp": datetime.now(timezone.utc).isoformat()}
    )

# 4. Health Check Endpoint
@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Returns server status, Gemini integration status, and configuration info."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=settings.VERSION,
        service=settings.PROJECT_NAME,
        gemini_enabled=bool(settings.GEMINI_API_KEY),
        offline_demo_enabled=settings.OFFLINE_DEMO_ENABLED
    )

# 5. Autocomplete Search Endpoint
@app.get("/api/search")
async def search_tickers(q: str = Query(..., min_length=1, max_length=80)):
    """Provides instant suggestions for stock search autocomplete."""
    if any(ord(char) < 32 or ord(char) == 127 for char in q):
        raise HTTPException(status_code=422, detail="Query contains unsupported control characters.")
    query = q.lower().strip()
    results = []
    for alias, (ticker, name) in COMMON_TICKER_MAP.items():
        if query in alias or query in ticker.lower() or query in name.lower():
            if not any(r["ticker"] == ticker for r in results):
                results.append({"name": name, "ticker": ticker, "display": f"{name} ({ticker})"})
        if len(results) >= 8:
            break
    return {"results": results}

# 5b. Symbol Resolver Endpoint
@app.get("/api/resolve", response_model=ResolveResponse)
async def resolve_company_symbol(q: str = Query(..., min_length=1, max_length=120, description="Free-text company name or ticker")) -> ResolveResponse:
    """
    Resolves a free-text company name (e.g. "HAL", "hindustan aeronautics",
    "Bajaj Finserv", "HDFC Bank") to a Yahoo Finance ticker.
    Prefers NSE (.NS), then BSE (.BO). Returns the top match plus up to 3
    alternatives (company name, exchange, sector). If the query is ambiguous,
    is_ambiguous=true and alternatives are returned so the UI can ask the
    user to confirm. Typos are handled via rapidfuzz fuzzy matching over the
    built-in alias map, with Yahoo Finance search as fallback.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' must contain non-whitespace characters.")
    if any(ord(char) < 32 or ord(char) == 127 for char in q):
        raise HTTPException(status_code=422, detail="Query contains unsupported control characters.")
    logger.info(f"Resolving symbol for query: '{q}'")
    try:
        result = await resolve_symbol(q)
        return result
    except Exception as e:
        logger.error(f"Symbol resolution failed for '{q}': {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to resolve symbol: {str(e)}")


# 5c. Price Fetcher Endpoint
@app.get("/api/prices/{ticker}", response_model=PriceResponse)
async def get_ticker_prices(
    ticker: str,
    days: int = Query(730, ge=30, le=730, description="Lookback window in calendar days (default 730)"),
    force_live: bool = Query(False, description="Bypass the fresh disk cache and force a live fetch")
) -> PriceResponse:
    """
    Fetches daily OHLCV for the given ticker over the last `days` days
    (yfinance, auto_adjust=True so closes are adjusted), plus the NIFTY 50
    benchmark (^NSEI) and the relevant sector index when one exists.
    Data is cleaned (NaN drop, <=3 trading-day forward fill, gap detection,
    timezone-naive sorted DatetimeIndex) and accompanied by a data quality
    report. Results are disk-cached with a 6-hour TTL; if the live fetch
    fails, stale cache is served with stale_data=true.
    """
    clean_ticker = ticker.strip().upper()
    if len(clean_ticker) > 24 or not re.fullmatch(r"[A-Z0-9^.=\-]+", clean_ticker):
        raise HTTPException(status_code=422, detail="Ticker contains unsupported characters.")
    logger.info(f"Fetching prices: ticker={clean_ticker}, days={days}, force_live={force_live}")
    try:
        return await fetch_ticker_prices(clean_ticker, days=days, force_live=force_live)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"Price fetch failed for '{clean_ticker}': {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Failed to fetch price data for '{clean_ticker}': {str(e)}")


# 6. Main Comparative Analysis Endpoint
async def _analyze_stocks_live(payload: AnalyzeRequest) -> AnalysisResponse:
    """
    Main comparative analysis orchestrator:
    1. Resolves company queries to validated NSE tickers.
    2. Fetches 2-year dynamic historical data (with offline demo fallback).
    3. Builds aligned monthly summaries, 3M & 6M MA, and template table shape.
    4. Computes volatility, CAGR, max drawdown, Sharpe, Beta, RSI, DMA, slope, momentum.
    5. Calculates 0-100 Stability and Growth Scores using documented weights.
    6. Programmatically generates 5-8 plain-English comparative sentences.
    7. Detects price anomalies and correlates with contemporaneous news headlines.
    """
    try:
        comp_a_str = payload.get_company_a()
        comp_b_str = payload.get_company_b()
    except ValueError as ve:
        # Graceful degradation for empty/missing company inputs (no 500s)
        raise HTTPException(status_code=400, detail=str(ve))
    is_offline = bool(payload.use_offline_demo) and OFFLINE_DEMO_ENABLED
    pair_key = get_pair_key(comp_a_str, comp_b_str)
    if is_offline and pair_key:
        snapshot = load_demo_snapshot(pair_key)
        if snapshot:
            return AnalysisResponse.model_validate(snapshot)

    logger.info(f"Analyzing stocks live from web: company_a='{comp_a_str}', company_b='{comp_b_str}'")

    # 1. Resolve tickers
    try:
        ticker_a, name_a = await resolve_ticker(comp_a_str)
        ticker_b, name_b = await resolve_ticker(comp_b_str)
    except Exception as e:
        logger.error(f"Failed to resolve company names: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to resolve company names: {str(e)}")

    df_a, meta_a = None, {}
    df_b, meta_b = None, {}

    # 2. Fetch price data live from Yahoo Finance
    try:
        fetch_tasks = [
            fetch_stock_history_with_retry(ticker_a),
            fetch_stock_history_with_retry(ticker_b)
        ]
        (df_a, meta_a), (df_b, meta_b) = await asyncio.gather(*fetch_tasks)
    except Exception as e:
        logger.error(f"Live market data fetch failed for '{ticker_a}' / '{ticker_b}': {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Error retrieving stock data: {str(e)}. Please check your internet connection or ticker symbol."
        )

    info_a = CompanyInfo(
        ticker=ticker_a,
        name=meta_a.get("longName", name_a),
        sector=meta_a.get("sector", "Diversified"),
        industry=meta_a.get("industry", "General"),
        currency=meta_a.get("currency", "INR"),
        exchange=meta_a.get("exchange", "NSE")
    )
    info_b = CompanyInfo(
        ticker=ticker_b,
        name=meta_b.get("longName", name_b),
        sector=meta_b.get("sector", "Diversified"),
        industry=meta_b.get("industry", "General"),
        currency=meta_b.get("currency", "INR"),
        exchange=meta_b.get("exchange", "NSE")
    )

    # 3. Analytics Engine (Sections A, B, C, D, E, F, G)
    bench_df = await fetch_benchmark_history()

    monthly_a, monthly_b, project_template_table = build_monthly_table(df_a, df_b)
    daily_a = compute_daily_series(df_a)
    daily_b = compute_daily_series(df_b)

    metrics_a = compute_performance_metrics(df_a, benchmark_df=bench_df, risk_free_rate_pct=settings.RISK_FREE_RATE_PCT)
    metrics_b = compute_performance_metrics(df_b, benchmark_df=bench_df, risk_free_rate_pct=settings.RISK_FREE_RATE_PCT)

    overlay_pts, correlation = compute_overlay_and_correlation(df_a, df_b)

    comparison_obj = build_comparison_object(
        comp1_name=info_a.name,
        comp1_ticker=info_a.ticker,
        m1=metrics_a,
        comp2_name=info_b.name,
        comp2_ticker=info_b.ticker,
        m2=metrics_b
    )

    # 4. Recommendations & Head to Head
    rec_a = generate_recommendation(metrics_a, info_a.name, df=df_a, meta=meta_a)
    rec_b = generate_recommendation(metrics_b, info_b.name, df=df_b, meta=meta_b)
    h2h = compare_head_to_head(
        info_a, metrics_a, rec_a,
        info_b, metrics_b, rec_b,
        df_a=df_a, df_b=df_b,
        meta_a=meta_a, meta_b=meta_b
    )

    # 5. Price Anomalies & Explanations (Spike Detection + Market Classification + News + AI/Rule-based Narrative)
    anomalies_a = detect_price_anomalies(df_a, max_events=6)
    anomalies_b = detect_price_anomalies(df_b, max_events=6)

    recent_a = detect_recent_change(df_a)
    recent_b = detect_recent_change(df_b)

    # Market context enrichment for all events
    events_to_analyze_a = list(anomalies_a)
    if recent_a:
        events_to_analyze_a.append(recent_a)

    events_to_analyze_b = list(anomalies_b)
    if recent_b:
        events_to_analyze_b.append(recent_b)

    enriched_a = await analyze_market_context_for_events(df_a, events_to_analyze_a, sector_str=info_a.sector)
    enriched_b = await analyze_market_context_for_events(df_b, events_to_analyze_b, sector_str=info_b.sector)

    async def _process_single_anomaly(item: Dict[str, Any], t_sym: str, c_name: str) -> PriceMovementEvent:
        dt = item["primary_date"]
        end_dt = item.get("end_date")
        chg = item["change_pct"]
        direct = item["direction"]
        vol_mult = item.get("volume_spike_multiplier", 1.0)
        gap = item.get("gap_pct", 0.0)
        m_ctx = item.get("market_context", {})

        try:
            news_res = await asyncio.wait_for(
                fetch_news_for_event(t_sym, c_name, dt, end_date_str=end_dt),
                timeout=2.5
            )
        except Exception:
            news_res = {
                "headlines": [],
                "corporate_events": [],
                "has_news": False,
                "headline": "No specific headline indexed for this session",
                "source": "Market Trading Data",
                "url": None
            }

        try:
            expl = await asyncio.wait_for(
                explain_price_movement(
                    company_name=c_name,
                    ticker=t_sym,
                    event_date=item["date"],
                    change_pct=chg,
                    direction=direct,
                    vol_multiplier=vol_mult,
                    gap_pct=gap,
                    market_context=m_ctx,
                    news_res=news_res
                ),
                timeout=2.5
            )
        except Exception:
            expl = {
                "summary": f"{c_name} recorded a {chg:+.2f}% price movement on {item['date']}.",
                "likely_reasons": ["Trading volume shift", "Market volatility"],
                "confidence": "Medium",
                "sources_used": ["Market Trading Data"],
                "is_ai_generated": False
            }

        market_ctx_obj = None
        if m_ctx:
            market_ctx_obj = MarketContext(
                stock_return_pct=m_ctx.get("stock_return_pct", chg),
                nifty_return_pct=m_ctx.get("nifty_return_pct", 0.0),
                sector_return_pct=m_ctx.get("sector_return_pct"),
                residual_pct=m_ctx.get("residual_pct", 0.0),
                classification=m_ctx.get("classification", "Company-specific move"),
                sector_name=m_ctx.get("sector_name"),
                explanation_factor=m_ctx.get("explanation_factor", "")
            )

        news_items = [
            NewsItem(
                title=h.get("title", ""),
                source=h.get("source", ""),
                url=h.get("url"),
                date=h.get("date")
            )
            for h in news_res.get("headlines", [])
        ]

        return PriceMovementEvent(
            date=item["date"],
            start_date=item.get("start_date"),
            end_date=item.get("end_date"),
            change_pct=chg,
            direction=direct,
            volume_spike_multiplier=vol_mult,
            gap_pct=gap,
            market_context=market_ctx_obj,
            headlines=news_items,
            corporate_events=news_res.get("corporate_events", []),
            explanation=expl.get("summary", ""),
            likely_reasons=expl.get("likely_reasons", []),
            confidence=expl.get("confidence", "Medium"),
            sources_used=expl.get("sources_used", []),
            is_recent=item.get("is_recent", False),
            is_ai_generated=expl.get("is_ai_generated", False),
            headline=news_res.get("headline", "No specific headline indexed"),
            source=news_res.get("source", "Market Trading Data"),
            url=news_res.get("url")
        )

    async def _process_anomalies(enriched_list, t_sym, c_name):
        tasks = [_process_single_anomaly(item, t_sym, c_name) for item in enriched_list]
        processed = await asyncio.gather(*tasks) if tasks else []
        events = [ev for ev in processed if not ev.is_recent]
        recent_ev = next((ev for ev in processed if ev.is_recent), None)
        return events, recent_ev

    (events_a, recent_ev_a), (events_b, recent_ev_b) = await asyncio.gather(
        _process_anomalies(enriched_a, ticker_a, info_a.name),
        _process_anomalies(enriched_b, ticker_b, info_b.name)
    )

    # Top-level anomalies list consumed by the frontend (enriched with ticker/company context)
    anomaly_objs: List[AnomalyEvent] = []
    for _key, _ticker, _name, _evs, _recent in (
        ("company1", ticker_a, info_a.name, events_a, recent_ev_a),
        ("company2", ticker_b, info_b.name, events_b, recent_ev_b),
    ):
        for _ev in _evs:
            anomaly_objs.append(AnomalyEvent(
                **_ev.model_dump(), company_key=_key, ticker=_ticker, company_name=_name
            ))
        if _recent is not None and abs(_recent.change_pct) >= 3.2:
            anomaly_objs.append(AnomalyEvent(
                **_recent.model_dump(), company_key=_key, ticker=_ticker, company_name=_name
            ))

    comp_a = CompanyAnalysis(
        info=info_a,
        metrics=metrics_a,
        monthly_series=monthly_a,
        daily_series=daily_a,
        recommendation=rec_a,
        movement_events=events_a,
        anomalies=events_a,
        recent_change=recent_ev_a
    )
    comp_b = CompanyAnalysis(
        info=info_b,
        metrics=metrics_b,
        monthly_series=monthly_b,
        daily_series=daily_b,
        recommendation=rec_b,
        movement_events=events_b,
        anomalies=events_b,
        recent_change=recent_ev_b
    )


    # Backward compatibility tables
    monthly_table_legacy = [
        MonthlyTableRow(
            date=row.date,
            month_label=row.month_label,
            month_year=row.month_year,
            company1_adj_close=row.adj_close,
            company2_adj_close=monthly_b[idx].adj_close if idx < len(monthly_b) else 0.0,
            company1_ma=row.ma_3m,
            company2_ma=monthly_b[idx].ma_3m if idx < len(monthly_b) else None
        )
        for idx, row in enumerate(monthly_a)
    ]
    moving_averages_legacy = [
        MovingAverageRow(
            date=row.date,
            month_label=row.month_label,
            company1_ma_3m=row.ma_3m,
            company2_ma_3m=monthly_b[idx].ma_3m if idx < len(monthly_b) else None,
            company1_ma_6m=row.ma_6m,
            company2_ma_6m=monthly_b[idx].ma_6m if idx < len(monthly_b) else None
        )
        for idx, row in enumerate(monthly_a)
    ]

    ai_label = "Google Gemini 1.5 Flash (Synthesized Context)" if GEMINI_API_KEY else "Deterministic Rule-Based Intelligence Engine"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Modern frontend contract fields (required by AnalysisResponse schema)
    resolved_tickers = ResolvedTickers(
        company1=CompanyTickerInfo(
            query=comp_a_str,
            ticker=info_a.ticker,
            name=info_a.name,
            exchange=info_a.exchange or "NSE",
            currency=info_a.currency or "INR"
        ),
        company2=CompanyTickerInfo(
            query=comp_b_str,
            ticker=info_b.ticker,
            name=info_b.name,
            exchange=info_b.exchange or "NSE",
            currency=info_b.currency or "INR"
        )
    )
    metrics_per_company = MetricsPerCompany(
        company1=CompanyMetrics(**metrics_a.model_dump(), ticker=info_a.ticker, name=info_a.name),
        company2=CompanyMetrics(**metrics_b.model_dump(), ticker=info_b.ticker, name=info_b.name)
    )
    comparison_result = ComparisonResult(
        winner_ticker=h2h.winner_ticker,
        winner_name=h2h.winner_name,
        margin=h2h.margin,
        score_diff=h2h.score_diff,
        correlation_2y=correlation,
        verdict_text=h2h.verdict_text,
        rebased_overlay=[RebasedOverlayPoint(date=p.date, company1_rebased=p.company_a_rebased, company2_rebased=p.company_b_rebased) for p in overlay_pts]
    )
    recommendations_per_company = RecommendationsPerCompany(
        company1=RecommendationItem(
            action=rec_a.action,
            score=rec_a.score,
            risk_level=rec_a.risk_level,
            signals=rec_a.signals,
            key_drivers=rec_a.key_drivers,
            summary=rec_a.summary,
            limitations=rec_a.limitations
        ),
        company2=RecommendationItem(
            action=rec_b.action,
            score=rec_b.score,
            risk_level=rec_b.risk_level,
            signals=rec_b.signals,
            key_drivers=rec_b.key_drivers,
            summary=rec_b.summary,
            limitations=rec_b.limitations
        )
    )
    analysis_metadata = AnalysisMetadata(
        data_source=("Offline demonstration snapshot (Adjusted Close)" if is_offline else "Yahoo Finance (Adjusted Close)"),
        fetched_at=generated_at,
        is_offline_demo=is_offline,
        demo_captured_at=generated_at if is_offline else None
    )

    return AnalysisResponse(
        resolved_tickers=resolved_tickers,
        metrics=metrics_per_company,
        comparison=comparison_result,
        recommendations=recommendations_per_company,
        metadata=analysis_metadata,
        anomalies=anomaly_objs,
        company_a=comp_a,
        company_b=comp_b,
        correlation_2y=correlation,
        overlay_series=overlay_pts,
        head_to_head=h2h,
        is_offline_demo=is_offline,
        ai_engine=ai_label,
        disclaimer="Educational project. Not financial advice. Historical performance does not guarantee future results.",
        causation_warning="Important Notice: Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news.",
        generated_at=generated_at,
        project_template_table=project_template_table,
        comparison_object=comparison_obj,
        monthly_table=monthly_table_legacy,
        moving_averages=moving_averages_legacy
    )


@app.post("/api/analyze", response_model=AnalysisResponse, dependencies=[Depends(enforce_analyze_rate_limit)])
async def analyze_stocks(payload: AnalyzeRequest) -> AnalysisResponse:
    """Analyze live first; serve a captured, date-stamped result when that fails."""
    pair_key = get_pair_key(payload.get_company_a(), payload.get_company_b())
    if pair_key and (OFFLINE_DEMO_ENABLED or payload.use_offline_demo):
        snapshot = load_demo_snapshot(pair_key)
        if snapshot:
            return AnalysisResponse.model_validate(snapshot)

    cache_key = "|".join((payload.get_company_a().strip().casefold(), payload.get_company_b().strip().casefold()))
    cached = _ANALYSIS_CACHE.get(cache_key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    _ANALYSIS_CACHE.pop(cache_key, None)

    timeout_sec = int(os.getenv("ANALYZE_TIMEOUT_SECONDS", "75"))
    try:
        result = await asyncio.wait_for(_analyze_stocks_live(payload), timeout=timeout_sec)
        if len(_ANALYSIS_CACHE) >= 30:
            _ANALYSIS_CACHE.clear()
        _ANALYSIS_CACHE[cache_key] = (time.monotonic() + _ANALYSIS_CACHE_TTL_SECONDS, result)
        return result
    except Exception as exc:
        logger.warning(f"Live analysis encountered an issue ({exc}). Checking fallback snapshots...")
        if pair_key:
            snapshot = load_demo_snapshot(pair_key)
            if snapshot:
                return AnalysisResponse.model_validate(snapshot)
        if isinstance(exc, HTTPException):
            raise exc
        logger.error(f"Analysis failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")


@app.post("/api/report/pdf")
async def download_report_pdf(payload: ReportRequest):
    """
    Generates and returns an exhibition-grade academic science project PDF report.
    Supports dark editorial and light-ink print themes, with server-side rendered charts,
    formula breakdowns, anomaly attribution, and Playwright PDF printing.
    """
    req = AnalyzeRequest(
        company_a=payload.get_company_a(),
        company_b=payload.get_company_b(),
        use_offline_demo=payload.use_offline_demo
    )
    analysis = await analyze_stocks(req)

    theme = payload.theme or "dark"
    student = payload.student_name or "Senior Secondary Student"
    roll = payload.roll_number or "SEC-2026-042"

    pdf_bytes = await generate_pdf_report(
        analysis=analysis,
        student_name=student,
        roll_number=roll,
        theme=theme
    )

    t_a = analysis.company_a.info.ticker
    t_b = analysis.company_b.info.ticker
    filename = f"StockLens_Report_{t_a}_vs_{t_b}_{theme}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-StockLens-Theme": theme,
            "X-StockLens-Student": student
        }
    )


@app.post("/api/report/html")
async def preview_report_html(payload: ReportRequest):
    """
    Generates and returns the print-styled HTML report for browser preview.
    """
    req = AnalyzeRequest(
        company_a=payload.get_company_a(),
        company_b=payload.get_company_b(),
        use_offline_demo=payload.use_offline_demo
    )
    analysis = await analyze_stocks(req)

    theme = payload.theme or "dark"
    student = payload.student_name or "Senior Secondary Student"
    roll = payload.roll_number or "SEC-2026-042"

    html_content = await generate_report_html(
        analysis=analysis,
        student_name=student,
        roll_number=roll,
        theme=theme
    )

    return Response(content=html_content, media_type="text/html")


@app.api_route("/api/report/csv", methods=["GET", "POST"])
async def export_template_csv(
    company_a: Optional[str] = Query(None),
    company_b: Optional[str] = Query(None),
    company1: Optional[str] = Query(None),
    company2: Optional[str] = Query(None),
    use_offline_demo: Optional[bool] = Query(False),
    request: Request = None
):
    """
    Exports the official project template table as standard CSV.
    Columns: Month-Year, Company1 Close, Company1 3M-MA, Company2 Close, Company2 3M-MA.
    """
    c1 = company_a or company1
    c2 = company_b or company2
    demo = use_offline_demo

    if request and request.method == "POST":
        try:
            body = await request.json()
            c1 = body.get("company_a") or body.get("company1") or c1
            c2 = body.get("company_b") or body.get("company2") or c2
            if "use_offline_demo" in body:
                demo = bool(body["use_offline_demo"])
        except Exception:
            pass

    c1 = c1 or "HAL"
    c2 = c2 or "Mazagon Dock"

    req = AnalyzeRequest(company_a=c1, company_b=c2, use_offline_demo=demo)
    analysis = await analyze_stocks(req)

    csv_data = generate_template_table_csv(analysis)
    t_a = analysis.company_a.info.ticker
    t_b = analysis.company_b.info.ticker
    filename = f"StockLens_Template_{t_a}_vs_{t_b}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.api_route("/api/report/sheets-csv", methods=["GET", "POST"])
async def export_sheets_csv(
    company_a: Optional[str] = Query(None),
    company_b: Optional[str] = Query(None),
    company1: Optional[str] = Query(None),
    company2: Optional[str] = Query(None),
    use_offline_demo: Optional[bool] = Query(False),
    request: Request = None
):
    """
    Exports CSV structured for Google Sheets demonstration, complete with
    GOOGLEFINANCE guide syntax and =AVERAGE(...) rolling moving average formulas.
    """
    c1 = company_a or company1
    c2 = company_b or company2
    demo = use_offline_demo

    if request and request.method == "POST":
        try:
            body = await request.json()
            c1 = body.get("company_a") or body.get("company1") or c1
            c2 = body.get("company_b") or body.get("company2") or c2
            if "use_offline_demo" in body:
                demo = bool(body["use_offline_demo"])
        except Exception:
            pass

    c1 = c1 or "HAL"
    c2 = c2 or "Mazagon Dock"

    req = AnalyzeRequest(company_a=c1, company_b=c2, use_offline_demo=demo)
    analysis = await analyze_stocks(req)

    csv_data = generate_google_sheets_csv(analysis)
    t_a = analysis.company_a.info.ticker
    t_b = analysis.company_b.info.ticker
    filename = f"StockLens_GoogleSheets_{t_a}_vs_{t_b}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
