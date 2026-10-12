import React from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { useCountUp } from './useCountUp';

export interface MetricCardProps {
  label: string;
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  delta?: number; // e.g. 14.8 or -5.2
  deltaPeriod?: string; // e.g. 'vs benchmark' or '2-year change'
  deltaLabel?: string; // e.g. 'GAIN' or 'LOSS'
  sparklineData?: number[];
  accent?: 'gain' | 'loss' | 'neutral' | 'company1' | 'company2';
  tooltipText?: string;
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  prefix = '',
  suffix = '',
  decimals = 2,
  delta,
  deltaPeriod = '2-yr span',
  deltaLabel,
  sparklineData = [12, 14, 13, 16, 15, 18, 22, 20, 24, 28, 27, 31],
  accent,
  tooltipText,
  className,
}) => {
  const { formatted } = useCountUp({
    end: value,
    duration: 800,
    decimals,
    prefix,
    suffix,
  });

  // Determine semantic delta direction
  const isPositive = delta !== undefined && delta > 0;
  const isNegative = delta !== undefined && delta < 0;
  const isNeutral = delta !== undefined && delta === 0;

  const defaultDeltaLabel = isPositive ? 'GAIN' : isNegative ? 'LOSS' : 'NEUTRAL';
  const effectiveDeltaLabel = deltaLabel || defaultDeltaLabel;

  // Render SVG Sparkline
  const renderSparkline = () => {
    if (!sparklineData || sparklineData.length < 2) return null;

    const width = 110;
    const height = 36;
    const padding = 3;

    const min = Math.min(...sparklineData);
    const max = Math.max(...sparklineData);
    const range = max - min || 1;

    const points = sparklineData.map((val, idx) => {
      const x = padding + (idx / (sparklineData.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((val - min) / range) * (height - 2 * padding);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });

    const pathD = `M ${points.join(' L ')}`;
    const areaD = `${pathD} L ${width - padding},${height} L ${padding},${height} Z`;

    // Stroke color based on delta or accent
    const strokeColor =
      accent === 'company1'
        ? '#C9A96A'
        : accent === 'company2'
        ? '#6FB7D6'
        : isNegative
        ? '#FF5A4D'
        : '#2FD08A';

    const gradientId = `sparkline-grad-${label.replace(/[^a-zA-Z0-9]/g, '-')}`;

    return (
      <div className="relative w-[110px] h-[36px] shrink-0">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={strokeColor} stopOpacity={0.25} />
              <stop offset="100%" stopColor={strokeColor} stopOpacity={0.0} />
            </linearGradient>
          </defs>
          <path d={areaD} fill={`url(#${gradientId})`} />
          <path
            d={pathD}
            fill="none"
            stroke={strokeColor}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Terminal dot */}
          {points.length > 0 && (
            <circle
              cx={points[points.length - 1].split(',')[0]}
              cy={points[points.length - 1].split(',')[1]}
              r="2"
              fill={strokeColor}
            />
          )}
        </svg>
      </div>
    );
  };

  return (
    <div
      className={twMerge(
        clsx(
          'relative p-5 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline transition-all duration-300 hover:border-editorial-subtle group',
          className
        )
      )}
    >
      {/* Top row: Label & Tooltip/Info */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-mono uppercase tracking-wider text-editorial-secondary font-medium">
          {label}
        </span>
        {tooltipText && (
          <div className="relative group/info cursor-help" title={tooltipText}>
            <Info className="w-3.5 h-3.5 text-editorial-muted group-hover/info:text-editorial-secondary transition-colors" />
          </div>
        )}
      </div>

      {/* Middle row: Big Mono Metric Number */}
      <div className="flex items-baseline justify-between gap-4 my-1">
        <div className="font-mono text-3xl sm:text-4xl font-semibold tracking-tight text-editorial-primary font-tabular">
          {formatted}
        </div>
        {renderSparkline()}
      </div>

      {/* Bottom row: Semantic Delta Pill + Period */}
      {delta !== undefined && (
        <div className="mt-3 pt-2.5 border-t border-editorial-hairline/60 flex items-center justify-between text-xs font-mono">
          <div
            className={clsx(
              'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold border',
              isPositive && 'bg-gain/10 text-gain border-gain/20',
              isNegative && 'bg-loss/10 text-loss border-loss/20',
              isNeutral && 'bg-gold/10 text-gold border-gold/20'
            )}
          >
            {isPositive && <TrendingUp className="w-3 h-3 stroke-[2.5]" />}
            {isNegative && <TrendingDown className="w-3 h-3 stroke-[2.5]" />}
            {isNeutral && <Minus className="w-3 h-3 stroke-[2.5]" />}
            <span>
              {isPositive ? '+' : ''}
              {delta.toFixed(2)}%
            </span>
            <span className="opacity-75 tracking-wider text-[10px] uppercase font-bold">
              {effectiveDeltaLabel}
            </span>
          </div>

          <span className="text-[11px] text-editorial-muted truncate font-sans">
            {deltaPeriod}
          </span>
        </div>
      )}
    </div>
  );
};
