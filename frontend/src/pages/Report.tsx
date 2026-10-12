import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Printer, ArrowLeft, AlertTriangle, Download, FileSpreadsheet } from 'lucide-react';
import { analyzeStocks, downloadGoogleSheetsCsv, downloadReportPdf, downloadTemplateCsv } from '../lib/api';
import { AnalysisResponse } from '../lib/types';
import { fmtPctSigned } from '../lib/utils';

const stripLabel = (text?: string | null) => (text ?? '').replace(/^\[Auto-generated without AI\]\s*/, '');
const STUDENT_DETAILS_KEY = 'stocklens.report.student-details.v1';

function readStudentDetails() {
  try {
    const saved = JSON.parse(localStorage.getItem(STUDENT_DETAILS_KEY) || '{}');
    return {
      name: typeof saved.name === 'string' ? saved.name : '',
      roll: typeof saved.roll === 'string' ? saved.roll : '',
    };
  } catch {
    return { name: '', roll: '' };
  }
}

export const Report: React.FC = () => {
  const [searchParams] = useSearchParams();
  const savedPair = (() => {
    try { return JSON.parse(localStorage.getItem('stocklens.active_pair') || '{}'); } catch { return {}; }
  })();
  const c1 = searchParams.get('c1') || savedPair.c1 || '';
  const c2 = searchParams.get('c2') || savedPair.c2 || '';

  useEffect(() => {
    if (c1 && c2) {
      try {
        localStorage.setItem('stocklens.active_pair', JSON.stringify({ c1, c2 }));
      } catch {
        // ignore
      }
    }
  }, [c1, c2]);

  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(c1 && c2));
  const [error, setError] = useState<string | null>(null);
  const [student, setStudent] = useState(readStudentDetails);
  const [printTheme, setPrintTheme] = useState<'dark' | 'light'>('dark');
  const [exporting, setExporting] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const lastRunKey = useRef<string | null>(null);

  useEffect(() => {
    localStorage.setItem(STUDENT_DETAILS_KEY, JSON.stringify(student));
  }, [student]);

  useEffect(() => {
    if (!c1.trim() || !c2.trim()) {
      setLoading(false);
      return;
    }
    const key = `${c1}|${c2}`;
    if (lastRunKey.current === key) return;
    lastRunKey.current = key;
    analyzeStocks({ company1: c1, company2: c2 })
      .then(setData)
      .catch((e: any) => setError(e.message || 'Could not load report data.'))
      .finally(() => setLoading(false));
  }, [c1, c2]);

  const handlePrint = () => {
    window.print();
  };

  const runExport = async (kind: 'pdf' | 'csv' | 'sheets') => {
    setExporting(kind);
    setExportError(null);
    try {
      const options = {
        company1: c1,
        company2: c2,
        use_offline_demo: false,
        student_name: student.name.trim() || 'Equity Research Analyst',
        roll_number: student.roll.trim() || 'SL-EQ-730',
        theme: printTheme,
      };
      if (kind === 'pdf') await downloadReportPdf(options);
      else if (kind === 'csv') await downloadTemplateCsv(options);
      else await downloadGoogleSheetsCsv(options);
    } catch (e) {
      setExportError(e instanceof Error ? e.message : 'Could not export this file.');
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen text-editorial-primary flex flex-col items-center justify-center gap-3 p-4">
        <div className="w-8 h-8 border-2 border-gold/20 border-t-gold rounded-full animate-spin" aria-hidden="true" />
        <p className="text-sm text-editorial-secondary animate-pulse" role="status" aria-live="polite">
          Compiling comparative research report…
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen text-editorial-primary flex flex-col items-center justify-center p-4 text-center gap-4">
        <AlertTriangle className="w-7 h-7 text-loss" aria-hidden="true" />
        <p className="text-sm text-editorial-secondary max-w-md">{error || 'Could not load report data.'}</p>
        <Link to="/" className="px-4 py-2 bg-gold hover:bg-gold-light text-surface-base rounded-md text-xs font-semibold">
          Back to home
        </Link>
      </div>
    );
  }

  const { resolved_tickers, monthly_table, moving_averages, metrics, comparison, recommendations, anomalies, metadata } = data;
  const dd = (v: number) => (v === 0 ? '0.0%' : `-${v.toFixed(1)}%`);

  return (
    <div className="min-h-screen text-editorial-primary pb-16">
      {/* Action Bar (hidden in print) */}
      <div className="print:hidden border-b border-editorial-hairline py-4 px-4 sm:px-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between gap-3">
          <Link
            to={`/analysis?c1=${encodeURIComponent(c1)}&c2=${encodeURIComponent(c2)}`}
            className="flex items-center gap-2 text-xs font-medium text-editorial-secondary hover:text-editorial-primary transition"
          >
            <ArrowLeft className="w-4 h-4" aria-hidden="true" />
            <span>Back to analysis</span>
          </Link>

          <div className="flex flex-wrap items-center justify-end gap-2">
            <button type="button" disabled={Boolean(exporting)} onClick={() => void runExport('pdf')}
              className="px-4 py-2 bg-gold hover:bg-gold-light disabled:opacity-60 text-surface-base rounded-md text-xs font-semibold flex items-center gap-2 transition cursor-pointer">
              <Download className="w-4 h-4" aria-hidden="true" />
              <span>{exporting === 'pdf' ? 'Generating PDF…' : 'Download Report'}</span>
            </button>
            <button type="button" disabled={Boolean(exporting)} onClick={() => void runExport('csv')}
              className="px-3 py-2 border border-editorial-hairline hover:border-gold disabled:opacity-60 rounded-md text-xs font-medium flex items-center gap-2 transition cursor-pointer">
              <FileSpreadsheet className="w-4 h-4" aria-hidden="true" /> Export CSV
            </button>
            <button type="button" disabled={Boolean(exporting)} onClick={() => void runExport('sheets')}
              className="px-3 py-2 border border-editorial-hairline hover:border-gold disabled:opacity-60 rounded-md text-xs font-medium transition cursor-pointer">
              Export Google Sheets CSV
            </button>
            <button type="button" onClick={handlePrint}
              className="px-3 py-2 border border-editorial-hairline hover:border-gold rounded-md text-xs font-medium flex items-center gap-2 transition cursor-pointer">
              <Printer className="w-4 h-4" aria-hidden="true" /> Print preview
            </button>
          </div>
        </div>
        <div className="max-w-4xl mx-auto mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto] items-end">
          <label className="text-[11px] text-editorial-secondary">Prepared by / Analyst
            <input value={student.name} maxLength={120} onChange={(e) => setStudent((v) => ({ ...v, name: e.target.value }))}
              className="mt-1 block w-full rounded border border-editorial-hairline bg-surface-base px-3 py-2 text-xs text-editorial-primary outline-none focus:border-gold" placeholder="e.g. Lead Research Analyst" />
          </label>
          <label className="text-[11px] text-editorial-secondary">Report Reference / ID
            <input value={student.roll} maxLength={40} onChange={(e) => setStudent((v) => ({ ...v, roll: e.target.value }))}
              className="mt-1 block w-full rounded border border-editorial-hairline bg-surface-base px-3 py-2 text-xs text-editorial-primary outline-none focus:border-gold" placeholder="e.g. SL-EQ-2026" />
          </label>
          <label className="text-[11px] text-editorial-secondary">PDF ink theme
            <select value={printTheme} onChange={(e) => setPrintTheme(e.target.value as 'dark' | 'light')}
              className="mt-1 block w-full rounded border border-editorial-hairline bg-surface-base px-3 py-2 text-xs text-editorial-primary outline-none focus:border-gold">
              <option value="dark">Dark editorial</option><option value="light">Light-ink print</option>
            </select>
          </label>
        </div>
        {exportError && <p className="max-w-4xl mx-auto mt-3 text-xs text-loss" role="alert">{exportError}</p>}
      </div>

      {/* Printable document — warm paper instead of glaring pure white */}
      <div className="max-w-4xl mx-auto my-6 sm:my-8 p-6 sm:p-10 lg:p-12 bg-[#F7F5F0] text-[#16181C] rounded-lg shadow-hairline print:m-0 print:p-6 print:shadow-none print:rounded-none print:max-w-none">
        {/* Cover / Document Header */}
        <header className="border-b-2 border-[#16181C] pb-5 mb-7 text-center space-y-2">
          <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#7A6A3F]">
            StockLens Institutional Equity Research
          </span>
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight">
            Comparative Time-Series Equity Analysis
          </h1>
          <p className="text-sm font-semibold text-[#3A3F47]">
            {resolved_tickers.company1.name} ({resolved_tickers.company1.ticker}) vs{' '}
            {resolved_tickers.company2.name} ({resolved_tickers.company2.ticker})
          </p>
          <p className="text-xs text-[#6A6F78]">
            Analysis date:{' '}
            {new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })} ·
            Window: dynamic 730 calendar days
          </p>
        </header>

        {/* 1. Executive Summary */}
        <section className="mb-7 space-y-2.5">
          <h2 className="text-sm font-bold uppercase tracking-wide border-b border-[#D8D3C8] pb-1">
            1. Executive summary
          </h2>
          <p className="text-xs leading-relaxed text-[#3A3F47]">
            This study compares {resolved_tickers.company1.name} and {resolved_tickers.company2.name} over a
            rolling 730-day window using corporate-action-adjusted closing prices, month-end 3-month moving
            averages and annualised risk metrics — removing split/dividend distortions so both securities are
            judged on identical terms.
          </p>
          <div className="p-3 bg-[#EFEBE1] border border-[#D8D3C8] rounded-md text-xs text-[#2A2E35] font-medium">
            <strong>Head-to-head finding:</strong> {comparison.winner_name} ({comparison.winner_ticker}) scored{' '}
            {Math.abs(comparison.score_diff).toFixed(1)} points higher — {comparison.margin.toLowerCase()} — with a
            2-year price correlation of {comparison.correlation_2y.toFixed(2)} against{' '}
            {comparison.winner_ticker === resolved_tickers.company1.ticker
              ? resolved_tickers.company2.ticker
              : resolved_tickers.company1.ticker}
            .
          </div>
        </section>

        {/* 2. Methodology */}
        <section className="mb-7 space-y-2.5">
          <h2 className="text-sm font-bold uppercase tracking-wide border-b border-[#D8D3C8] pb-1">
            2. Methodology &amp; formulas
          </h2>
          <ul className="text-xs space-y-1.5 text-[#3A3F47] list-disc list-inside">
            <li>
              <strong>Adjusted close:</strong> raw closes restated for splits, bonuses and dividends to prevent
              false structural dislocations.
            </li>
            <li>
              <strong>CAGR:</strong> <code className="font-mono text-[11px]">(P_end / P_start)^(365.25 / Δdays) − 1</code>
            </li>
            <li>
              <strong>Annualised volatility:</strong> <code className="font-mono text-[11px]">StdDev(daily returns) × √252</code>
            </li>
            <li>
              <strong>Sharpe ratio:</strong> <code className="font-mono text-[11px]">(CAGR% − 6.5%) / σ_ann%</code>{' '}
              with the Indian sovereign 10-year yield as R<sub>f</sub>.
            </li>
            <li>
              <strong>MA-3M:</strong> rolling mean of the last three month-end closes; the first two cells are
              blank by construction.
            </li>
          </ul>
        </section>

        {/* 3. Metric matrix */}
        <section className="mb-7 space-y-2.5">
          <h2 className="text-sm font-bold uppercase tracking-wide border-b border-[#D8D3C8] pb-1">
            3. Quantitative comparison
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-xs border border-[#D8D3C8]">
            <caption className="sr-only">
              Key metrics for {resolved_tickers.company1.name} and {resolved_tickers.company2.name}
            </caption>
            <thead className="bg-[#EFEBE1] font-bold text-[#2A2E35]">
              <tr>
                <th scope="col" className="py-2 px-3 text-left">Metric</th>
                <th scope="col" className="py-2 px-3 text-right">{resolved_tickers.company1.ticker.replace('.NS', '')}</th>
                <th scope="col" className="py-2 px-3 text-right">{resolved_tickers.company2.ticker.replace('.NS', '')}</th>
                <th scope="col" className="py-2 px-3 text-center">Advantage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E3DED3] text-[#2A2E35]">
              <tr>
                <td className="py-2 px-3 font-medium">Latest adjusted close</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">₹{metrics.company1.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">₹{metrics.company2.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="py-2 px-3 text-center">—</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">2-year CAGR</td>
                <td className={`py-2 px-3 text-right font-mono font-bold tabular-nums ${metrics.company1.cagr_pct >= 0 ? 'text-[#1B7A50]' : 'text-[#B3352B]'}`}>
                  {fmtPctSigned(metrics.company1.cagr_pct)}
                </td>
                <td className={`py-2 px-3 text-right font-mono font-bold tabular-nums ${metrics.company2.cagr_pct >= 0 ? 'text-[#1B7A50]' : 'text-[#B3352B]'}`}>
                  {fmtPctSigned(metrics.company2.cagr_pct)}
                </td>
                <td className="py-2 px-3 text-center font-semibold">
                  {metrics.company1.cagr_pct > metrics.company2.cagr_pct
                    ? resolved_tickers.company1.ticker.replace('.NS', '')
                    : resolved_tickers.company2.ticker.replace('.NS', '')}
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">Annualised volatility</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">{metrics.company1.annualized_volatility_pct.toFixed(1)}%</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">{metrics.company2.annualized_volatility_pct.toFixed(1)}%</td>
                <td className="py-2 px-3 text-center font-semibold">
                  {metrics.company1.annualized_volatility_pct < metrics.company2.annualized_volatility_pct
                    ? resolved_tickers.company1.ticker.replace('.NS', '')
                    : resolved_tickers.company2.ticker.replace('.NS', '')}{' '}
                  <span className="font-normal text-[#6A6F78]">(lower)</span>
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">Max drawdown</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">{dd(metrics.company1.max_drawdown_pct)}</td>
                <td className="py-2 px-3 text-right font-mono tabular-nums">{dd(metrics.company2.max_drawdown_pct)}</td>
                <td className="py-2 px-3 text-center font-semibold">
                  {metrics.company1.max_drawdown_pct < metrics.company2.max_drawdown_pct
                    ? resolved_tickers.company1.ticker.replace('.NS', '')
                    : resolved_tickers.company2.ticker.replace('.NS', '')}{' '}
                  <span className="font-normal text-[#6A6F78]">(shallower)</span>
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">Sharpe ratio (R<sub>f</sub> = 6.5%)</td>
                <td className="py-2 px-3 text-right font-mono font-bold tabular-nums">{metrics.company1.sharpe_ratio.toFixed(2)}</td>
                <td className="py-2 px-3 text-right font-mono font-bold tabular-nums">{metrics.company2.sharpe_ratio.toFixed(2)}</td>
                <td className="py-2 px-3 text-center font-semibold">
                  {metrics.company1.sharpe_ratio > metrics.company2.sharpe_ratio
                    ? resolved_tickers.company1.ticker.replace('.NS', '')
                    : resolved_tickers.company2.ticker.replace('.NS', '')}
                </td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">Model rating <span className="text-[#6A6F78] font-normal">(-10…+10)</span></td>
                <td className="py-2 px-3 text-right font-semibold">
                  {recommendations.company1.action}{' '}
                  <span className="font-mono text-[#6A6F78]">
                    ({recommendations.company1.score > 0 ? '+' : ''}{recommendations.company1.score.toFixed(1)})
                  </span>
                </td>
                <td className="py-2 px-3 text-right font-semibold">
                  {recommendations.company2.action}{' '}
                  <span className="font-mono text-[#6A6F78]">
                    ({recommendations.company2.score > 0 ? '+' : ''}{recommendations.company2.score.toFixed(1)})
                  </span>
                </td>
                <td className="py-2 px-3 text-center">—</td>
              </tr>
            </tbody>
            </table>
          </div>
        </section>

        {/* 4. Monthly template table (project shape) */}
        <section className="mb-7 space-y-2.5">
          <h2 className="text-sm font-bold uppercase tracking-wide border-b border-[#D8D3C8] pb-1">
            4. Month-end closes &amp; 3-month moving averages
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[460px] text-xs border border-[#D8D3C8]">
            <caption className="sr-only">
              Monthly closing prices and 3-month moving averages for both companies
            </caption>
            <thead className="bg-[#EFEBE1] font-bold text-[#2A2E35]">
              <tr>
                <th scope="col" className="py-2 px-3 text-left">Month</th>
                <th scope="col" className="py-2 px-3 text-right">{resolved_tickers.company1.ticker.replace('.NS', '')} close</th>
                <th scope="col" className="py-2 px-3 text-right">MA-3M</th>
                <th scope="col" className="py-2 px-3 text-right">{resolved_tickers.company2.ticker.replace('.NS', '')} close</th>
                <th scope="col" className="py-2 px-3 text-right">MA-3M</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#E3DED3] text-[#2A2E35]">
              {monthly_table.map((row) => {
                const ma = moving_averages.find((m) => m.date === row.date);
                const fmt = (v?: number | null) =>
                  v != null
                    ? v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                    : '—';
                return (
                  <tr key={row.date}>
                    <th scope="row" className="py-1.5 px-3 text-left font-medium whitespace-nowrap">{row.month_label}</th>
                    <td className="py-1.5 px-3 text-right font-mono tabular-nums">{fmt(row.company1_adj_close)}</td>
                    <td className="py-1.5 px-3 text-right font-mono tabular-nums text-[#6A6F78]">{fmt(ma?.company1_ma_3m)}</td>
                    <td className="py-1.5 px-3 text-right font-mono tabular-nums">{fmt(row.company2_adj_close)}</td>
                    <td className="py-1.5 px-3 text-right font-mono tabular-nums text-[#6A6F78]">{fmt(ma?.company2_ma_3m)}</td>
                  </tr>
                );
              })}
            </tbody>
            </table>
          </div>
          <p className="text-[11px] text-[#6A6F78]">
            Each month is sampled on its final trading session; blank MA cells mark the warm-up window.
          </p>
        </section>

        {/* 5. Anomaly attribution */}
        <section className="mb-7 space-y-2.5">
          <h2 className="text-sm font-bold uppercase tracking-wide border-b border-[#D8D3C8] pb-1">
            5. Verified anomaly attribution
          </h2>
          {anomalies.length === 0 ? (
            <p className="text-xs text-[#3A3F47] p-3 bg-[#EFEBE1] border border-[#D8D3C8] rounded-md">
              No net move crossed the 3.2% outlier threshold during this window; no attribution was required.
            </p>
          ) : (
            <>
              <p className="text-xs text-[#4A4F58]">
                Sessions with net moves ≥3.2% (beyond 2.5× trailing volatility), paired with contemporaneous
                indexed headlines:
              </p>
              <ul className="space-y-2">
                {anomalies.map((anom, idx) => (
                  <li key={idx} className="p-3 bg-[#EFEBE1] border border-[#D8D3C8] rounded-md text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold gap-2">
                      <span className="text-[#16181C]">{anom.company_name} ({anom.ticker})</span>
                      <span className="text-[#4A4F58] font-mono tabular-nums">
                        {anom.date} · {fmtPctSigned(anom.change_pct)}
                      </span>
                    </div>
                    <p className="text-[#3A3F47] italic">“{anom.headline}” — <strong>{anom.source}</strong></p>
                    <p className="text-[#4A4F58]">{stripLabel(anom.explanation)}</p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        {/* 6. Disclaimers */}
        <footer className="pt-5 border-t-2 border-[#16181C] text-[11px] text-[#6A6F78] space-y-1.5">
          <p className="font-semibold text-[#3A3F47]">Disclaimers</p>
          <p>{metadata.disclaimer}</p>
          <p>{metadata.causation_warning}</p>
        </footer>
      </div>
    </div>
  );
};
