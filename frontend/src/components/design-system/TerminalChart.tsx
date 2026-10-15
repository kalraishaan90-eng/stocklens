import React, { useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ChartDataPoint {
  date: string;
  // Company 1
  c1Price: number | null;
  c1MA: number | null;
  c1Rebased: number | null;
  c1PctChange: number | null;
  // Company 2
  c2Price: number | null;
  c2MA: number | null;
  c2Rebased: number | null;
  c2PctChange: number | null;
}

export interface TerminalChartProps {
  data: ChartDataPoint[];
  company1Name?: string;
  company1Symbol?: string;
  company2Name?: string;
  company2Symbol?: string;
  title?: string;
  subtitle?: string;
  height?: number;
  className?: string;
}

/**
 * Design-system sample ONLY for /design-system showcase.
 * Product pages must pass real API data - the chart never fabricates prices.
 */
export const SAMPLE_CHART_DATA: ChartDataPoint[] = [
  { date: 'Nov 24', c1Price: 1250, c1MA: null, c1Rebased: 100.0, c1PctChange: null, c2Price: 720, c2MA: null, c2Rebased: 100.0, c2PctChange: null },
  { date: 'Dec 24', c1Price: 1290, c1MA: null, c1Rebased: 103.2, c1PctChange: 3.2, c2Price: 760, c2MA: null, c2Rebased: 105.5, c2PctChange: 5.5 },
  { date: 'Jan 25', c1Price: 1240, c1MA: 1260.0, c1Rebased: 99.2, c1PctChange: -3.9, c2Price: 750, c2MA: 743.3, c2Rebased: 104.2, c2PctChange: -1.3 },
  { date: 'Feb 25', c1Price: 1310, c1MA: 1280.0, c1Rebased: 104.8, c1PctChange: 5.6, c2Price: 790, c2MA: 766.7, c2Rebased: 109.7, c2PctChange: 5.3 },
  { date: 'Mar 25', c1Price: 1380, c1MA: 1310.0, c1Rebased: 110.4, c1PctChange: 5.3, c2Price: 830, c2MA: 790.0, c2Rebased: 115.3, c2PctChange: 5.1 },
  { date: 'Apr 25', c1Price: 1470, c1MA: 1386.7, c1Rebased: 117.6, c1PctChange: 6.5, c2Price: 890, c2MA: 836.7, c2Rebased: 123.6, c2PctChange: 7.2 },
  { date: 'May 25', c1Price: 1540, c1MA: 1463.3, c1Rebased: 123.2, c1PctChange: 4.8, c2Price: 940, c2MA: 886.7, c2Rebased: 130.6, c2PctChange: 5.6 },
  { date: 'Jun 25', c1Price: 1720, c1MA: 1576.7, c1Rebased: 137.6, c1PctChange: 11.7, c2Price: 1120, c2MA: 983.3, c2Rebased: 155.6, c2PctChange: 19.1 },
];

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(
    () => typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
  React.useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener?.('change', onChange);
    return () => mq.removeEventListener?.('change', onChange);
  }, []);
  return reduced;
}

const TerminalChartView: React.FC<TerminalChartProps> = ({
  data,
  company1Name = 'Company 1',
  company1Symbol = 'C1',
  company2Name = 'Company 2',
  company2Symbol = 'C2',
  title = 'Adjusted Close & 3-Month Moving Average',
  subtitle = 'Month-end adjusted closes with rolling 3-month averages, rebased to 100 for a like-for-like comparison.',
  height = 420,
  className,
}) => {
  const [isRebased, setIsRebased] = useState(true);
  const [showCompany1, setShowCompany1] = useState(true);
  const [showCompany2, setShowCompany2] = useState(true);
  const [showMA, setShowMA] = useState(true);
  const reducedMotion = usePrefersReducedMotion();

  // Rebase base = first available price. (Never hard-code a divisor: real
  // datasets start at arbitrary price levels.)
  const c1Base = useMemo(
    () => data.find((d) => d.c1Price != null && isFinite(d.c1Price))?.c1Price ?? null,
    [data]
  );
  const c2Base = useMemo(
    () => data.find((d) => d.c2Price != null && isFinite(d.c2Price))?.c2Price ?? null,
    [data]
  );

  const rebase = (value: number | null | undefined, base: number | null): number | null => {
    if (value == null || !base) return null;
    return (value / base) * 100;
  };

  // Accessible text summary (screen readers cannot inspect the SVG lines)
  const textSummary = useMemo(() => {
    if (!data.length) return 'No chart data available.';
    const first = data[0];
    const last = data[data.length - 1];
    const span = `${first.date} to ${last.date}`;
    const c1Move = first.c1Rebased != null && last.c1Rebased != null
      ? ((last.c1Rebased - first.c1Rebased) / first.c1Rebased) * 100 : null;
    const c2Move = first.c2Rebased != null && last.c2Rebased != null
      ? ((last.c2Rebased - first.c2Rebased) / first.c2Rebased) * 100 : null;
    const parts = [
      `Line chart comparing ${company1Name} (${company1Symbol}) and ${company2Name} (${company2Symbol}) over ${span}, ${data.length} monthly points.`,
    ];
    if (c1Move != null) parts.push(`${company1Symbol} changed ${c1Move >= 0 ? '+' : ''}${c1Move.toFixed(1)} percent.`);
    if (c2Move != null) parts.push(`${company2Symbol} changed ${c2Move >= 0 ? '+' : ''}${c2Move.toFixed(1)} percent.`);
    if (showMA) parts.push('Dashed lines show the 3-month moving average, which begins after the first two months.');
    return parts.join(' ');
  }, [data, company1Name, company1Symbol, company2Name, company2Symbol, showMA]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    const point = payload[0].payload as ChartDataPoint;
    const fmtPrice = (v: number | null) => (v == null ? '—' : `₹${v.toLocaleString('en-IN')}`);
    const fmtRebased = (v: number | null) => (v == null ? '—' : v.toFixed(1));

    return (
      <div className="p-3.5 rounded-lg bg-surface-card border border-editorial-hairline shadow-2xl backdrop-blur-md min-w-[260px] font-sans">
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-editorial-hairline text-xs font-mono">
          <span className="text-editorial-primary font-semibold tracking-wide">{label}</span>
          <span className="text-[10px] text-editorial-muted uppercase tracking-widest">
            {isRebased ? 'Base 100 Index' : 'Adjusted Close'}
          </span>
        </div>

        {showCompany1 && (
          <div className="py-1.5 space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-gold font-mono font-semibold">
                <span className="w-2 h-2 rounded-full bg-gold" />
                <span>{company1Symbol}</span>
              </span>
              <span className="font-mono text-editorial-primary font-bold font-tabular">
                {isRebased ? fmtRebased(point.c1Rebased) : fmtPrice(point.c1Price)}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-editorial-secondary font-mono pl-3.5">
              <span>
                3M MA:{' '}
                {point.c1MA == null
                  ? '—'
                  : isRebased
                  ? fmtRebased(rebase(point.c1MA, c1Base))
                  : fmtPrice(point.c1MA)}
              </span>
              <span className={clsx('font-semibold', (point.c1PctChange ?? 0) >= 0 ? 'text-gain' : 'text-loss')}>
                {point.c1PctChange == null
                  ? '—'
                  : `${point.c1PctChange >= 0 ? '+' : ''}${point.c1PctChange.toFixed(1)}%`}
              </span>
            </div>
          </div>
        )}

        {showCompany2 && (
          <div className="py-1.5 space-y-1 border-t border-editorial-hairline/40 mt-1">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-cyan font-mono font-semibold">
                <span className="w-2 h-2 rounded-full bg-cyan" />
                <span>{company2Symbol}</span>
              </span>
              <span className="font-mono text-editorial-primary font-bold font-tabular">
                {isRebased ? fmtRebased(point.c2Rebased) : fmtPrice(point.c2Price)}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-editorial-secondary font-mono pl-3.5">
              <span>
                3M MA:{' '}
                {point.c2MA == null
                  ? '—'
                  : isRebased
                  ? fmtRebased(rebase(point.c2MA, c2Base))
                  : fmtPrice(point.c2MA)}
              </span>
              <span className={clsx('font-semibold', (point.c2PctChange ?? 0) >= 0 ? 'text-gain' : 'text-loss')}>
                {point.c2PctChange == null
                  ? '—'
                  : `${point.c2PctChange >= 0 ? '+' : ''}${point.c2PctChange.toFixed(1)}%`}
              </span>
            </div>
          </div>
        )}

        {showCompany1 && showCompany2 && point.c1Rebased != null && point.c2Rebased != null && (
          <div className="mt-2 pt-2 border-t border-editorial-hairline text-[10px] font-mono text-editorial-muted flex justify-between items-center">
            <span>Relative spread:</span>
            <span className="text-gold font-medium">
              {(point.c2Rebased - point.c1Rebased).toFixed(1)} pts
            </span>
          </div>
        )}
      </div>
    );
  };

  if (!data.length) {
    return (
      <div className={twMerge('p-6 rounded-card bg-surface-card border border-editorial-hairline', className)}>
        <p className="text-sm text-editorial-secondary font-sans">
          No overlapping trading history is available for these two securities, so no comparison chart can be drawn.
        </p>
      </div>
    );
  }

  return (
    <figure
      className={twMerge(
        clsx(
          'p-4 sm:p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-4 font-sans m-0',
          className
        )
      )}
      role="img"
      aria-label={textSummary}
    >
      {/* Chart Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-editorial-hairline">
        <figcaption className="space-y-1 text-left">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold tracking-widest text-gold uppercase px-2 py-0.5 rounded bg-gold/10 border border-gold/25">
              Monthly Series
            </span>
          </div>
          <h3 className="font-serif text-lg sm:text-xl font-normal text-editorial-primary">
            {title}
          </h3>
          <p className="text-xs text-editorial-secondary max-w-xl leading-relaxed">
            {subtitle}
          </p>
        </figcaption>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <div className="inline-flex p-0.5 rounded-lg bg-surface-raised border border-editorial-hairline text-xs font-mono" role="group" aria-label="Price scale">
            <button
              type="button"
              onClick={() => setIsRebased(true)}
              aria-pressed={isRebased}
              className={clsx(
                'px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium',
                isRebased
                  ? 'bg-gold text-surface-base font-semibold shadow-sm'
                  : 'text-editorial-secondary hover:text-editorial-primary'
              )}
            >
              Rebased to 100
            </button>
            <button
              type="button"
              onClick={() => setIsRebased(false)}
              aria-pressed={!isRebased}
              className={clsx(
                'px-2.5 py-1 rounded-md transition-all cursor-pointer font-medium',
                !isRebased
                  ? 'bg-gold text-surface-base font-semibold shadow-sm'
                  : 'text-editorial-secondary hover:text-editorial-primary'
              )}
            >
              Actual (₹)
            </button>
          </div>

          <button
            type="button"
            onClick={() => setShowMA(!showMA)}
            aria-pressed={showMA}
            className={clsx(
              'px-2.5 py-1 rounded-md text-xs font-mono border transition-colors cursor-pointer flex items-center gap-1.5',
              showMA
                ? 'bg-surface-raised text-editorial-primary border-editorial-subtle'
                : 'text-editorial-muted border-editorial-hairline hover:text-editorial-secondary'
            )}
          >
            <span
              className={clsx(
                'w-2 h-0.5 border-t border-dashed',
                showMA ? 'border-editorial-primary' : 'border-editorial-muted'
              )}
            />
            <span>3M MA</span>
          </button>
        </div>
      </div>

      {/* Legend toggles */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono pt-1">
        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={() => setShowCompany1(!showCompany1)}
            aria-pressed={showCompany1}
            className={clsx(
              'flex items-center gap-2 px-2.5 py-1 rounded border transition-colors cursor-pointer',
              showCompany1
                ? 'border-gold/30 bg-gold/10 text-gold'
                : 'border-editorial-hairline text-editorial-muted line-through opacity-50'
            )}
          >
            <span className="w-3 h-0.5 bg-gold" />
            <span className="font-semibold">{company1Symbol}</span>
            <span className="text-[10px] text-editorial-secondary hidden sm:inline">
              ({company1Name})
            </span>
          </button>

          <button
            type="button"
            onClick={() => setShowCompany2(!showCompany2)}
            aria-pressed={showCompany2}
            className={clsx(
              'flex items-center gap-2 px-2.5 py-1 rounded border transition-colors cursor-pointer',
              showCompany2
                ? 'border-cyan/30 bg-cyan/10 text-cyan'
                : 'border-editorial-hairline text-editorial-muted line-through opacity-50'
            )}
          >
            <span className="w-3 h-0.5 bg-cyan" />
            <span className="font-semibold">{company2Symbol}</span>
            <span className="text-[10px] text-editorial-secondary hidden sm:inline">
              ({company2Name})
            </span>
          </button>
        </div>

        <div className="text-[11px] text-editorial-muted flex flex-wrap items-center gap-3">
          <span className="flex items-center gap-1.5">
            <span className="w-3.5 h-[1.5px] bg-editorial-secondary inline-block" /> Solid: adjusted close
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-3.5 h-[1.5px] border-t border-dashed border-editorial-secondary inline-block" /> Dashed: 3M MA
          </span>
        </div>
      </div>

      {/* Main Responsive Recharts Area */}
      <div style={{ width: '100%', height }} className="pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="c1AreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#C9A96A" stopOpacity={0.16} />
                <stop offset="90%" stopColor="#C9A96A" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="c2AreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6FB7D6" stopOpacity={0.14} />
                <stop offset="90%" stopColor="#6FB7D6" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="rgba(131, 127, 120, 0.12)"
            />

            <XAxis
              dataKey="date"
              stroke="#4D524B"
              tick={{ fill: '#837F78', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(131, 127, 120, 0.2)' }}
              dy={10}
              interval="preserveStartEnd"
              minTickGap={28}
            />

            <YAxis
              stroke="#4D524B"
              tick={{ fill: '#837F78', fontSize: 11, fontFamily: 'JetBrains Mono' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(val) => (isRebased ? `${val}` : `₹${val}`)}
              dx={-5}
              width={56}
            />

            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: 'rgba(206, 26, 30, 0.45)',
                strokeWidth: 1,
                strokeDasharray: '4 4',
              }}
            />

            {showCompany1 && (
              <Area
                type="monotone"
                dataKey={isRebased ? 'c1Rebased' : 'c1Price'}
                stroke="#C9A96A"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#c1AreaGrad)"
                name={company1Symbol}
                connectNulls
                isAnimationActive={!reducedMotion}
                animationDuration={900}
                animationEasing="ease-out"
              />
            )}

            {showCompany1 && showMA && (
              <Line
                type="monotone"
                dataKey={
                  isRebased
                    ? (d: ChartDataPoint) => rebase(d.c1MA, c1Base)
                    : 'c1MA'
                }
                stroke="#C9A96A"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                name={`${company1Symbol} 3M MA`}
                isAnimationActive={!reducedMotion}
                animationDuration={1100}
                animationEasing="ease-out"
              />
            )}

            {showCompany2 && (
              <Area
                type="monotone"
                dataKey={isRebased ? 'c2Rebased' : 'c2Price'}
                stroke="#6FB7D6"
                strokeWidth={1.5}
                fillOpacity={1}
                fill="url(#c2AreaGrad)"
                name={company2Symbol}
                connectNulls
                isAnimationActive={!reducedMotion}
                animationDuration={900}
                animationEasing="ease-out"
              />
            )}

            {showCompany2 && showMA && (
              <Line
                type="monotone"
                dataKey={
                  isRebased
                    ? (d: ChartDataPoint) => rebase(d.c2MA, c2Base)
                    : 'c2MA'
                }
                stroke="#6FB7D6"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
                name={`${company2Symbol} 3M MA`}
                isAnimationActive={!reducedMotion}
                animationDuration={1100}
                animationEasing="ease-out"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Visually-hidden text alternative for screen readers */}
      <p className="sr-only">{textSummary}</p>
    </figure>
  );
};

export const TerminalChart = React.memo(TerminalChartView);
