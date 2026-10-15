import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  ArrowRight,
  BarChart3,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Globe,
  TrendingUp,
  LineChart,
  Search,
  ShieldAlert,
  Sparkles,
  X,
  RefreshCw,
  Info,
  AlertTriangle,
  Award,
} from 'lucide-react';
import { checkHealth, API_BASE_URL, FALLBACK_STOCKS } from '../lib/api';
import { HealthResponse } from '../lib/types';
// Popular comparisons
const POPULAR_COMPARISONS: Array<[string, string, string]> = [
  ['Morgan Stanley', 'JPMorgan Chase', 'Global Investment Banks'],
  ['Apple', 'Microsoft', 'Mega-cap Tech'],
  ['Zomato', 'Swiggy', 'Consumer Tech'],
  ['State Bank of India', 'HDFC Bank', 'Banking'],
  ['TCS', 'Infosys', 'IT Services'],
];

// Guided discovery steps shown while the backend computes
const STEPS = [
  { icon: Globe, label: 'Fetching 2 years of prices', color: 'text-pepper' },
  { icon: LineChart, label: 'Calculating moving averages', color: 'text-editorial-secondary' },
  { icon: Activity, label: 'Scanning for sudden moves', color: 'text-pepper' },
  { icon: Search, label: 'Reading the news', color: 'text-editorial-secondary' },
  { icon: Award, label: 'Preparing the verdict', color: 'text-pepper' },
];

/**
 * Friendly validation state machine for the two input fields.
 * - empty field            -> 'Please enter a company.'
 * - same company twice      -> 'Choose two different companies.'
 * - unknown company         -> '“<q>” could not be resolved to a listed symbol.'
 * - resolution succeeded    -> no error (resolved ticker shown as a chip)
 */
interface ValidationState {
  field: null | 1 | 2;      // which field is invalid
  message: string;          // friendly hint to show under the fields
}

/** Resolve a single query live against the backend or offline catalog so we can surface a chip + sector. */
async function resolveQuery(q: string): Promise<{ ticker: string; name: string; sector: string } | null> {
  const cleanQ = q.trim().toLowerCase();
  try {
    const res = await fetch(`${API_BASE_URL}/api/resolve?q=${encodeURIComponent(q.trim())}`);
    if (res.ok) {
      const json = await res.json();
      const match = json.match;
      if (match && !json.is_ambiguous) {
        return { ticker: match.ticker, name: match.name, sector: match.sector ?? 'Diversified' };
      }
    }
  } catch {
    // Backend offline / not reached
  }

  // Resilient offline fallback
  const found = FALLBACK_STOCKS.find(
    (s) =>
      s.name.toLowerCase() === cleanQ ||
      s.ticker.toLowerCase() === cleanQ ||
      s.name.toLowerCase().includes(cleanQ) ||
      s.ticker.toLowerCase().includes(cleanQ)
  );
  if (found) {
    return { ticker: found.ticker, name: found.name, sector: found.sector };
  }
  return null;
}

const DEFAULT_POPULAR_1 = [
  { name: 'Morgan Stanley', ticker: 'MS', display: 'Morgan Stanley (MS)', sector: 'Financial Services' },
  { name: 'State Bank of India', ticker: 'SBIN.NS', display: 'State Bank of India (SBIN.NS)', sector: 'Financial Services' },
  { name: 'Zomato (Eternal)', ticker: 'ETERNAL.NS', display: 'Zomato (ETERNAL.NS)', sector: 'Consumer Cyclical' },
  { name: 'Reliance Industries', ticker: 'RELIANCE.NS', display: 'Reliance Industries (RELIANCE.NS)', sector: 'Energy' },
  { name: 'Hindustan Aeronautics', ticker: 'HAL.NS', display: 'Hindustan Aeronautics (HAL.NS)', sector: 'Industrials' },
  { name: 'Apple Inc.', ticker: 'AAPL', display: 'Apple Inc. (AAPL)', sector: 'Technology' },
];

const DEFAULT_POPULAR_2 = [
  { name: 'JPMorgan Chase & Co.', ticker: 'JPM', display: 'JPMorgan Chase (JPM)', sector: 'Financial Services' },
  { name: 'HDFC Bank', ticker: 'HDFCBANK.NS', display: 'HDFC Bank (HDFCBANK.NS)', sector: 'Financial Services' },
  { name: 'Swiggy Limited', ticker: 'SWIGGY.NS', display: 'Swiggy (SWIGGY.NS)', sector: 'Consumer Cyclical' },
  { name: 'Mazagon Dock Shipbuilders', ticker: 'MAZDOCK.NS', display: 'Mazagon Dock (MAZDOCK.NS)', sector: 'Industrials' },
  { name: 'Tata Consultancy Services', ticker: 'TCS.NS', display: 'TCS (TCS.NS)', sector: 'Technology' },
  { name: 'Microsoft Corporation', ticker: 'MSFT', display: 'Microsoft (MSFT)', sector: 'Technology' },
];

/**
 * An input field that:
 *  - searches /api/resolve on each keystroke,
 *  - displays full company match with ticker and alternatives in a dropdown,
 *  - tracks validation state so the "Analyse" button surfaces friendly messages.
 */
const CompanyInput: React.FC<{
  label: string;
  value: string;
  onChange: (v: string) => void;
  accent: 'gold' | 'cyan';
  accentNumber: 1 | 2;
  placeholder: string;
  autoComplete: string;
  validation: ValidationState;
}> = ({ label, value, onChange, accent, accentNumber, placeholder, autoComplete, validation }) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<Array<{ name: string; ticker: string; display: string; sector: string; isTop?: boolean }>>([]);
  const [isResolved, setIsResolved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resolvedName, setResolvedName] = useState<string | null>(null);
  const [resolvedSector, setResolvedSector] = useState<string | null>(null);
  const [highlight, setHighlight] = useState(0);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const listRef = React.useRef<HTMLUListElement>(null);

  // Keep internal query in sync whenever the parent value changes
  useEffect(() => { setQuery(value); }, [value]);

  const runResolve = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setResults(accentNumber === 1 ? DEFAULT_POPULAR_1 : DEFAULT_POPULAR_2);
      setIsResolved(false);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/resolve?q=${encodeURIComponent(q)}`);
      if (res.ok) {
        const json = await res.json();
        const items: Array<{ name: string; ticker: string; display: string; sector: string; isTop?: boolean }> = [];
        if (json.match) {
          items.push({
            name: json.match.name,
            ticker: json.match.ticker,
            display: `${json.match.name} (${json.match.ticker})`,
            sector: json.match.sector ?? 'Diversified',
            isTop: true,
          });
          setIsResolved(true);
          setResolvedName(json.match.name);
          setResolvedSector(json.match.sector ?? 'Diversified');
        }
        if (json.alternatives && json.alternatives.length > 0) {
          for (const a of json.alternatives) {
            if (!items.some((it) => it.ticker === a.ticker)) {
              items.push({
                name: a.name,
                ticker: a.ticker,
                display: `${a.name} (${a.ticker})`,
                sector: a.sector ?? 'Diversified',
                isTop: false,
              });
            }
          }
        }
        setResults(items);
        return;
      }
    } catch {
      // Backend not reached, fall through to offline matcher
    }

    // Offline matcher for typing suggestions & resolution
    const clean = q.toLowerCase();
    const matched = FALLBACK_STOCKS.filter(
      (s) =>
        s.name.toLowerCase().includes(clean) ||
        s.ticker.toLowerCase().includes(clean)
    );
    if (matched.length > 0) {
      const items = matched.map((m, idx) => ({
        name: m.name,
        ticker: m.ticker,
        display: m.display,
        sector: m.sector,
        isTop: idx === 0,
      }));
      setResults(items);
      setIsResolved(true);
      setResolvedName(items[0].name);
      setResolvedSector(items[0].sector);
    } else {
      setResults([]);
      setIsResolved(false);
    }
  }, [query, accentNumber]);

  useEffect(() => { runResolve(); }, [runResolve]);

  // Close the dropdown when clicking outside
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (listRef.current && !listRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const pick = (t: string, n: string, s: string) => {
    setQuery(n);
    onChange(n);
    setIsResolved(true);
    setResolvedName(n);
    setResolvedSector(s);
    setOpen(false);
    setResults([]);
  };

  const clear = () => {
    setQuery('');
    onChange('');
    setIsResolved(false);
    setResults([]);
    setOpen(false);
    inputRef.current?.focus();
  };

  return (
    <div className={`w-full max-w-2xl relative ${validation.field === accentNumber ? 'border-editorial-subtle' : ''}`}>
      <div className="flex items-center justify-between mb-1.5 px-0.5">
        <label htmlFor={`company-${accentNumber}`} className="text-xs uppercase tracking-wider font-semibold text-editorial-secondary flex items-center gap-1.5">
          <span
            className={`w-4 h-4 rounded-full text-[10px] font-mono font-bold flex items-center justify-center border ${accent === 'gold' ? 'border-gold/40 text-gold bg-gold/10' : 'border-cyan/40 text-cyan bg-cyan/10'}`}
          >
            {accentNumber}
          </span>
          {label}
        </label>
        {isResolved && resolvedName && (
          <span className="text-[11px] font-mono text-editorial-muted flex items-center gap-1.5 truncate max-w-[240px]">
            <Building2 className="w-3 h-3 text-editorial-muted shrink-0" aria-hidden="true" />
            <span className="font-semibold text-editorial-primary truncate">{resolvedName}</span>
            <span className="px-1.5 py-0.2 rounded bg-surface-raised text-[10px] font-mono border border-editorial-hairline shrink-0">{resolvedSector}</span>
          </span>
        )}
      </div>

      <div className="relative flex items-center rounded-md bg-surface-card border border-editorial-hairline transition-all duration-200 shadow-hairline focus-within:ring-2 focus-within:ring-offset-2 focus-within:ring-offset-base">
        <div className="pl-3.5 pr-1 flex items-center pointer-events-none text-editorial-muted">
          <Search className="w-4 h-4" aria-hidden="true" />
        </div>
        <input
          ref={inputRef}
          id={`company-${accentNumber}`}
          type="text"
          value={query}
          autoComplete={autoComplete}
          onFocus={() => {
            setOpen(true);
            if (!query.trim()) {
              setResults(accentNumber === 1 ? DEFAULT_POPULAR_1 : DEFAULT_POPULAR_2);
            }
          }}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange(e.target.value);
            setOpen(true);
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') { e.preventDefault(); setOpen(true); }
            else if (e.key === 'ArrowDown' && open) setHighlight(0);
            else if (e.key === 'Escape') setOpen(false);
          }}
          placeholder={placeholder}
          className="w-full py-2.5 bg-transparent text-editorial-primary placeholder:text-editorial-muted text-sm font-sans focus:outline-none"
        />
        <div className="pr-2 flex items-center gap-1.5">
          {query && (
            <button
              type="button"
              onClick={clear}
              className="p-1 rounded-md text-editorial-muted hover:text-editorial-primary hover:bg-surface-raised transition-colors cursor-pointer"
              aria-label="Clear input"
            >
              <X className="w-3.5 h-3.5" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      {/* Autocomplete list */}
      {open && (
        <ul
          ref={listRef}
          className="absolute z-50 mt-1.5 w-full rounded-md bg-surface-card border border-editorial-hairline shadow-2xl py-1.5 max-h-72 overflow-y-auto backdrop-blur-xl animate-fadeIn"
        >
          {loading && (
            <li className="px-3 py-2 text-[11px] font-mono text-editorial-muted flex items-center gap-2">
              <span className="w-3 h-3 border-2 border-gold/20 border-t-gold rounded-full animate-spin" aria-hidden="true" />
              Searching market index…
            </li>
          )}
          {!query.trim() && (
            <li className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-editorial-muted border-b border-editorial-hairline">
              Popular Stocks
            </li>
          )}
          {results.map((r, i) => (
            <li
              key={r.ticker}
              onMouseEnter={() => setHighlight(i)}
              onClick={() => pick(r.ticker, r.name, r.sector)}
              className={`px-3.5 py-2.5 flex items-center justify-between cursor-pointer transition-colors text-xs ${i === highlight ? 'bg-surface-hover text-editorial-primary' : 'text-editorial-secondary hover:bg-surface-hover'}`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <div className={`w-7 h-7 rounded-md border flex items-center justify-center shrink-0 ${accent === 'gold' ? 'bg-gold/10 border-gold/30' : 'bg-cyan/10 border-cyan/30'}`}>
                  <Building2 className={`w-3.5 h-3.5 ${accent === 'gold' ? 'text-gold' : 'text-cyan'}`} aria-hidden="true" />
                </div>
                <div className="truncate">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-editorial-primary">{r.ticker}</span>
                    {r.isTop && (
                      <span className="text-[9px] font-mono px-1 py-0.2 rounded bg-gold/15 text-gold border border-gold/30 font-semibold">
                        Top Match
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-editorial-secondary truncate">{r.name}</p>
                </div>
              </div>
              <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono border shrink-0 ${accent === 'gold' ? 'bg-gold/15 text-gold border-gold/30' : 'bg-cyan/15 text-cyan border-cyan/30'}`}>
                {r.sector}
              </span>
            </li>
          ))}
          {!loading && results.length === 0 && (
            <li className="px-3 py-3 text-center text-[11px] text-editorial-muted">No ticker found for “{query}”.</li>
          )}
        </ul>
      )}

      {/* Validation message */}
      {validation.field === accentNumber && (
        <p className="mt-1.5 text-xs text-loss font-mono flex items-center gap-1.5" role="alert">
          <AlertTriangle className="w-3 h-3" aria-hidden="true" />
          {validation.message}
        </p>
      )}
    </div>
  );
};

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [company1, setCompany1] = useState<string>(() => {
    try {
      const p = JSON.parse(localStorage.getItem('stocklens.active_pair') || '{}');
      return p.c1 || '';
    } catch { return ''; }
  });
  const [company2, setCompany2] = useState<string>(() => {
    try {
      const p = JSON.parse(localStorage.getItem('stocklens.active_pair') || '{}');
      return p.c2 || '';
    } catch { return ''; }
  });
  const [howOpen, setHowOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  // Loading stages (shown on the analysis page)
  const [loadingStage, setLoadingStage] = useState<number>(0);

  useEffect(() => {
    let alive = true;
    checkHealth()
      .then((d) => { if (alive) setHealth(d); })
      .catch(() => { if (alive) setHealth(null); })
      .finally(() => { if (alive) setHealthLoading(false); });
    return () => { alive = false; };
  }, []);

  const go = useCallback(
    (c1: string, c2: string) => {
      const a = c1.trim();
      const b = c2.trim();
      if (!a || !b) return;
      if (a.toUpperCase() === b.toUpperCase()) return;
      try {
        localStorage.setItem('stocklens.active_pair', JSON.stringify({ c1: a, c2: b }));
      } catch {
        // ignore
      }
      navigate(`/analysis?c1=${encodeURIComponent(a)}&c2=${encodeURIComponent(b)}`);
    },
    [navigate]
  );

  // Local validation state (same company twice / empty)
  const [valid1, setValid1] = useState<boolean>(true);
  const [valid2, setValid2] = useState<boolean>(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!company1.trim() || !company2.trim()) {
      setValid1(!company1.trim());
      setValid2(!company2.trim());
      return;
    }
    if (company1.trim().toUpperCase() === company2.trim().toUpperCase()) {
      setValid1(true);
      setValid2(true);
      return;
    }
    go(company1.trim(), company2.trim());
  };

  return (
    <div className="min-h-screen text-editorial-primary flex flex-col">
      <main className="flex-1 w-full max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 pb-12">
        {/* ---------- Hero (cinematic, full-width) ---------- */}
        <div className="relative hero-radial-glow py-8 sm:py-14 lg:py-18 text-center">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(206,26,30,0.08),transparent_60%)] pointer-events-none" aria-hidden="true" />
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pepper/10 border border-pepper/30 text-pepper text-[11px] font-mono uppercase tracking-widest mb-4 relative z-10">
            <BadgeCheck className="w-3 h-3" aria-hidden="true" />
            Institutional Equity Analytics · Live Market Data
          </span>

          <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl lg:text-hero-lg font-normal tracking-tight leading-[1.02] max-w-4xl mx-auto relative z-10">
            Two stocks. <span className="text-pepper italic">One verdict.</span>{' '}
            <span className="font-normal text-editorial-primary">And the reason behind every move.</span>
          </h1>

          <p className="text-secondary text-base sm:text-lg leading-relaxed max-w-2xl mx-auto mt-4 relative z-10">
            730 days of adjusted prices, month-end moving averages and risk-adjusted
            metrics — with every sudden move traced to a real, indexed headline.
          </p>
        </div>

        {/* ---------- Search card ---------- */}
        <div className="card-highlight p-4 sm:p-8 max-w-4xl mx-auto mb-8">
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <CompanyInput
                label="Company 1"
                value={company1}
                onChange={setCompany1}
                accent="gold"
                accentNumber={1}
                placeholder="HAL, Reliance, TCS…"
                autoComplete="company-name"
                validation={{ field: valid1 ? null : 1, message: 'Please enter a company.' }}
              />
              <div className="flex items-end pb-1">
                <div className="text-[11px] uppercase tracking-widest font-mono text-editorial-muted select-none">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gold/70 inline-block" />
                    vs
                  </span>
                </div>
              </div>
              <CompanyInput
                label="Company 2"
                value={company2}
                onChange={setCompany2}
                accent="cyan"
                accentNumber={2}
                placeholder="Mazagon Dock, Airtel, Infosys…"
                autoComplete="company-name"
                validation={{ field: valid2 ? null : 2, message: 'Please enter a company.' }}
              />
            </div>

            {/* Inline validation summary for cross-field rules */}
            {(() => {
              const empty = !company1.trim() || !company2.trim();
              const same = company1.trim().toUpperCase() === company2.trim().toUpperCase();
              if (same) {
                return (
                  <p className="text-xs text-loss font-mono flex items-center gap-1.5" role="alert">
                    <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                    Choose two different companies — we only compare two securities at a time.
                  </p>
                );
              }
              if (empty) {
                return (
                  <p className="text-xs text-loss font-mono flex items-center gap-1.5" role="alert">
                    <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                    Both fields are required.
                  </p>
                );
              }
              return null;
            })()}

            {/* Live market row + run button */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-editorial-hairline">
              <div className="flex items-center gap-2 text-xs font-mono text-editorial-secondary">
                <span className="w-2 h-2 rounded-full bg-gain animate-pulse" />
                <span>Live Market Feed · 730-day corporate-action adjusted data</span>
              </div>

              <button
                type="submit"
                className="inline-flex items-center justify-center gap-2 px-7 py-3 rounded-lg bg-pepper text-white hover:bg-pepper-light font-semibold transition-all duration-200 shadow-glow-pepper cursor-pointer"
              >
                <span>Analyse both stocks</span>
                <ArrowRight className="w-4 h-4" aria-hidden="true" />
              </button>
            </div>
          </form>

          {/* Popular comparisons */}
          <div className="mt-5 pt-4 border-t border-editorial-hairline">
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-mono uppercase tracking-widest text-editorial-muted">
                Popular comparisons
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {POPULAR_COMPARISONS.map(([c1, c2, tag]) => (
                <button
                  key={`${c1}-${c2}`}
                  type="button"
                  onClick={() => {
                    setCompany1(c1);
                    setCompany2(c2);
                    go(c1, c2);
                  }}
                  className="text-xs px-3 py-1.5 rounded-md bg-surface-raised hover:bg-surface-subtle border border-editorial-hairline hover:border-gold/40 text-editorial-secondary hover:text-editorial-primary transition-all duration-200 flex items-center gap-1.5 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.04)] cursor-pointer"
                >
                  <span className="font-semibold text-gold">{c1}</span>
                  <span className="text-editorial-muted hidden sm:inline">vs</span>
                  <span className="font-semibold text-cyan">{c2}</span>
                  <span className="text-[10px] text-editorial-muted ml-1.5 hidden sm:inline">{tag}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* ---------- Discovery (how the platform works) ---------- */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-4xl mx-auto text-left">
          {STEPS.map((step, i) => (
            <div
              key={step.label}
              className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-2.5 transition-colors hover:border-editorial-subtle"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-surface-raised border border-editorial-hairline flex items-center justify-center shrink-0">
                  <step.icon className={`w-4 h-4 ${step.color}`} aria-hidden="true" />
                </div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-editorial-muted">
                  Step {i + 1} of 5
                </span>
              </div>
              <h3 className="text-sm font-semibold text-editorial-primary">{step.label}</h3>
              <p className="text-xs text-editorial-secondary leading-relaxed">
                {step.label === 'Fetching 2 years of prices'
                  ? 'Daily adjusted closes, resampled to the last trading session of every month.'
                  : step.label === 'Calculating moving averages'
                  ? 'Three-month moving averages smooth the month-end series and reveal the underlying trend.'
                  : step.label === 'Scanning for sudden moves'
                  ? 'Outlier days (|return| ≥ 2.5σ) are merged, filtered on a ≥3.2% net move, and classified.'
                  : step.label === 'Reading the news'
                  ? 'Contemporaneous headlines are fetched and cross-checked against the move — nothing is invented.'
                  : 'A rule-based verdict (with AI assistance when a key is available) scores stability, growth and risk.'}</p>
            </div>
          ))}
        </div>

        {/* ---------- Backend status ---------- */}
        <div className="max-w-2xl mx-auto p-3.5 card-highlight flex flex-wrap items-center justify-between gap-2 text-xs mb-10">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-editorial-muted" aria-hidden="true" />
            <span className="text-editorial-muted whitespace-nowrap">Backend API:</span>
            {healthLoading ? (
              <span className="text-editorial-muted animate-pulse">Connecting…</span>
            ) : health ? (
              <span className="text-gain font-semibold inline-flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
                {health.service} · Live Data Ready
              </span>
            ) : (
              <span className="text-loss font-semibold">unreachable — start the backend on port 8000</span>
            )}
          </div>
          <span className="font-mono text-[11px] text-editorial-muted">API /api/analyze</span>
        </div>

        <div className="max-w-4xl mx-auto mb-5 flex justify-center">
          <button type="button" onClick={() => setHowOpen(true)} className="px-5 py-3 min-h-12 rounded-lg border border-gold/30 bg-gold/10 text-gold hover:bg-gold/15 font-medium transition-colors cursor-pointer">
            How StockLens works · 20 second tour
          </button>
        </div>

        {/* ---------- How it works ---------- */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-4xl mx-auto text-left">
          {[
            { icon: Building2, title: 'Verified news', body: 'Every sudden move is paired with indexed contemporaneous headlines. If no headline exists, the system says so.' },
            { icon: Sparkles, title: 'AI-verified stories', body: 'With a key, Gemini writes the explanation; without one, a rule-based narrative takes over. Nothing is hallucinated.' },
            { icon: ShieldAlert, title: 'Transparent signals', body: 'Correlation is never presented as causation. Scores are a -10…+10 composite, including documented data bounds.' },
          ].map((f) => (
            <div key={f.title} className="p-4 rounded-lg bg-surface-card border border-editorial-hairline space-y-2">
              <div className="w-7 h-7 rounded-md bg-gold/10 text-gold flex items-center justify-center">
                <f.icon className="w-4 h-4" aria-hidden="true" />
              </div>
              <h3 className="text-sm font-semibold text-editorial-primary">{f.title}</h3>
              <p className="text-xs text-editorial-secondary leading-relaxed">{f.body}</p>
            </div>
          ))}</div>
      </main>

      {/* Production disclaimer */}
      <footer className="border-t border-editorial-hairline py-6 text-center text-xs text-editorial-muted">
        <p className="flex items-center justify-center gap-1.5 px-4">
          <ShieldAlert className="w-3.5 h-3.5 text-gold/70" aria-hidden="true" />
          <span>StockLens Dual Equity Intelligence. Market data gathered live from the web for comparative research. Not investment advice.</span>
        </p>
      </footer>

      {howOpen && <div className="fixed inset-0 z-[80] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4" onMouseDown={(event) => { if (event.target === event.currentTarget) setHowOpen(false); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="how-title" className="w-full max-w-2xl p-6 rounded-xl bg-surface-card border border-gold/30 shadow-2xl">
          <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-mono uppercase tracking-widest text-gold">A 20 second tour</p><h2 id="how-title" className="mt-1 text-2xl font-serif">From two tickers to a clear comparison</h2></div><button type="button" onClick={() => setHowOpen(false)} aria-label="Close explainer" className="p-2 rounded-md hover:bg-surface-raised"><X className="w-5 h-5" /></button></div>
          <ol className="mt-6 grid gap-3 sm:grid-cols-5">{[
            ['Pick', 'Choose two listed companies.'], ['Fetch', 'Load adjusted historical prices.'], ['Calculate', 'Measure returns, risk and moving averages.'], ['Detect', 'Find unusual moves and check dated sources.'], ['Decide', 'Compare the signals and their limits.'],
          ].map(([title, body], index) => <li key={title} className="how-step rounded-lg border border-editorial-hairline bg-surface-base p-3" style={{ animationDelay: `${index * 180}ms` }}><span className="text-xs font-mono text-gold">0{index + 1}</span><h3 className="mt-2 font-semibold">{title}</h3><p className="mt-1 text-xs leading-relaxed text-editorial-secondary">{body}</p></li>)}</ol>
          <p className="mt-5 text-xs text-editorial-muted">Market data and reported events show timing and context; they do not prove that a headline caused a price move.</p>
        </section>
      </div>}
    </div>
  );
};

/** Small badge used in the hero — doesn't exist in the design system yet */
const BadgeCheck: React.FC<{ className?: string }> = ({ className }) => (
  <svg className={className} viewBox="0 0 16 16" fill="none" aria-hidden="true">
    <circle cx="8" cy="8" r="7.5" stroke="currentColor" strokeWidth="1.5" />
    <path d="M8 6.5 l2 2 l-2 2" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
