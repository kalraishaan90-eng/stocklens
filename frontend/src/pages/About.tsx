import React from 'react';
import {
  BookOpen,
  ShieldCheck,
  Calculator,
  Scale,
  AlertCircle,
  FileCheck2,
} from 'lucide-react';

const OBJECTIVES = [
  {
    n: '01',
    title: 'Neutralise distortion',
    body: 'Compute exclusively on adjusted closes so splits and bonuses never masquerade as crashes.',
  },
  {
    n: '02',
    title: 'Smooth the noise',
    body: 'Sample the last trading day of every month, then average three months at a time.',
  },
  {
    n: '03',
    title: 'Verify every claim',
    body: 'Pair outlier moves with indexed contemporaneous headlines — or say plainly that none was found.',
  },
];

const FORMULAS = [
  {
    title: 'Compound annual growth rate',
    body: 'Geometric annualised return across the 730-day window.',
    formula: 'CAGR = (P_end / P_start)^(365.25 / Δdays) − 1',
    cls: 'text-pepper',
  },
  {
    title: 'Annualised volatility',
    body: 'Dispersion of daily returns scaled to 252 sessions.',
    formula: 'σ_ann = StdDev(daily returns) × √252',
    cls: 'text-editorial-secondary',
  },
  {
    title: 'Maximum drawdown',
    body: 'Deepest peak-to-trough decline before recovery.',
    formula: 'MDD = |min( (P_t − peak_t) / peak_t )|',
    cls: 'text-loss',
  },
  {
    title: 'Sharpe ratio',
    body: 'Excess return per unit of risk, against the Indian sovereign yield (R_f = 6.5%).',
    formula: 'Sharpe = (CAGR% − 6.5%) / σ_ann%',
    cls: 'text-gain',
  },
];

const RULES = [
  {
    icon: FileCheck2,
    title: 'Rule 1 — no fabricated news',
    body: 'Explanations cite indexed public headlines only. If none is found within the event window, the engine says so instead of inventing a cause.',
    iconCls: 'text-gain',
  },
  {
    icon: AlertCircle,
    title: 'Rule 2 — correlation ≠ causation',
    body: 'A headline near a price move does not prove the headline caused it. Liquidity and sentiment move markets too.',
    iconCls: 'text-pepper',
  },
  {
    icon: ShieldCheck,
    title: 'Rule 3 — research use only',
    body: 'StockLens provides analytical equity research, not personal financial advice. Past performance never guarantees future returns.',
    iconCls: 'text-editorial-secondary',
  },
];

export const About: React.FC = () => {
  return (
    <div className="min-h-screen text-editorial-primary pb-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10 sm:py-14 space-y-10 sm:space-y-14">
        {/* Header */}
        <header className="text-center space-y-3">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-pepper/10 border border-pepper/30 text-pepper text-xs font-mono uppercase tracking-widest">
            Institutional Architecture
          </span>
          <h1 className="text-3xl sm:text-4xl font-serif tracking-tight">About StockLens</h1>
          <p className="text-editorial-secondary max-w-2xl mx-auto text-sm sm:text-base leading-relaxed">
            A high-precision financial comparative intelligence platform: compare any two publicly listed
            equities over 730 days on identical, corporate-action-adjusted terms with verified market context.
          </p>
        </header>

        {/* Objectives */}
        <section aria-labelledby="objectives" className="card-highlight p-5 sm:p-8 space-y-5">
          <h2 id="objectives" className="text-xl font-serif flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-pepper" aria-hidden="true" />
            Objectives
          </h2>
          <p className="text-sm text-editorial-secondary leading-relaxed">
            Financial time series lie in small ways: splits, bonuses and headline noise all distort what actually
            happened. StockLens applies one consistent method so two very different securities can be compared
            honestly.
          </p>
          <ol className="grid grid-cols-1 sm:grid-cols-3 gap-4 list-none p-0 m-0">
            {OBJECTIVES.map((o) => (
              <li key={o.n} className="p-4 bg-surface-base rounded-md border border-editorial-hairline text-xs space-y-1.5">
                <span className="font-mono text-[11px] font-bold text-pepper tracking-widest">{o.n}</span>
                <p className="font-semibold text-editorial-primary text-sm">{o.title}</p>
                <p className="text-editorial-secondary leading-relaxed">{o.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Formulas */}
        <section aria-labelledby="formulas" className="card-highlight p-5 sm:p-8 space-y-5">
          <h2 id="formulas" className="text-xl font-serif flex items-center gap-2">
            <Calculator className="w-5 h-5 text-pepper" aria-hidden="true" />
            Mathematical formulations
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {FORMULAS.map((f) => (
              <div key={f.title} className="p-4 bg-surface-base rounded-md border border-editorial-hairline space-y-2">
                <h3 className="font-semibold text-editorial-primary text-sm">{f.title}</h3>
                <p className="text-editorial-secondary">{f.body}</p>
                <p className={`p-2 bg-surface-raised rounded font-mono text-[11px] ${f.cls} overflow-x-auto whitespace-nowrap`}>
                  {f.formula}
                </p>
              </div>
            ))}
          </div>
        </section>

        {/* Compliance rules */}
        <section aria-labelledby="rules" className="card-highlight p-5 sm:p-8 space-y-5">
          <h2 id="rules" className="text-xl font-serif flex items-center gap-2">
            <Scale className="w-5 h-5 text-pepper" aria-hidden="true" />
            Hard rules &amp; disclaimers
          </h2>
          <ul className="space-y-3 text-xs list-none p-0 m-0">
            {RULES.map((r) => (
              <li key={r.title} className="flex items-start gap-3 p-3.5 bg-surface-base rounded-md border border-editorial-hairline">
                <r.icon className={`w-4 h-4 flex-shrink-0 mt-0.5 ${r.iconCls}`} aria-hidden="true" />
                <div>
                  <strong className="text-editorial-primary">{r.title}:</strong>{' '}
                  <span className="text-editorial-secondary">{r.body}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
};
