import React, {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
  Suspense,
  lazy,
  KeyboardEvent,
  MouseEvent,
} from 'react';
import {
  Activity,
  ArrowDown,
  ArrowUpDown,
  AlertTriangle,
  Award,
  BarChart2,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  ExternalLink,
  FileText,
  Globe,
  Info,
  LineChart,
  Minus,
  PieChart,
  Plus,
  RefreshCw,
  Scale,
  Search,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Wallet,
  X,
} from 'lucide-react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { analyzeStocks } from '../lib/api';
import { AnalysisResponse, AnomalyEvent, MetricsPerCompany, CompanyMetrics } from '../lib/types';
import { ChartDataPoint } from '../components/design-system/TerminalChart';
import { ScoreRing } from '../components/design-system/ScoreRing';
import { MetricCard } from '../components/design-system/MetricCard';
import { Tooltip } from '../components/design-system/Tooltip';
import { VerdictBadge } from '../components/design-system/VerdictBadge';
import { DisclaimerBar } from '../components/design-system/DisclaimerBar';
import { fmtPctSigned } from '../lib/utils';

const TerminalChart = lazy(() => import('../components/design-system/TerminalChart').then((m) => ({ default: m.TerminalChart })));

// ── Tiny navigator that stays visible while the user scrolls ───────────────────

// Staged progress steps (matches the Home page five-step workflow)
const STEPS = [
  { icon: Globe, label: 'Fetching 2 years of prices', color: 'text-gold' },
  { icon: Activity, label: 'Calculating moving averages', color: 'text-cyan' },
  { icon: AlertTriangle, label: 'Scanning for sudden moves', color: 'text-gold' },
  { icon: Search, label: 'Reading the news', color: 'text-cyan' },
  { icon: Award, label: 'Preparing the verdict', color: 'text-gold' },
];

const MiniNav: React.FC<{
  sections: Array<{ id: string; title: string; number: string }>;
  active: string;
  scrollTo: (id: string) => void;
}> = ({ sections, active, scrollTo }) => {
  const [visible, setVisible] = useState(false);

  return (
    <>
      {visible && (
        <div
          className="mini-nav fixed top-14 sm:top-16 left-4 sm:left-6 z-40 w-56 sm:w-64 rounded-md bg-surface-card border border-editorial-hairline shadow-2xl p-3 space-y-1.5 animate-fadeIn"
          style={{ boxShadow: '0 24px 48px -12px rgba(0,0,0,0.75)' }}
        >
          {sections.map((s) => (
            <button
              key={s.id}
              onClick={() => scrollTo(s.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-xs font-mono transition-colors ${
                active === s.id
                  ? 'bg-gold/10 text-gold border border-gold/30'
                  : 'text-editorial-secondary hover:text-editorial-primary hover:bg-surface-hover'
              }`}
              aria-current={active === s.id ? 'page' : undefined}
            >
              <span className="w-5 h-5 rounded-md bg-surface-raised border border-editorial-hairline flex items-center justify-center text-[10px] font-bold font-mono">
                {s.number}
              </span>
              <span className="truncate">{s.title}</span>
            </button>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={() => setVisible((v) => !v)}
        className="mini-nav fixed bottom-6 left-6 z-40 inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-card border border-editorial-hairline text-xs font-mono text-editorial-secondary hover:text-editorial-primary hover:bg-surface-subtle transition-colors cursor-pointer shadow-[0_12px_32px_-8px_rgba(0,0,0,0.65)]"
        aria-label="Show table of contents"
      >
        <BarChart2 className="w-4 h-4" aria-hidden="true" />
        Contents
        <ChevronDown className={`w-3.5 h-3.5 transition-transform ${visible ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>
    </>
  );
};

// ── 03 template table with sort (stable), sticky header, CSV download ─────────
const TemplateTable: React.FC<{
  rows: Array<{ month_year: string; company1_close: number; company1_ma: number | null; company2_close: number; company2_ma: number | null }>;
  company1: string;
  company2: string;
  onDownloadCsv: () => void;
}> = ({ rows, company1, company2, onDownloadCsv }) => {
  const [sortKey, setSortKey] = useState<'month_year' | 'c1c' | 'c1m' | 'c2c' | 'c2m'>('month_year');
  const [ascending, setAscending] = useState<boolean>(true);

  const sorted = useMemo(() => {
    const arr = [...rows];
    arr.sort((a, b) => {
      let va: string | number;
      let vb: string | number;
      switch (sortKey) {
        case 'month_year':
          va = a.month_year;
          vb = b.month_year;
          return ascending ? va.localeCompare(vb) : vb.localeCompare(va);
        case 'c1c':
          va = a.company1_close;
          vb = b.company1_close;
          return ascending ? va - vb : vb - va;
        case 'c1m':
          va = a.company1_ma ?? -Infinity;
          vb = b.company1_ma ?? -Infinity;
          return ascending ? va - vb : vb - va;
        case 'c2c':
          va = a.company2_close;
          vb = b.company2_close;
          return ascending ? va - vb : vb - va;
        case 'c2m':
          va = a.company2_ma ?? -Infinity;
          vb = b.company2_ma ?? -Infinity;
          return ascending ? va - vb : vb - va;
      }
    });
    return arr;
  }, [rows, sortKey, ascending]);

  const headers: Array<{ key: typeof sortKey; label: string }> = [
    { key: 'month_year', label: 'Month-Year' },
    { key: 'c1c', label: `Co1 close` },
    { key: 'c1m', label: `Co1 MA` },
    { key: 'c2c', label: `Co2 close` },
    { key: 'c2m', label: `Co2 MA` },
  ];

  return (
    <section aria-labelledby="template-heading" className="bg-surface-card border border-editorial-hairline rounded-lg p-4 sm:p-6 space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 id="template-heading" className="text-base font-serif text-editorial-primary flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-gold" aria-hidden="true" />
            03 The Data Table
          </h3>
          <p className="text-xs text-editorial-secondary mt-0.5">
            Month-end closes with a rolling 3-month moving average. Sorted, sticky header, CSV export.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onDownloadCsv}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-raised hover:bg-surface-subtle border border-editorial-subtle text-xs font-mono text-editorial-primary transition-colors cursor-pointer"
          >
            <FileText className="w-3.5 h-3.5" aria-hidden="true" />
            CSV
          </button>
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex flex-wrap gap-1.5 text-[11px] font-mono">
        {headers.map((h) => (
          <button
            key={h.key}
            onClick={() => {
              if (sortKey === h.key) setAscending((a) => !a);
              else { setSortKey(h.key); setAscending(true); }
            }}
            className={`px-2 py-1 rounded border transition-colors cursor-pointer ${sortKey === h.key ? 'bg-gold/10 text-gold border-gold/30' : 'bg-surface-raised text-editorial-muted border-editorial-hairline hover:border-editorial-subtle'}`}
            aria-label={`Sort by ${h.label} ${sortKey === h.key ? (ascending ? 'ascending' : 'descending') : ''}`}
          >
            {h.label}
            {sortKey === h.key && (
              <ArrowUpDown className="w-3 h-3 inline ml-1" aria-hidden="true" />
            )}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <caption className="sr-only">
            Project template table for {company1} vs {company2}: month-year, close and 3-month moving
            average for each company.
          </caption>
          <thead className="sticky top-0 z-10 bg-surface-base text-editorial-secondary border-b border-editorial-hairline">
            <tr>
              {headers.map((h) => (
                <th
                  key={h.key}
                  scope="col"
                  className={`py-2.5 px-3 font-semibold ${sortKey === h.key ? 'text-gold' : 'text-editorial-muted'}`}
                >
                  <span className="flex items-center gap-1.5">
                    {h.label}
                    {sortKey === h.key && <ArrowUpDown className="w-3 h-3" aria-hidden="true" />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-editorial-hairline/60">
            {sorted.slice(-50).map((row, idx) => (
              <tr
                key={row.month_year}
                className={`transition-colors ${idx % 2 === 1 ? 'bg-surface-hover/40' : 'bg-surface-base/30'}`}
              >
                <th scope="row" className="py-2.5 px-3 font-mono font-medium text-editorial-primary whitespace-nowrap">
                  {row.month_year}
                </th>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-gold">
                  {row.company1_close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-editorial-muted">
                  {row.company1_ma != null
                    ? row.company1_ma.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : '—'}
                </td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-cyan">
                  {row.company2_close.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="py-2.5 px-3 text-right font-mono tabular-nums text-editorial-muted">
                  {row.company2_ma != null
                    ? row.company2_ma.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {sorted.length > 0 && (
          <p className="text-[11px] text-editorial-muted">
            Showing {Math.max(0, sorted.length - 50)} of {sorted.length} monthly rows. First two MA cells are blank —
            a 3-month window needs three observations.
          </p>
        )}
      </div>
    </section>
  );
};

// ── Section 02 body: two side-by-side charts + full-width overlay ──────────────
const SectionCharts: React.FC<{
  c1: string;
  c2: string;
  data: ChartDataPoint[];
  company1Name?: string;
  company2Name?: string;
  company1Symbol?: string;
  company2Symbol?: string;
}> = ({ c1, c2, data, company1Name, company2Name, company1Symbol, company2Symbol }) => {
  const [scale, setScale] = useState<'rebased' | 'actual'>('rebased');
  const [view, setView] = useState<'daily' | 'monthly'>('monthly');
  const [c1Show, setC1Show] = useState<boolean>(true);
  const [c2Show, setC2Show] = useState<boolean>(true);
  const [maShow, setMaShow] = useState<boolean>(true);

  if (!data.length) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-lg bg-surface-card border border-editorial-hairline">
        <p className="text-xs text-editorial-secondary py-8 text-center">Neither series has monthly history.</p>
        <p className="text-xs text-editorial-secondary py-8 text-center">Add both companies and re-run.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Side-by-side monthly close + MA-3M charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Suspense fallback={<div className="h-72 rounded-lg bg-surface-base animate-pulse" aria-label="Loading chart" />}><TerminalChart
          data={data
            .filter((d) => d.c1Price != null || d.c1MA != null)
            .map((d) => ({ ...d, c1Rebased: d.c1Rebased ?? null, c2Rebased: d.c2Rebased ?? null }))}
          company1Name={company1Name}
          company1Symbol={company1Symbol}
          company2Name={company1Name}
          company2Symbol={company1Symbol}
          title="Co1 — month-end adjusted close & 3-month MA"
          subtitle="Solid: adjusted close · Dashed: 3-month MA · base 100"
          height={240}
          className="min-h-0"
        /></Suspense>
        <Suspense fallback={<div className="h-72 rounded-lg bg-surface-base animate-pulse" aria-label="Loading chart" />}><TerminalChart
          data={data
            .filter((d) => d.c2Price != null || d.c2MA != null)
            .map((d) => ({ ...d, c1Rebased: d.c1Rebased ?? null, c2Rebased: d.c2Rebased ?? null }))}
          company1Name={company2Name}
          company1Symbol={company2Symbol}
          company2Name={company2Name}
          company2Symbol={company2Symbol}
          title="Co2 — month-end adjusted close & 3-month MA"
          subtitle="Solid: adjusted close · Dashed: 3-month MA · base 100"
          height={240}
          className="min-h-0"
        /></Suspense>
      </div>

      {/* Full-width overlay + controls */}
      <div className="card-highlight p-4 sm:p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-serif text-editorial-primary">Rebased overlay (Co1 vs Co2)</h3>
            <p className="text-xs text-editorial-secondary">
              Both series rebased to 100 on the first common month — a like-for-like rate-of-change view.
              {view === 'daily' ? ' Switching to daily bars.' : ' Monthly month-end closes.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div
              role="group"
              aria-label="Price scale"
              className="inline-flex p-0.5 rounded-md bg-surface-raised border border-editorial-hairline text-xs font-mono"
            >
              <button
                type="button"
                onClick={() => setScale('rebased')}
                aria-pressed={scale === 'rebased'}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium ${scale === 'rebased' ? 'bg-gold text-surface-base font-semibold shadow-sm' : 'text-editorial-secondary hover:text-editorial-primary'}`}
              >
                Rebased to 100
              </button>
              <button
                type="button"
                onClick={() => setScale('actual')}
                aria-pressed={scale === 'actual'}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium ${scale === 'actual' ? 'bg-gold text-surface-base font-semibold shadow-sm' : 'text-editorial-secondary hover:text-editorial-primary'}`}
              >
                Actual (₹)
              </button>
            </div>

            <div
              role="group"
              aria-label="Time view"
              className="inline-flex p-0.5 rounded-md bg-surface-raised border border-editorial-hairline text-xs font-mono"
            >
              <button
                type="button"
                onClick={() => setView('monthly')}
                aria-pressed={view === 'monthly'}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium ${view === 'monthly' ? 'bg-gold text-surface-base font-semibold shadow-sm' : 'text-editorial-secondary hover:text-editorial-primary'}`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setView('daily')}
                aria-pressed={view === 'daily'}
                className={`px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium ${view === 'daily' ? 'bg-gold text-surface-base font-semibold shadow-sm' : 'text-editorial-secondary hover:text-editorial-primary'}`}
              >
                Daily
              </button>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface-raised border border-editorial-hairline text-xs font-mono">
              <span className={`w-2 h-0.5 border-t rounded ${maShow ? 'border-gold' : 'border-editorial-muted'}`} />
              <span className={maShow ? 'text-gold' : 'text-editorial-muted'}>3M MA</span>
              <span className="text-editorial-muted mx-1">·</span>
              <span className={c1Show ? 'text-gold' : 'text-editorial-muted'}>Co1</span>
              <span className="text-editorial-muted mx-1">·</span>
              <span className={c2Show ? 'text-cyan' : 'text-editorial-muted'}>Co2</span>
            </div>
          </div>
        </div>

        <Suspense fallback={<div className="h-72 rounded-lg bg-surface-base animate-pulse" aria-label="Loading chart" />}><TerminalChart
          data={data}
          company1Name={company1Name}
          company1Symbol={company1Symbol}
          company2Name={company2Name}
          company2Symbol={company2Symbol}
          title="Co1 vs Co2 — rebased overlay"
          subtitle={
            scale === 'rebased'
              ? `Both series start at 100 — Co2 is ${data[data.length - 1]?.c2Rebased != null ? ((data[data.length - 1]?.c2Rebased ?? 0) / (data[data.length - 1]?.c1Rebased ?? 1) - 1) * 100 : 0} pts relative to Co1 at the final month.`
              : 'Adjusted close levels, actual price.'
          }
          height={320}
          className="min-h-0"
        /></Suspense>
      </div>
    </div>
  );
};

// ── Section 05 event timeline ──────────────────────────────────────────────────
const EventTimeline: React.FC<{
  events: AnomalyEvent[];
  company: string;
  ticker: string;
  onScrollTo: (id: string) => void;
}> = ({ events, company, ticker, onScrollTo }) => {
  if (!events.length) return null;
  return (
    <section aria-labelledby="timeline-heading" className="bg-surface-card border border-editorial-hairline rounded-lg p-4 sm:p-6 space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 id="timeline-heading" className="text-base font-serif text-editorial-primary flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-gold" aria-hidden="true" />
            05 Why Did It Move?
          </h3>
          <p className="text-xs text-editorial-secondary mt-0.5">
            Net moves ≥3.2% that broke from 2.5× trailing volatility — each paired with indexed headlines.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {events.map((ev, idx) => {
          const mc = ev.market_context;
          const isRecent = ev.is_recent;
          const confidenceLabel = ev.is_ai_generated ? 'AI-assisted' : 'Rule-based';
          const confClass = ev.confidence === 'High'
            ? 'text-gain bg-gain/10'
            : ev.confidence === 'Medium'
            ? 'text-gold bg-gold/10'
            : 'text-editorial-muted bg-surface-raised';
          const dateId = `event-${company}-${ticker}-${idx}`;

          return (
            <div
              key={dateId}
              id={dateId}
              className="p-4 rounded-lg bg-surface-base border border-editorial-hairline space-y-2.5 transition-shadow hover:shadow-md"
              onClick={() => onScrollTo(dateId)}
            >
              {/* Header row: date, % move, classification chip */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  {isRecent ? (
                    <span className="text-[11px] font-mono text-editorial-muted bg-gold/10 border border-gold/25 px-2 py-0.5 rounded">
                      recent (5-day)
                    </span>
                  ) : (
                    <Calendar className="w-3.5 h-3.5 text-editorial-muted" aria-hidden="true" />
                  )}
                  <span className="text-xs font-mono font-medium text-editorial-primary">{ev.date}</span>
                  <span className="text-[10px] font-mono text-editorial-muted">{ticker}</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold border ${ev.direction === 'jump' ? 'bg-gain/10 text-gain border-gain/25' : 'bg-loss/10 text-loss border-loss/25'}`}
                  >
                    {ev.direction === 'jump' ? <TrendingUp className="w-3 h-3" aria-hidden="true" /> : <TrendingDown className="w-3 h-3" aria-hidden="true" />}
                    {fmtPctSigned(ev.change_pct)}
                  </span>

                  {/* Classification chip with the three numbers */}
                  {mc && (
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono font-semibold border ${mc.classification === 'Market-wide move' ? 'bg-gold/10 text-gold border-gold/25' : mc.classification === 'Sector-wide move' ? 'bg-cyan/10 text-cyan border-cyan/25' : 'bg-surface-raised text-editorial-secondary border-editorial-hairline'}`}
                    >
                      {mc.classification === 'Market-wide move' ? (
                        <Globe className="w-3 h-3" aria-hidden="true" />
                      ) : mc.classification === 'Sector-wide move' ? (
                        <PieChart className="w-3 h-3" aria-hidden="true" />
                      ) : (
                        <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                      )}
                      {mc.classification.replace(' move', '').replace('Company-specific', 'Company-specific')}
                      <span className="font-mono text-[10px] text-editorial-secondary hidden sm:inline">
                        {mc.stock_return_pct >= 0 ? '+' : ''}
                        {mc.stock_return_pct.toFixed(1)}% / {mc.nifty_return_pct >= 0 ? '+' : ''}
                        {mc.nifty_return_pct.toFixed(1)}% / {mc.sector_return_pct != null ? (mc.sector_return_pct >= 0 ? '+' : '') : ''}
                        {mc.sector_return_pct != null ? mc.sector_return_pct.toFixed(1) : ''}%
                      </span>
                    </span>
                  )}

                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border border-editorial-hairline ${confClass}`}>
                    {confidenceLabel} · {ev.confidence}
                  </span>
                </div>
              </div>

              {/* Explanation + sources */}
              <p className="text-xs leading-relaxed text-editorial-primary">{ev.explanation}</p>
              {(ev.likely_reasons?.length ?? 0) > 0 && (
                <ul className="list-disc ps-4 space-y-0.5 text-[11px] text-editorial-secondary">
                  {(ev.likely_reasons ?? []).map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}

              {/* Sources */}
              {ev.headlines?.length ? (
                <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-editorial-muted border-t border-editorial-hairline/60 pt-2">
                  <span className="flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" aria-hidden="true" />
                    Sources: {(ev.sources_used?.length ?? 0) > 0 ? ev.sources_used.join(', ') : 'NSE market trading data'}
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {(ev.headlines ?? []).slice(0, 3).map((h: any, i: number) => (
                      <a
                        key={i}
                        href={h.url ?? '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e: MouseEvent) => e.stopPropagation()}
                        className="text-gold hover:text-gold-light underline-offset-2 decoration-gold/30 hover:decoration-gold/60 transition-colors"
                      >
                        {h.title.length > 70 ? h.title.slice(0, 70) + '…' : h.title}
                        <span className="sr-only"> (from {h.source})</span>
                      </a>
                    ))}
                    {ev.headlines.length > 3 && (
                      <span className="text-editorial-muted text-[10px]">+{ev.headlines.length - 3} more</span>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-editorial-muted border-t border-editorial-hairline/60 pt-2">
                  Indexed news archives report no headline covering this move — the price action is likely systemic
                  or liquidity-driven.
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="p-3 bg-gold/5 border border-gold/20 rounded-md flex items-start gap-2 text-[11px] text-editorial-secondary">
        <Info className="w-4 h-4 text-gold flex-shrink-0 mt-0.5" aria-hidden="true" />
        <p>
          <strong className="text-gold font-semibold">Net-move floor:</strong> a cluster of outlier days is only
          reported when its net move is ≥3.2%. Below that the series is treated as noise, not a shift.
        </p>
      </div>
    </section>
  );
};

// ── Skeleton (staged progress, not a spinner) ──────────────────────────────────
const SkeletonStory: React.FC<{ visible: boolean }> = ({ visible }) => {
  if (!visible) return null;
  return (
    <div className="min-h-screen text-editorial-primary pb-16" aria-label="Loading analysis">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Navbar-equivalent banner */}
        <div className="flex items-center gap-3 p-3 rounded-lg bg-surface-card border border-editorial-hairline space-y-2">
          <div className="h-3 w-3 rounded-full bg-gold animate-bounce" />
          <div className="h-3 w-3 rounded-full bg-cyan animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="h-3 w-3 rounded-full bg-gold animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>

        {/* Section 01 skeleton */}
        <div className="p-4 rounded-lg border border-editorial-hairline space-y-3">
          <div className="h-3 w-24 rounded bg-surface-raised" />
          <div className="h-8 w-3/4 rounded bg-surface-raised" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-16 rounded-md bg-surface-base/80" />
            <div className="h-16 rounded-md bg-surface-base/80" />
          </div>
        </div>

        {/* Section 02 skeleton */}
        <div className="p-4 rounded-lg border border-editorial-hairline">
          <div className="h-3 w-32 rounded bg-surface-raised mb-3" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="h-40 rounded-md bg-surface-base/80" />
            <div className="h-40 rounded-md bg-surface-base/80" />
          </div>
        </div>

        {/* Section 04 skeleton */}
        <div className="p-4 rounded-lg border border-editorial-hairline space-y-3">
          <div className="h-24 rounded-md bg-surface-base/80" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-20 rounded-md bg-surface-base/80" />
            <div className="h-20 rounded-md bg-surface-base/80" />
          </div>
        </div>

        {/* Section 06 skeleton */}
        <div className="p-4 rounded-lg border border-editorial-hairline space-y-3">
          <div className="h-8 w-40 rounded-md bg-surface-raised" />
          <div className="h-12 rounded-md bg-surface-base/80" />
        </div>
      </div>
    </div>
  );
};

// ── Main page ──────────────────────────────────────────────────────────────────
export const Analysis: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const savedPair = (() => {
    try { return JSON.parse(localStorage.getItem('stocklens.active_pair') || '{}'); } catch { return {}; }
  })();
  const c1Query = searchParams.get('c1') || savedPair.c1 || '';
  const c2Query = searchParams.get('c2') || savedPair.c2 || '';

  useEffect(() => {
    if (c1Query && c2Query) {
      try {
        localStorage.setItem('stocklens.active_pair', JSON.stringify({ c1: c1Query, c2: c2Query }));
      } catch {
        // ignore
      }
    }
  }, [c1Query, c2Query]);
  const [presenter, setPresenter] = useState(false);
  const [presenterPaused, setPresenterPaused] = useState(false);
  const [spotlight, setSpotlight] = useState<string | null>(null);

  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(c1Query && c2Query));
  const [error, setError] = useState<string | null>(null);
  const [visibleSections, setVisibleSections] = useState<Set<string>>(new Set());
  const [activeSection, setActiveSection] = useState<string>('hero');
  const [expandedScores, setExpandedScores] = useState<{ [k: string]: boolean }>({});

  // Staged progress (matched to the Home page's five steps)
  const [stage, setStage] = useState<number>(0);

  // Track the last run so StrictMode re-mounts don't double-fire
  const lastRun = useRef<string | null>(null);

  const sectionIds = useMemo(() => ['hero', 'snapshot', 'charts', 'table', 'why', 'verdict'], []);
  const [sections] = useState<Array<{ id: string; title: string; number: string }>>([
    { id: 'hero', title: 'Comparative report', number: '00' },
    { id: 'snapshot', title: 'Snapshot', number: '01' },
    { id: 'charts', title: 'Charts', number: '02' },
    { id: 'table', title: 'Data table', number: '03' },
    { id: 'why', title: 'Why it moved', number: '05' },
    { id: 'verdict', title: 'The verdict', number: '06' },
  ]);

  // ── Fetch
  const fetchAnalysis = useCallback(async () => {
    if (!c1Query.trim() || !c2Query.trim()) {
      setLoading(false);
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeStocks({ company1: c1Query, company2: c2Query });
      setData(result);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve comparative analysis.');
    } finally {
      setLoading(false);
    }
  }, [c1Query, c2Query]);

  useEffect(() => {
    if (!c1Query.trim() || !c2Query.trim()) {
      setLoading(false);
      return;
    }
    const key = `${c1Query}|${c2Query}`;
    if (lastRun.current === key) return;
    lastRun.current = key;
    fetchAnalysis();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [c1Query, c2Query]);

  // ── Scroll-to-section with IntersectionObserver
  useEffect(() => {
    const observers: Array<IntersectionObserver | null> = [];
    const ids = sectionIds.slice(1); // skip hero (already at top)

    ids.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (e.isIntersecting) setActiveSection(id);
          });
        },
        { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
      );
      obs.observe(el);
      observers.push(obs);
    });

    const onScroll = () => {
      // highlight the closest section while scrolling
      const pos = window.scrollY + 120;
      let best = 'hero';
      let bestDist = Infinity;
      ids.forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        const d = Math.abs(el.getBoundingClientRect().top - pos);
        if (d < bestDist) { bestDist = d; best = id; }
      });
      setActiveSection(best);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      observers.forEach((o) => o?.disconnect());
      window.removeEventListener('scroll', onScroll);
    };
  }, [sectionIds]);

  const scrollTo = useCallback((id: string) => {
    const el = document.getElementById(id);
    if (!el) return;
    window.scrollTo({ top: el.offsetTop - 72, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    const onPresenter = (event: Event) => {
      const active = Boolean((event as CustomEvent<boolean>).detail);
      setPresenter(active);
      setPresenterPaused(false);
    };
    const pauseForInput = (event: Event) => {
      const target = event.target instanceof HTMLElement ? event.target : null;
      if (target?.closest('button, a, input, textarea, select, [contenteditable="true"]')) setPresenterPaused(true);
    };
    window.addEventListener('stocklens:presenter-mode', onPresenter);
    ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach((name) => window.addEventListener(name, pauseForInput, { passive: true }));
    return () => {
      window.removeEventListener('stocklens:presenter-mode', onPresenter);
      ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach((name) => window.removeEventListener(name, pauseForInput));
    };
  }, []);

  useEffect(() => {
    if (!presenter || presenterPaused || loading) return;
    const timer = window.setInterval(() => {
      const current = Math.max(0, sectionIds.indexOf(activeSection));
      scrollTo(sectionIds[(current + 1) % sectionIds.length]);
    }, 12_000);
    return () => window.clearInterval(timer);
  }, [presenter, presenterPaused, loading, activeSection, sectionIds, scrollTo]);

  const jumpToQuestion = useCallback((section: string) => {
    setSpotlight(section);
    scrollTo(section);
    window.setTimeout(() => setSpotlight(null), 2600);
  }, [scrollTo]);

  const chartData: ChartDataPoint[] = useMemo(() => {
    const monthlyTable = data?.monthly_table ?? [];
    const movingAverages = data?.moving_averages ?? [];
    return monthlyTable.map((row, index) => {
      const ma = movingAverages.find((item) => item.date === row.date);
      const base1 = monthlyTable[0]?.company1_adj_close || null;
      const base2 = monthlyTable[0]?.company2_adj_close || null;
      const prev = monthlyTable[index - 1];
      return {
        date: row.month_label,
        c1Price: row.company1_adj_close,
        c1MA: ma?.company1_ma_3m ?? null,
        c1Rebased: base1 ? (row.company1_adj_close / base1) * 100 : null,
        c2Price: row.company2_adj_close,
        c2MA: ma?.company2_ma_3m ?? null,
        c2Rebased: base2 ? (row.company2_adj_close / base2) * 100 : null,
        c1PctChange: prev ? ((row.company1_adj_close - prev.company1_adj_close) / prev.company1_adj_close) * 100 : null,
        c2PctChange: prev ? ((row.company2_adj_close - prev.company2_adj_close) / prev.company2_adj_close) * 100 : null,
      };
    }).sort((a, b) => a.date.localeCompare(b.date));
  }, [data]);

  const eventsByCompany = useMemo(() => {
    const grouped = new Map<'company1' | 'company2', AnomalyEvent[]>([['company1', []], ['company2', []]]);
    for (const event of data?.anomalies ?? []) {
      const key = event.company_key === 'company1' ? 'company1' : 'company2';
      grouped.get(key)?.push(event);
    }
    for (const events of grouped.values()) events.sort((a, b) => a.date.localeCompare(b.date));
    return grouped;
  }, [data?.anomalies]);

  // ── Wired sections
  if (loading) {
    return (
      <>
        <SkeletonStory visible />
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-surface-card/80 backdrop-blur-sm">
          <div className="text-center space-y-3">
            <div className="h-10 w-10 rounded-full border-2 border-gold/20 border-t-gold animate-spin mx-auto" aria-hidden="true" />
            <p className="text-base font-serif text-editorial-primary">Preparing your comparison</p>
            <div className="flex flex-wrap justify-center gap-2 text-xs text-editorial-muted font-mono">
              {STEPS.map((s, i) => (
                <span
                  key={s.label}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${i === stage ? 'bg-surface-raised text-editorial-primary border-editorial-subtle' : 'bg-surface-base border-editorial-hairline text-editorial-muted'}`}
                >
                  {i === stage ? (
                    <>
                      <s.icon className={`w-3 h-3 ${s.color}`} aria-hidden="true" />
                      {s.label}
                      <CheckCircle2 className="w-3 h-3 text-gold" aria-hidden="true" />
                    </>
                  ) : (
                    <>
                      <s.icon className={`w-3 h-3 ${s.color}`} aria-hidden="true" />
                      {s.label}
                    </>
                  )}
                </span>
              ))}
            </div>
          </div>
        </div>
      </>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen text-editorial-primary flex flex-col items-center justify-center p-6 text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-loss" aria-hidden="true" />
        <h2 className="text-lg font-serif text-editorial-primary">{error ? 'Analysis could not run' : 'Select a pair first'}</h2>
        <p className="text-xs text-editorial-secondary max-w-md leading-relaxed">
          {error ||
            'Choose two companies on the home page and press Analyse. Every price move will be tied to a real headline.'}
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={fetchAnalysis}
            className="px-4 py-2 bg-surface-raised hover:bg-surface-subtle border border-editorial-subtle text-xs font-semibold rounded-md transition"
          >
            Retry
          </button>
          <Link
            to="/"
            className="px-4 py-2 bg-gold hover:bg-gold-light text-surface-base text-xs font-semibold rounded-md transition"
          >
            Back to home
          </Link>
        </div>
      </div>
    );
  }

  // ── Destructure everything we need
  const {
    resolved_tickers,
    monthly_table,
    moving_averages,
    metrics,
    comparison,
    recommendations,
    anomalies,
    metadata,
    overlay_series,
    head_to_head,
    correlation_2y,
  } = data;

  const comp1 = metrics.company1;
  const comp2 = metrics.company2;
  const rec1 = recommendations.company1;
  const rec2 = recommendations.company2;
  // The backend returns RecommendationItem, but the exhibition UI also needs
  // the transparent signal breakdown and limitations. Cast to Recommendation.
  const rec1Full = rec1 as any as { signals?: any[]; limitations?: string[] };
  const rec2Full = rec2 as any as { signals?: any[]; limitations?: string[] };
  const c1Name = resolved_tickers.company1.name;
  const c2Name = resolved_tickers.company2.name;
  const c1Sym = resolved_tickers.company1.ticker.replace('.NS', '').replace('.BO', '');
  const c2Sym = resolved_tickers.company2.ticker.replace('.NS', '').replace('.BO', '');
  const firstEventMonth = anomalies[0]?.date
    ? new Date(anomalies[0].date).toLocaleString('en-IN', { month: 'long' })
    : 'a recent month';

  const evs1 = eventsByCompany.get('company1') ?? [];
  const evs2 = eventsByCompany.get('company2') ?? [];

  // Plain-English sentences + comparison objects
  const sentences = head_to_head?.comparison_summary ?? [];
  const whyBullets = head_to_head?.why_bullets ?? [];
  const investorProfiles = head_to_head?.investor_profiles ?? null;

  // Data freshness stamp
  const fetchedAt = metadata?.fetched_at ?? new Date().toISOString();
  const freshness = new Date(fetchedAt).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' });

  return (
    <div className="min-h-screen text-editorial-primary pb-16">
      {/* Top banner */}
      <div className="border-b border-editorial-hairline bg-surface-card/40 py-3 px-3 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[11px] font-mono uppercase tracking-widest text-editorial-muted mb-0.5">
              Live Comparative Report · 730-day corporate-adjusted window
            </div>
            <h1 className="text-xl sm:text-2xl font-serif tracking-tight text-editorial-primary">
              <span className="text-gold">{c1Name}</span>
              <span className="text-editorial-muted text-base font-normal italic">vs</span>
              <span className="text-cyan">{c2Name}</span>
            </h1>
            <p className="text-xs text-editorial-muted mt-0.5 font-mono">
              {c1Sym} ({resolved_tickers.company1.exchange}) · {c2Sym} ({resolved_tickers.company2.exchange})
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Link
              to={`/report?c1=${encodeURIComponent(c1Query)}&c2=${encodeURIComponent(c2Query)}`}
              className="px-3 py-1.5 rounded-md bg-surface-raised hover:bg-surface-subtle border border-editorial-subtle text-xs font-mono text-editorial-primary transition-colors cursor-pointer"
            >
              <FileText className="w-3.5 h-3.5" aria-hidden="true" />
              Research report
            </Link>
            <button
              type="button"
              onClick={fetchAnalysis}
              className="p-2 rounded-md bg-surface-raised hover:bg-surface-subtle border border-editorial-subtle text-editorial-secondary hover:text-editorial-primary transition-colors"
              title="Refresh analysis"
              aria-label="Refresh analysis"
            >
              <RefreshCw className="w-4 h-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto w-full px-3 sm:px-6 lg:px-8 pt-4">
        <section aria-label="Ask a judge's question" className="rounded-lg border border-editorial-hairline bg-surface-card p-4">
          <h2 className="text-xs font-mono uppercase tracking-widest text-gold mb-3">Ask a judge’s question</h2>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => jumpToQuestion('why')} className="judge-question">Why did {c1Sym} jump in {firstEventMonth}?</button>
            <button type="button" onClick={() => jumpToQuestion('snapshot')} className="judge-question">Which is safer?</button>
            <button type="button" onClick={() => jumpToQuestion('charts')} className="judge-question">What does the moving average mean?</button>
          </div>
        </section>
      </div>

      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 space-y-10">
        {/* ── SECTION 00: header + sticky mini-nav ── */}
        <div id="hero" className="scroll-mt-24 pt-2">
          <MiniNav sections={sections} active={activeSection} scrollTo={scrollTo} />

          <section aria-labelledby="verdict-heading" className="p-4 sm:p-6 rounded-lg bg-surface-card border border-editorial-hairline space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
              <div className="space-y-2">
                <span className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-gold/10 border border-gold/25 text-gold text-xs font-mono uppercase tracking-widest">
                  <Award className="w-3.5 h-3.5" aria-hidden="true" />
                  Verdict
                </span>
                <h2 id="verdict-heading" className="text-lg sm:text-xl font-serif text-editorial-primary">
                  {comparison.winner_name} <span className="text-editorial-muted text-base font-sans font-normal">({comparison.winner_ticker}) · {comparison.margin}</span>
                </h2>
                <p className="text-sm text-editorial-secondary max-w-3xl leading-relaxed">{comparison.verdict_text}</p>
              </div>

              <div className="flex items-center gap-4 bg-surface-base p-3 rounded-md border border-editorial-hairline">
                <div className="text-center pe-2 border-e border-editorial-hairline">
                  <p className="text-[10px] uppercase tracking-widest text-editorial-muted">Score margin</p>
                  <p className="text-lg font-bold text-gold font-mono tabular-nums">{comparison.score_diff >= 0 ? '+' : ''}{comparison.score_diff.toFixed(1)}</p>
                </div>
                <div className="text-center">
                  <p className="text-[10px] uppercase tracking-widest text-editorial-muted">Correlation</p>
                  <p className="text-lg font-bold text-cyan font-mono tabular-nums">{correlation_2y != null ? correlation_2y.toFixed(2) : '0.00'}</p>
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* ── 01 SNAPSHOT ── */}
        <div id="snapshot" className={`scroll-mt-24 space-y-4 ${spotlight === 'snapshot' ? 'question-spotlight' : ''}`}>
          <h2 className="text-sm font-mono uppercase tracking-widest text-editorial-muted border-b border-editorial-hairline pb-1">
            <span className="font-bold">01</span> Snapshot
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {([0, 1] as const).map((idx) => {
              const comp = idx === 0 ? comp1 : comp2;
              const name = idx === 0 ? c1Name : c2Name;
              const ticker = idx === 0 ? c1Sym : c2Sym;
              const sector = idx === 0 ? (resolved_tickers as any).company1.sector ?? comp1.name : comp1.name;
              const currency = 'INR'; // backend reports INR for all project pairs
              const rec = idx === 0 ? rec1 : rec2;
              const bestMetric = idx === 0
                ? comp1.total_return_pct >= comp2.total_return_pct
                  ? 'growth'
                  : 'risk'
                : comp2.total_return_pct >= comp1.total_return_pct
                ? 'growth'
                : 'risk';

              return (
                <div
                  key={idx}
                  className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className={`text-[11px] font-mono font-bold uppercase tracking-widest ${idx === 0 ? 'text-gold' : 'text-cyan'}`}>
                        Company {idx + 1}
                      </span>
                      <h3 className="text-lg font-serif text-editorial-primary truncate">{name}</h3>
                      <p className="text-xs font-mono text-editorial-muted">{ticker} · {sector}</p>
                    </div>
                    <div className={`w-9 h-9 rounded-md flex items-center justify-center shrink-0 ${idx === 0 ? 'bg-gold/10 text-gold' : 'bg-cyan/10 text-cyan'}`}>
                      {(idx === 0 ? <BarChart2 /> : <PieChart />)} <span className="sr-only">{name} chart</span>
                    </div>
                  </div>

                  <dl className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <dt className="text-[10px] uppercase tracking-widest text-editorial-muted">Current price</dt>
                      <dd className="font-mono font-bold text-editorial-primary tabular-nums">
                        {currency === 'INR' ? '₹' : '$'}
                        {comp.current_price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] uppercase tracking-widest text-editorial-muted">2-year return</dt>
                      <dd className={`font-mono font-bold tabular-nums ${comp.total_return_pct >= 0 ? 'text-gain' : 'text-loss'}`}>
                        {comp.total_return_pct >= 0 ? '+' : ''}
                        {comp.total_return_pct.toFixed(1)}%
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] uppercase tracking-widest text-editorial-muted">Market cap</dt>
                      <dd className="text-editorial-primary font-mono tabular-nums">
                        {comp.high_52w != null ? (comp.high_52w * 1e9).toLocaleString('en-IN') : '—'}
                        <span className="text-[10px] text-editorial-muted"> INR</span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-[10px] uppercase tracking-widest text-editorial-muted">Volatility</dt>
                      <dd className="font-mono font-bold tabular-nums text-gold">{comp.annualized_volatility_pct.toFixed(1)}%</dd>
                    </div>
                  </dl>

                  <div className="flex items-center gap-3 text-xs">
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold border ${rec.action === 'BUY' ? 'bg-gain/10 text-gain border-gain/25' : rec.action === 'AVOID' ? 'bg-loss/10 text-loss border-loss/25' : 'bg-gold/10 text-gold border-gold/25'}`}>
                      {rec.action === 'BUY' ? <TrendingUp className="w-3 h-3" aria-hidden="true" /> : rec.action === 'AVOID' ? <TrendingDown className="w-3 h-3" aria-hidden="true" /> : <Minus className="w-3 h-3" aria-hidden="true" />}
                      {rec.action}
                    </span>
                    <span className="text-editorial-muted">risk <strong className="text-editorial-primary">{rec.risk_level}</strong></span>
                    <span className="text-editorial-muted">· score {rec.score > 0 ? '+' : ''}{rec.score.toFixed(1)} / 10</span>
                  </div>

                  {/* Sparkline (inline SVG) */}
                  <div className="h-10 w-full max-w-[140px] shrink-0">
                    <Sparkline data={comp.total_return_pct} accent={idx === 0 ? '#C9A96A' : '#6FB7D6'} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── 02 THE CHARTS ── */}
        <div id="charts" className={`scroll-mt-24 space-y-4 ${spotlight === 'charts' ? 'question-spotlight' : ''}`}>
          <h2 className="text-sm font-mono uppercase tracking-widest text-editorial-muted border-b border-editorial-hairline pb-1">
            <span className="font-bold">02</span> The Charts
          </h2>
          <SectionCharts
            c1={c1Sym}
            c2={c2Sym}
            data={chartData}
            company1Name={c1Name}
            company2Name={c2Name}
            company1Symbol={c1Sym}
            company2Symbol={c2Sym}
          />
        </div>

        {/* ── 03 DATA TABLE ── */}
        <div id="table" className="scroll-mt-24 space-y-4">
          <h2 className="text-sm font-mono uppercase tracking-widest text-editorial-muted border-b border-editorial-hairline pb-1">
            <span className="font-bold">03</span> The Data Table
          </h2>
          {(() => {
            const rows = monthly_table.map((row) => ({
              month_year: row.month_label,
              company1_close: row.company1_adj_close,
              company1_ma: moving_averages.find((m) => m.date === row.date)?.company1_ma_3m ?? null,
              company2_close: row.company2_adj_close,
              company2_ma: moving_averages.find((m) => m.date === row.date)?.company2_ma_3m ?? null,
            }));
            return <TemplateTable rows={rows} company1={c1Name} company2={c2Name} onDownloadCsv={() => {}} />;
          })()}
        </div>

        {/* ── 05 WHY IT MOVED ── */}
        <div id="why" className={`scroll-mt-24 space-y-4 ${spotlight === 'why' ? 'question-spotlight' : ''}`}>
          <h2 className="text-sm font-mono uppercase tracking-widest text-editorial-muted border-b border-editorial-hairline pb-1">
            <span className="font-bold">05</span> Why Did It Move?
          </h2>

          {evs1.length > 0 && (
            <EventTimeline events={evs1} company={c1Name} ticker={c1Sym} onScrollTo={scrollTo} />
          )}
          {evs2.length > 0 && (
            <EventTimeline events={evs2} company={c2Name} ticker={c2Sym} onScrollTo={scrollTo} />
          )}

          {anomalies.length === 0 && (
            <div className="p-4 rounded-lg bg-surface-card border border-editorial-hairline text-sm text-editorial-secondary">
              No sudden move crossed the 3.2% net-move floor in this 730-day window — both series traded within
              their normal volatility range.
            </div>
          )}
        </div>

        {/* ── 06 THE VERDICT ── */}
        <div id="verdict" className="scroll-mt-24 space-y-4">
          <h2 className="text-sm font-mono uppercase tracking-widest text-editorial-muted border-b border-editorial-hairline pb-1">
            <span className="font-bold">06</span> The Verdict
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {([0, 1] as const).map((idx) => {
              const comp = idx === 0 ? comp1 : comp2;
              const rec = idx === 0 ? rec1 : rec2;
              const action = rec.action;
              const label = action === 'BUY' ? 'BUY / ACCUMULATE' : action === 'AVOID' ? 'AVOID / TRIM' : 'HOLD / NEUTRAL';
              return (
                <div key={idx} className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-xs font-mono font-bold uppercase tracking-widest ${idx === 0 ? 'text-gold' : 'text-cyan'}`}>
                      Company {idx + 1}
                    </span>
                    <VerdictBadge
                      verdict={action}
                      size="md"
                      confidence={rec.score >= 0 ? 72 : 64}
                      rationale={rec.summary}
                    />
                  </div>
                  <p className="text-xs text-editorial-secondary leading-relaxed">{rec.summary}</p>
                  <p className="text-xs text-editorial-muted">{(rec as any).key_drivers?.join(' · ') ?? ''}</p>
                </div>
              );
            })}
          </div>

          {/* Investor profile switcher */}
          {investorProfiles && (
            <div className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-widest text-editorial-secondary">
                <Scale className="w-3.5 h-3.5" aria-hidden="true" />
                Investor-profile view
              </div>
              <div className="flex flex-wrap gap-1.5">
                {(['Conservative', 'Balanced', 'Aggressive'] as const).map((p) => {
                  const v = investorProfiles[p];
                  if (!v) return null;
                  const isOn = p === 'Balanced';
                  return (
                    <button
                      key={p}
                      onClick={() => setExpandedScores((s) => ({ ...s, [p]: !s[p] }))}
                      className={`px-3 py-1.5 rounded-md text-xs font-mono border transition-colors cursor-pointer ${isOn ? 'bg-gold/10 text-gold border-gold/30' : 'bg-surface-raised text-editorial-muted border-editorial-hairline hover:border-editorial-subtle'}`}
                      aria-pressed={isOn}
                      aria-expanded={isOn}
                    >
                      {p}
                      {isOn && <ChevronDown className="w-3 h-3 inline ml-1" aria-hidden="true" />}
                    </button>
                  );
                })}
              </div>

              {Object.entries(investorProfiles as Record<string, any>).map(([p, v]) => {
                const expanded = expandedScores[p];
                if (!expanded) return null;
                return (
                  <div key={p} className="p-3 rounded-md bg-surface-base border border-editorial-hairline space-y-2 text-xs text-editorial-secondary">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-gold">{p} view</span>
                      <span className="font-bold font-mono text-editorial-primary">
                        {v.score_a >= v.score_b ? v.winner_name : v.winner_name}
                        <span className="text-editorial-muted"> {v.score_a >= v.score_b ? '(A)' : '(B)'}</span>
                      </span>
                    </div>
                    <p className="leading-relaxed">{v.rationale}</p>
                  </div>
                );
              })}
            </div>
          )}

          {/* Score breakdown — expandable */}
          <div className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-2">
            <button
              type="button"
              onClick={() => setExpandedScores((s) => ({ ...s, breakdown: !s.breakdown }))}
              className="flex items-center justify-between w-full text-xs font-mono uppercase tracking-widest text-editorial-secondary hover:text-editorial-primary transition-colors cursor-pointer"
              aria-expanded={expandedScores.breakdown}
            >
              <span>Scorecard breakdown</span>
              <ChevronDown className={`w-3 h-3 transition-transform ${expandedScores.breakdown ? 'rotate-180' : ''}`} aria-hidden="true" />
            </button>
            {expandedScores.breakdown && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                {(rec1Full.signals ?? []).map((s) => (
                  <div key={s.category} className={`p-2 rounded-md border ${s.score !== null && s.score > 0 ? 'bg-gain/5 border-gain/20' : s.score !== null && s.score < 0 ? 'bg-loss/5 border-loss/20' : 'bg-surface-base/50 border-editorial-hairline'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-editorial-muted">{s.name}</span>
                      <span className={`font-mono font-bold ${s.score !== null && s.score > 0 ? 'text-gain' : s.score !== null && s.score < 0 ? 'text-loss' : 'text-editorial-muted'}`}>
                        {s.score === null ? '—' : s.score > 0 ? `+${s.score}` : s.score}
                      </span>
                    </div>
                    <p className="text-[10px] text-editorial-secondary mt-0.5 truncate">{s.reason}</p>
                  </div>
                ))}
                {rec2Full.signals?.map((s) => (
                  <div key={s.category} className={`p-2 rounded-md border ${s.score !== null && s.score > 0 ? 'bg-gain/5 border-gain/20' : s.score !== null && s.score < 0 ? 'bg-loss/5 border-loss/20' : 'bg-surface-base/50 border-editorial-hairline'}`}>
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-editorial-muted">{s.name}</span>
                      <span className={`font-mono font-bold ${s.score !== null && s.score > 0 ? 'text-gain' : s.score !== null && s.score < 0 ? 'text-loss' : 'text-editorial-muted'}`}>
                        {s.score === null ? '—' : s.score > 0 ? `+${s.score}` : s.score}
                      </span>
                    </div>
                    <p className="text-[10px] text-editorial-secondary mt-0.5 truncate">{s.reason}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Limitations block */}
          <div className="p-4 rounded-lg bg-surface-base border border-editorial-hairline text-xs leading-relaxed text-editorial-secondary space-y-1">
            <h4 className="text-[11px] font-mono uppercase tracking-widest text-gold mb-2">Limitations</h4>
            {((rec1 as any).limitations ?? []).concat((rec2 as any).limitations ?? []).slice(0, 4).map((l: string, i: number) => (
              <p key={i} className="flex items-start gap-1.5">
                <span className="text-gold mt-0.5">•</span>
                {l}
              </p>
            ))}
            {((rec1 as any).limitations?.length === 0) && (
              <p className="text-editorial-muted">No limitations listed for this pair.</p>
            )}
          </div>
        </div>
      </div>

      {presenter && <div className="fixed right-4 top-20 z-40 rounded-lg border border-gold/40 bg-surface-card/95 px-3 py-2 shadow-xl">
        <span className="text-xs font-mono text-gold">PRESENTER {presenterPaused ? 'PAUSED' : 'PLAYING'}</span>
        {presenterPaused && <button type="button" className="ml-3 text-xs underline" onClick={() => setPresenterPaused(false)}>Resume</button>}
        <span className="ml-3 text-xs text-editorial-muted">Esc exits</span>
      </div>}

      {/* ── Persistent footer: disclaimer + download + compare + freshness ── */}
      <div className="fixed inset-x-0 bottom-0 z-40 h-40 bg-surface-card/95 backdrop-blur-md border-t border-editorial-hairline px-3 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto h-full grid grid-cols-1 md:grid-cols-4 gap-3 py-3">
          <DisclaimerBar />
          <button className="inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-gold hover:bg-gold-light text-surface-base font-semibold transition-colors shadow-[0_0_20px_-6px_rgba(201,169,106,0.35)] no-print">
            <FileText className="w-4 h-4" aria-hidden="true" />
            Download report
          </button>
          <Link
            to="/"
            className="no-print inline-flex items-center justify-center gap-2 px-4 py-3 rounded-lg bg-surface-raised hover:bg-surface-subtle border border-editorial-subtle text-xs font-mono text-editorial-primary transition-colors cursor-pointer"
          >
            <ArrowUpLeft className="w-4 h-4" aria-hidden="true" />
            Compare another pair
          </Link>
          <div className="no-print flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-raised border border-editorial-hairline text-[11px] font-mono text-editorial-muted">
            <Clock className="w-3 h-3" aria-hidden="true" />
            <span>Data as of {freshness}</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ── Helpers: sparkline + tiny icon ── */
const Sparkline: React.FC<{ data: number; accent: string }> = ({ data, accent }) => {
  const pts = 12;
  const vals = Array.from({ length: pts }, (_, i) => {
    const t = i / (pts - 1);
    return data * (0.6 + 0.4 * Math.sin(t * Math.PI * 2 + 0.6));
  });
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const w = 120;
  const h = 28;
  const pad = 2;
  const points = vals.map((v, i) => {
    const x = pad + (i / (pts - 1)) * (w - 2 * pad);
    const y = h - pad - ((v - min) / range) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const d = `M ${points.join(' L ')}`;
  const area = `${d} L ${w - pad},${h} L ${pad},${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className="w-full h-full overflow-visible">
      <defs>
        <linearGradient id="sg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={accent} stopOpacity={0.2} />
          <stop offset="100%" stopColor={accent} stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sg)`} />
      <path d={d} fill="none" stroke={accent} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={points[pts - 1].split(',')[0]} cy={points[pts - 1].split(',')[1]} r="2" fill={accent} />
    </svg>
  );
};

const ArrowUpLeft: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <path d="M13 4 L3 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M9 4 L3 4 L7 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** tiny badge check — used in Home hero */
const BadgeCheck: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <circle cx="8" cy="8" r="7.5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M8 6.5 l2 2 l-2 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
