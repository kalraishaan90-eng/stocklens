import math
from typing import List, Optional, Dict, Literal, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

def _sanitize_float_val(v: Any, default: Optional[float] = None) -> Optional[float]:
    if v is None:
        return default
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _sanitize_user_text(value: Any, field_name: str, max_length: int) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")
    cleaned = value.strip()
    if not cleaned or len(cleaned) > max_length:
        raise ValueError(f"{field_name} must contain 1 to {max_length} characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in cleaned):
        raise ValueError(f"{field_name} contains unsupported control characters")
    return cleaned

# --- Fundamental Company Information ---

class CompanyInfo(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = "Diversified"
    industry: Optional[str] = "General"
    currency: Optional[str] = "INR"
    exchange: Optional[str] = "NSE"
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    pe_ratio: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None

    @field_validator("market_cap", "fifty_two_week_high", "fifty_two_week_low", "pe_ratio", "dividend_yield", "beta", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=None)

class CompanyTickerInfo(BaseModel):
    query: str
    ticker: str
    name: str
    exchange: str = "NSE"
    currency: str = "INR"

# --- Symbol Resolution Models ---

class ResolvedSymbolMatch(BaseModel):
    ticker: str
    name: str
    exchange: str = "NSE"
    sector: Optional[str] = None
    is_ambiguous: bool = False
    restructuring_note: Optional[str] = None
    confidence_score: float = 100.0

class ResolveResponse(BaseModel):
    query: str
    match: Optional[ResolvedSymbolMatch] = None
    alternatives: List[ResolvedSymbolMatch] = Field(default_factory=list)
    is_ambiguous: bool = False
    restructuring_note: Optional[str] = None

# --- Price Points & Series ---

class DailyPricePoint(BaseModel):
    date: str
    close: float
    adj_close: float
    volume: int
    daily_return_pct: Optional[float] = None

    @field_validator("close", "adj_close", "daily_return_pct", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=0.0)

class MonthlyPricePoint(BaseModel):
    date: str
    month_label: str  # e.g. "Oct 2024"
    month_year: Optional[str] = None
    adj_close: float
    ma_3m: Optional[float] = None  # 3-Month Moving Average (first 2 values MUST be null)
    ma_6m: Optional[float] = None  # 6-Month Moving Average (first 5 values MUST be null)

    @field_validator("adj_close", mode="before")
    @classmethod
    def clean_close(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

    @field_validator("ma_3m", "ma_6m", mode="before")
    @classmethod
    def clean_ma(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=None)

class MonthlyTableRow(BaseModel):
    date: str
    month_label: str
    month_year: Optional[str] = None
    company1_adj_close: float
    company2_adj_close: float
    company1_ma: Optional[float] = None
    company2_ma: Optional[float] = None

    @field_validator("company1_adj_close", "company2_adj_close", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class MovingAverageRow(BaseModel):
    date: str
    month_label: str
    company1_ma_3m: Optional[float] = None
    company2_ma_3m: Optional[float] = None
    company1_ma_6m: Optional[float] = None
    company2_ma_6m: Optional[float] = None

    @field_validator("company1_ma_3m", "company2_ma_3m", "company1_ma_6m", "company2_ma_6m", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=None)

class ProjectTemplateTableRow(BaseModel):
    month_year: str
    company1_close: float
    company1_ma: Optional[float] = None
    company2_close: float
    company2_ma: Optional[float] = None
    company1_ma_6m: Optional[float] = None
    company2_ma_6m: Optional[float] = None

    @field_validator("company1_close", "company2_close", mode="before")
    @classmethod
    def clean_close(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

    @field_validator("company1_ma", "company2_ma", "company1_ma_6m", "company2_ma_6m", mode="before")
    @classmethod
    def clean_ma(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=None)

class OverlayPoint(BaseModel):
    date: str
    company_a_rebased: float  # Rebased to 100 on start date
    company_b_rebased: float

    @field_validator("company_a_rebased", "company_b_rebased", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=100.0)
        return val if val is not None else 100.0

class RebasedOverlayPoint(BaseModel):
    date: str
    company1_rebased: float
    company2_rebased: float

    @field_validator("company1_rebased", "company2_rebased", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=100.0)
        return val if val is not None else 100.0

class DayReturnPoint(BaseModel):
    date: str
    return_pct: float

    @field_validator("return_pct", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class MonthReturnPoint(BaseModel):
    month: Optional[str] = None
    month_label: Optional[str] = None
    return_pct: float

    @model_validator(mode="before")
    @classmethod
    def reconcile_month_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            m = data.get("month") or data.get("month_label") or ""
            data["month"] = m
            data["month_label"] = m
        return data

    @field_validator("return_pct", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

# --- Financial Metrics ---

class PerformanceMetrics(BaseModel):
    current_price: float
    cagr_pct: float
    annualized_volatility_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    high_52w: float
    low_52w: float
    total_return_pct: float
    positive_days_pct: float
    pe_ratio: Optional[float] = None
    
    monthly_return_std_pct: Optional[float] = None
    drawdown_peak_date: Optional[str] = None
    drawdown_trough_date: Optional[str] = None
    drawdown_recovery_date: Optional[str] = None
    best_day: Optional[DayReturnPoint] = None
    worst_day: Optional[DayReturnPoint] = None
    best_month: Optional[MonthReturnPoint] = None
    worst_month: Optional[MonthReturnPoint] = None
    beta_nifty: Optional[float] = None
    rsi_14: Optional[float] = None
    dma_50: Optional[float] = None
    price_vs_50_dma_status: Optional[str] = None
    price_vs_50_dma_pct: Optional[float] = None
    dma_200: Optional[float] = None
    price_vs_200_dma_status: Optional[str] = None
    price_vs_200_dma_pct: Optional[float] = None
    ma_3m_slope: Optional[str] = None
    momentum_3m_pct: Optional[float] = None
    coefficient_of_variation_monthly: Optional[float] = None
    trend_consistency_pct: Optional[float] = None
    stability_score: Optional[float] = None
    growth_score: Optional[float] = None

    @field_validator(
        "current_price", "cagr_pct", "annualized_volatility_pct", "max_drawdown_pct",
        "sharpe_ratio", "high_52w", "low_52w", "total_return_pct", "positive_days_pct",
        mode="before"
    )
    @classmethod
    def clean_required_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

    @field_validator(
        "pe_ratio", "monthly_return_std_pct", "beta_nifty", "rsi_14", "dma_50",
        "price_vs_50_dma_pct", "dma_200", "price_vs_200_dma_pct", "momentum_3m_pct",
        "coefficient_of_variation_monthly", "trend_consistency_pct", "stability_score", "growth_score",
        mode="before"
    )
    @classmethod
    def clean_optional_floats(cls, v: Any) -> Optional[float]:
        return _sanitize_float_val(v, default=None)

class CompanyMetrics(PerformanceMetrics):
    ticker: str
    name: str

class MetricsPerCompany(BaseModel):
    company1: CompanyMetrics
    company2: CompanyMetrics

class MetricComparisonItem(BaseModel):
    metric_key: str
    display_name: str
    company1_val: Any
    company2_val: Any
    winner_ticker: Optional[str] = None
    winner_name: Optional[str] = None
    advantage_pct: float = 0.0
    advantage_description: str = ""

    @field_validator("advantage_pct", mode="before")
    @classmethod
    def clean_adv(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class ComparisonObject(BaseModel):
    stability_winner: str
    stability_winner_ticker: str
    growth_winner: str
    growth_winner_ticker: str
    overall_winner: str
    overall_winner_ticker: str
    metrics: List[MetricComparisonItem] = Field(default_factory=list)
    sentences: List[str] = Field(default_factory=list)

class NewsItem(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    date: Optional[str] = None

class MarketContext(BaseModel):
    stock_return_pct: float
    nifty_return_pct: float
    sector_return_pct: Optional[float] = None
    residual_pct: float
    classification: Literal["Company-specific move", "Sector-wide move", "Market-wide move"]
    sector_name: Optional[str] = None
    explanation_factor: str

    @field_validator("stock_return_pct", "nifty_return_pct", "residual_pct", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class PriceMovementEvent(BaseModel):
    date: str
    change_pct: float
    direction: Literal["jump", "drop"]
    headline: str
    source: str
    url: Optional[str] = None
    explanation: str
    confidence: Literal["High", "Medium", "Low", "Estimated / Market Context"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    volume_spike_multiplier: Optional[float] = 1.0
    gap_pct: Optional[float] = 0.0
    market_context: Optional[MarketContext] = None
    headlines: List[NewsItem] = Field(default_factory=list)
    corporate_events: List[str] = Field(default_factory=list)
    likely_reasons: List[str] = Field(default_factory=list)
    sources_used: List[str] = Field(default_factory=list)
    is_recent: bool = False
    is_ai_generated: bool = False

    @field_validator("change_pct", mode="before")
    @classmethod
    def clean_change(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class AnomalyEvent(PriceMovementEvent):
    company_key: Optional[Literal["company1", "company2"]] = None
    ticker: Optional[str] = None
    company_name: Optional[str] = None

# --- Recommendation & Scorecard Schemas ---

class SignalScore(BaseModel):
    name: str
    category: str
    score: Optional[int] = None
    weight: float
    weighted_score: float
    reason: str
    is_available: bool = True

    @field_validator("weight", "weighted_score", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class InvestorProfileVerdict(BaseModel):
    profile: Literal["Conservative", "Balanced", "Aggressive"]
    winner_ticker: str
    winner_name: str
    score_a: float
    score_b: float
    rationale: str

    @field_validator("score_a", "score_b", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class Recommendation(BaseModel):
    action: Literal["BUY", "HOLD", "AVOID"]
    score: float
    risk_level: Literal["Low", "Medium", "Moderate", "High"]
    signals: List[SignalScore] = Field(default_factory=list)
    key_drivers: List[str] = Field(default_factory=list)
    summary: str
    limitations: List[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class RecommendationItem(BaseModel):
    action: Literal["BUY", "HOLD", "AVOID"]
    score: float
    risk_level: Literal["Low", "Medium", "Moderate", "High"]
    signals: List[SignalScore] = Field(default_factory=list)
    key_drivers: List[str] = Field(default_factory=list)
    summary: str
    limitations: List[str] = Field(default_factory=list)

    @field_validator("score", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class RecommendationsPerCompany(BaseModel):
    company1: RecommendationItem
    company2: RecommendationItem

# --- Head to Head Verdict ---

class HeadToHeadVerdict(BaseModel):
    winner_ticker: str
    winner_name: str
    margin: Literal["Dominant Outperformance", "Slight Edge", "Balanced / Tie"]
    verdict_text: str
    score_diff: float
    why_bullets: List[str] = Field(default_factory=list)
    when_other_better: str = ""
    investor_profiles: Optional[Dict[str, InvestorProfileVerdict]] = None
    comparison_summary: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    @field_validator("score_diff", mode="before")
    @classmethod
    def clean_diff(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class ComparisonResult(BaseModel):
    winner_ticker: str
    winner_name: str
    margin: Literal["Dominant Outperformance", "Slight Edge", "Balanced / Tie"]
    score_diff: float
    correlation_2y: float
    verdict_text: str
    rebased_overlay: List[RebasedOverlayPoint] = Field(default_factory=list)

    @field_validator("score_diff", "correlation_2y", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

# --- Company Analysis & Top-Level Response ---

class CompanyAnalysis(BaseModel):
    info: CompanyInfo
    metrics: PerformanceMetrics
    monthly_series: List[MonthlyPricePoint] = Field(default_factory=list)
    daily_series: List[DailyPricePoint] = Field(default_factory=list)
    recommendation: Recommendation
    movement_events: List[PriceMovementEvent] = Field(default_factory=list)
    anomalies: List[PriceMovementEvent] = Field(default_factory=list)
    recent_change: Optional[PriceMovementEvent] = None

class ResolvedTickers(BaseModel):
    company1: CompanyTickerInfo
    company2: CompanyTickerInfo

class AnalysisMetadata(BaseModel):
    data_source: str = "Yahoo Finance (Adjusted Close)"
    fetched_at: str
    is_offline_demo: bool = False
    demo_captured_at: Optional[str] = None
    disclaimer: str = "Educational project. Not financial advice. Historical performance does not guarantee future results."
    causation_warning: str = "Important Notice: Statistical correlation is not proof of causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news."

class AnalysisResponse(BaseModel):
    # Contract fields required by modern frontend UI
    resolved_tickers: ResolvedTickers
    monthly_table: List[MonthlyTableRow] = Field(default_factory=list)
    moving_averages: List[MovingAverageRow] = Field(default_factory=list)
    metrics: MetricsPerCompany
    comparison: ComparisonResult
    recommendations: RecommendationsPerCompany
    anomalies: List[AnomalyEvent] = Field(default_factory=list)
    metadata: AnalysisMetadata

    # Backward-compatible & extended fields
    company_a: Optional[CompanyAnalysis] = None
    company_b: Optional[CompanyAnalysis] = None
    correlation_2y: float = 0.0
    overlay_series: List[OverlayPoint] = Field(default_factory=list)
    head_to_head: Optional[HeadToHeadVerdict] = None
    is_offline_demo: bool = False
    demo_captured_at: Optional[str] = None
    ai_engine: str = "Deterministic Rule-Based Engine"
    disclaimer: str = "Educational project. Not financial advice. Historical performance does not guarantee future results."
    causation_warning: str = "Important Notice: Correlation does not imply causation. Market movements are influenced by complex macroeconomic, liquidity, and sentiment factors alongside reported news."
    generated_at: Optional[str] = None
    project_template_table: List[ProjectTemplateTableRow] = Field(default_factory=list)
    comparison_object: Optional[ComparisonObject] = None

    @field_validator("correlation_2y", mode="before")
    @classmethod
    def clean_corr(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

# --- API Request & Health Check Schemas ---

class AnalyzeRequest(BaseModel):
    company_a: Optional[str] = Field(default=None, max_length=120, description="First company name or ticker")
    company_b: Optional[str] = Field(default=None, max_length=120, description="Second company name or ticker")
    company1: Optional[str] = Field(default=None, max_length=120, description="Alias for company_a")
    company2: Optional[str] = Field(default=None, max_length=120, description="Alias for company_b")
    use_offline_demo: Optional[bool] = Field(default=False, description="Whether to use offline demo sample dataset")

    @field_validator("company_a", "company_b", "company1", "company2", mode="before")
    @classmethod
    def sanitize_company_queries(cls, value: Any, info: Any) -> Any:
        return _sanitize_user_text(value, info.field_name, 120)

    @model_validator(mode="before")
    @classmethod
    def populate_and_validate_companies(cls, data: Any) -> Any:
        if isinstance(data, dict):
            c1 = data.get("company1") or data.get("company_a")
            c2 = data.get("company2") or data.get("company_b")
            data["company1"] = c1
            data["company_a"] = c1
            data["company2"] = c2
            data["company_b"] = c2
            if not isinstance(c1, str) or not c1.strip() or not isinstance(c2, str) or not c2.strip():
                raise ValueError("Both company names or tickers must be provided.")
        return data

    def get_company_a(self) -> str:
        val = self.company_a or self.company1
        if not val or not str(val).strip():
            raise ValueError("Company 1 / Company A must be provided and cannot be empty.")
        return str(val).strip()

    def get_company_b(self) -> str:
        val = self.company_b or self.company2
        if not val or not str(val).strip():
            raise ValueError("Company 2 / Company B must be provided and cannot be empty.")
        return str(val).strip()

class ReportRequest(BaseModel):
    company_a: Optional[str] = Field(default=None, max_length=120, description="First company name or ticker")
    company_b: Optional[str] = Field(default=None, max_length=120, description="Second company name or ticker")
    company1: Optional[str] = Field(default=None, max_length=120, description="Alias for company_a")
    company2: Optional[str] = Field(default=None, max_length=120, description="Alias for company_b")
    student_name: Optional[str] = Field(default="Senior Secondary Student", max_length=100, description="Student Name for Cover Page")
    roll_number: Optional[str] = Field(default="SEC-2026-042", max_length=40, description="Student Roll Number for Cover Page")
    theme: Optional[Literal["dark", "light"]] = Field(default="dark", description="Visual theme: dark (editorial) or light (print-ink)")
    use_offline_demo: Optional[bool] = Field(default=False, description="Whether to use offline demo sample dataset")

    @field_validator("company_a", "company_b", "company1", "company2", mode="before")
    @classmethod
    def sanitize_company_queries(cls, value: Any, info: Any) -> Any:
        return _sanitize_user_text(value, info.field_name, 120)

    @field_validator("student_name", "roll_number", mode="before")
    @classmethod
    def sanitize_report_labels(cls, value: Any, info: Any) -> Any:
        max_length = 100 if info.field_name == "student_name" else 40
        return _sanitize_user_text(value, info.field_name, max_length)

    @model_validator(mode="before")
    @classmethod
    def populate_and_validate_companies(cls, data: Any) -> Any:
        if isinstance(data, dict):
            c1 = data.get("company1") or data.get("company_a")
            c2 = data.get("company2") or data.get("company_b")
            data["company1"] = c1
            data["company_a"] = c1
            data["company2"] = c2
            data["company_b"] = c2
            if not isinstance(c1, str) or not c1.strip() or not isinstance(c2, str) or not c2.strip():
                raise ValueError("Both company names or tickers must be provided.")
        return data

    def get_company_a(self) -> str:
        val = self.company_a or self.company1
        if not val or not str(val).strip():
            raise ValueError("Company 1 / Company A must be provided and cannot be empty.")
        return str(val).strip()

    def get_company_b(self) -> str:
        val = self.company_b or self.company2
        if not val or not str(val).strip():
            raise ValueError("Company 2 / Company B must be provided and cannot be empty.")
        return str(val).strip()

class HealthResponse(BaseModel):
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"
    service: str = "StockLens API"
    gemini_enabled: bool = False
    offline_demo_enabled: bool = True

# --- Price Fetcher, Quality & Index Schemas ---

class PriceRecord(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    @field_validator("open", "high", "low", "close", mode="before")
    @classmethod
    def clean_floats(cls, v: Any) -> float:
        val = _sanitize_float_val(v, default=0.0)
        return val if val is not None else 0.0

class DataQualityGap(BaseModel):
    from_date: str
    to_date: str
    calendar_days: int
    business_days_missing: int

class DataQualityReport(BaseModel):
    rows: int
    first_date: Optional[str] = None
    last_date: Optional[str] = None
    missing_days: int = 0
    has_gaps: bool = False
    gaps: List[DataQualityGap] = Field(default_factory=list)
    is_restructured_or_short: bool = False

class IndexPriceSeries(BaseModel):
    ticker: str
    name: str
    records: List[PriceRecord] = Field(default_factory=list)
    data_quality: Optional[DataQualityReport] = None

class PriceResponse(BaseModel):
    ticker: str
    company_info: CompanyInfo
    data_quality: DataQualityReport
    stale_data: bool = False
    cached: bool = False
    warning: Optional[str] = None
    restructuring_note: Optional[str] = None
    prices: List[PriceRecord] = Field(default_factory=list)
    benchmark: Optional[IndexPriceSeries] = None
    sector_index: Optional[IndexPriceSeries] = None
