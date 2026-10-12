// ── Full API Contract TypeScript Definitions ──
// Matches Pydantic schemas in backend/app/models/schemas.py.

// ── Symbol resolution ──
export interface ResolvedSymbolMatch {
  ticker: string;
  name: string;
  exchange?: string;
  sector?: string;
  is_ambiguous?: boolean;
  restructuring_note?: string;
  confidence_score?: number;
}

export interface ResolveResponse {
  query: string;
  match: ResolvedSymbolMatch | null;
  alternatives: ResolvedSymbolMatch[];
  is_ambiguous: boolean;
  restructuring_note?: string;
}

export interface ResolvedTickers {
  company1: CompanyTickerInfo;
  company2: CompanyTickerInfo;
}


export interface AnalyzeRequest {
  company1: string;
  company2: string;
  use_offline_demo?: boolean;
}
export interface CompanyTickerInfo {
  query: string;
  ticker: string;
  name: string;
  exchange: string;
  currency: string;
}

// ── Price series ──
export interface MonthlyPricePoint {
  date: string;
  month_label: string;
  month_year?: string;
  adj_close: number;
  ma_3m?: number | null;
  ma_6m?: number | null;
}

export interface DailyPricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  daily_return_pct?: number;
}

export interface MonthlyTableRow {
  date: string;
  month_label: string;
  company1_adj_close: number;
  company2_adj_close: number;
}

export interface MovingAverageRow {
  date: string;
  month_label: string;
  company1_ma_3m?: number | null;
  company2_ma_3m?: number | null;
}

export interface ProjectTemplateTableRow {
  month_year: string;
  company1_close: number;
  company1_ma?: number | null;
  company2_close: number;
  company2_ma?: number | null;
  company1_ma_6m?: number | null;
  company2_ma_6m?: number | null;
}

export interface OverlayPoint {
  date: string;
  company_a_rebased: number;
  company_b_rebased: number;
}

export interface RebasedOverlayPoint {
  date: string;
  company1_rebased: number;
  company2_rebased: number;
}

// ── Metrics ──
export interface PerformanceMetrics {
  current_price: number;
  cagr_pct: number;
  annualized_volatility_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  high_52w: number;
  low_52w: number;
  total_return_pct: number;
  positive_days_pct: number;
  beta_nifty?: number;
  rsi_14?: number;
  pe_ratio?: number;
  sector?: string;
}

export interface CompanyMetrics extends PerformanceMetrics {
  ticker: string;
  name: string;
}

export interface MetricsPerCompany {
  company1: CompanyMetrics;
  company2: CompanyMetrics;
}

// ── Chart / overlay ──
export interface ChartDataPoint {
  date: string;
  c1Price: number | null;
  c1MA: number | null;
  c1Rebased: number | null;
  c1PctChange: number | null;
  c2Price: number | null;
  c2MA: number | null;
  c2Rebased: number | null;
  c2PctChange: number | null;
}

export interface RebasedOverlayPoint {
  date: string;
  company1_rebased: number;
  company2_rebased: number;
}

export interface ComparisonResult {
  winner_ticker: string;
  winner_name: string;
  margin: 'Dominant Outperformance' | 'Slight Edge' | 'Balanced / Tie';
  score_diff: number;
  correlation_2y: number;
  verdict_text: string;
  rebased_overlay: RebasedOverlayPoint[];
}

// ── Recommendation ──
export interface Recommendation {
  action: 'BUY' | 'HOLD' | 'AVOID';
  score: number;
  risk_level: 'Low' | 'Medium' | 'Moderate' | 'High';
  signals: Array<{
    name: string;
    category: string;
    score: number | null;
    weight: number;
    weighted_score: number;
    reason: string;
    is_available: boolean;
  }>;
  key_drivers: string[];
  summary: string;
  limitations: string[];
}

export interface RecommendationItem {
  action: 'BUY' | 'HOLD' | 'AVOID';
  score: number;
  risk_level: 'Low' | 'Medium' | 'Moderate' | 'High';
  key_drivers: string[];
  summary: string;
}

export interface RecommendationsPerCompany {
  company1: RecommendationItem;
  company2: RecommendationItem;
}

// ── News ──
export interface NewsItem {
  title: string;
  source: string;
  url?: string;
  date?: string;
}

// ── Market context (classification) ──
export interface MarketContext {
  stock_return_pct: number;
  nifty_return_pct: number;
  sector_return_pct?: number;
  residual_pct: number;
  classification: 'Company-specific move' | 'Sector-wide move' | 'Market-wide move';
  sector_name?: string;
  explanation_factor: string;
}

// ── Anomaly events (from /api/analyze `anomalies[]`) ──
export interface PriceMovementEvent {
  date: string;
  change_pct: number;
  direction: 'jump' | 'drop';
  headline: string;
  source: string;
  url?: string | null;
  explanation: string;
  confidence: 'High' | 'Medium' | 'Low' | 'Estimated / Market Context';
  start_date?: string;
  end_date?: string;
  volume_spike_multiplier?: number;
  gap_pct?: number;
  market_context?: MarketContext;
  headlines: NewsItem[];
  corporate_events: string[];
  likely_reasons: string[];
  sources_used: string[];
  is_recent: boolean;
  is_ai_generated: boolean;
}

export interface AnomalyEvent extends PriceMovementEvent {
  company_key: 'company1' | 'company2';
  ticker: string;
  company_name: string;
}

// ── Top-level response ──
export interface CompanyAnalysis {
  info: {
    ticker: string;
    name: string;
    sector?: string;
    industry?: string;
    currency?: string;
    exchange?: string;
  };
  metrics: PerformanceMetrics;
  monthly_series: MonthlyPricePoint[];
  daily_series: DailyPricePoint[];
  recommendation: Recommendation;
  movement_events: PriceMovementEvent[];
  anomalies: AnomalyEvent[];
  recent_change?: PriceMovementEvent;
}

export interface AnalysisMetadata {
  data_source: string;
  fetched_at: string;
  is_offline_demo: boolean;
  demo_captured_at?: string;
  disclaimer: string;
  causation_warning: string;
}

export interface AnalysisResponse {
  resolved_tickers: ResolvedTickers;
  monthly_table: MonthlyTableRow[];
  moving_averages: MovingAverageRow[];
  metrics: MetricsPerCompany;
  comparison: ComparisonResult;
  recommendations: RecommendationsPerCompany;
  anomalies: AnomalyEvent[];
  metadata: AnalysisMetadata;

  company_a?: CompanyAnalysis | null;
  company_b?: CompanyAnalysis | null;
  comparison_object?: {
    stability_winner: string;
    stability_winner_ticker: string;
    growth_winner: string;
    growth_winner_ticker: string;
    overall_winner: string;
    overall_winner_ticker: string;
    metrics: Array<{
      metric_key: string;
      display_name: string;
      company1_val: any;
      company2_val: any;
      winner_ticker?: string;
      winner_name?: string;
      advantage_pct: number;
      advantage_description: string;
    }>;
    sentences: string[];
    why_bullets: string[];
    investor_profiles?: Record<
      'Conservative' | 'Balanced' | 'Aggressive',
      {
        profile: string;
        winner_ticker: string;
        winner_name: string;
        score_a: number;
        score_b: number;
        rationale: string;
      }
    > | null;
  } | null;
  head_to_head?: {
    winner_ticker: string;
    winner_name: string;
    margin: string;
    verdict_text: string;
    score_diff: number;
    why_bullets: string[];
    when_other_better: string;
    investor_profiles?: Record<
      'Conservative' | 'Balanced' | 'Aggressive',
      {
        profile: string;
        winner_ticker: string;
        winner_name: string;
        score_a: number;
        score_b: number;
        rationale: string;
      }
    > | null;
    comparison_summary: string[];
    limitations: string[];
  } | null;
  overlay_series?: RebasedOverlayPoint[];
  correlation_2y?: number;
  is_offline_demo?: boolean;
  demo_captured_at?: string;
  ai_engine?: string;
  disclaimer?: string;
  causation_warning?: string;
  generated_at?: string;
  project_template_table?: ProjectTemplateTableRow[];
}

// ── Health / errors ──
export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  service: string;
  gemini_enabled: boolean;
  offline_demo_enabled: boolean;
}

export interface ApiErrorResponse {
  error: boolean;
  status_code: number;
  message: string;
  detail?: any;
  details?: any[];
  timestamp: string;
}
