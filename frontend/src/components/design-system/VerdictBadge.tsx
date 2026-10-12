import React from 'react';
import { ChevronsUp, Scale, AlertOctagon, TrendingUp, Minus, AlertTriangle } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export type VerdictType = 'BUY' | 'HOLD' | 'AVOID';

export interface VerdictBadgeProps {
  verdict: VerdictType;
  size?: 'sm' | 'md' | 'lg';
  confidence?: number; // 0 to 100
  rationale?: string;
  className?: string;
}

export const VerdictBadge: React.FC<VerdictBadgeProps> = ({
  verdict,
  size = 'md',
  confidence,
  rationale,
  className,
}) => {
  const configs = {
    BUY: {
      label: 'BUY / ACCUMULATE',
      shortLabel: 'BUY',
      colorText: 'text-gain',
      colorBg: 'bg-gain/10',
      colorBorder: 'border-gain/40',
      borderStyle: 'border-solid',
      Icon: ChevronsUp,
      secondaryIcon: TrendingUp,
      // Distinct geometry: chamfered/angled right flag shape or crisp sharp-edged pill
      shapeClass: 'rounded-l-lg rounded-r-[2px]',
      badgeAccent: 'bg-gain text-base',
      shapeDescription: 'Pointed Shield Pill (Solid Edge)',
    },
    HOLD: {
      label: 'HOLD / NEUTRAL',
      shortLabel: 'HOLD',
      colorText: 'text-gold',
      colorBg: 'bg-gold/10',
      colorBorder: 'border-gold/40',
      borderStyle: 'border-dashed',
      Icon: Scale,
      secondaryIcon: Minus,
      // Symmetrical classic rectangular pill with rounded corners
      shapeClass: 'rounded-md',
      badgeAccent: 'bg-gold text-base',
      shapeDescription: 'Dashed Outline Rectangular Pill',
    },
    AVOID: {
      label: 'AVOID / TRIM',
      shortLabel: 'AVOID',
      colorText: 'text-loss',
      colorBg: 'bg-loss/10',
      colorBorder: 'border-loss/40',
      borderStyle: 'border-solid',
      Icon: AlertOctagon,
      secondaryIcon: AlertTriangle,
      // Distinct geometry: faceted corner / octagonal slanted bevel
      shapeClass: 'rounded-none border-l-4 border-l-loss',
      badgeAccent: 'bg-loss text-white',
      shapeDescription: 'Faceted Warning Block (Thick Left Anchor)',
    },
  }[verdict];

  const sizeClasses = {
    sm: 'px-2.5 py-1 text-xs gap-1.5',
    md: 'px-3.5 py-1.5 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-3',
  }[size];

  const IconComponent = configs.Icon;

  return (
    <div className={twMerge(clsx('inline-flex flex-col gap-1', className))}>
      <div
        className={clsx(
          'inline-flex items-center font-mono font-bold tracking-wider uppercase border transition-all duration-200 select-none shadow-sm',
          configs.colorText,
          configs.colorBg,
          configs.colorBorder,
          configs.borderStyle,
          configs.shapeClass,
          sizeClasses
        )}
      >
        <span className="shrink-0">
          <IconComponent
            className={clsx(
              'stroke-[2.5]',
              size === 'sm' ? 'w-3.5 h-3.5' : size === 'md' ? 'w-4 h-4' : 'w-5 h-5'
            )}
          />
        </span>
        <span className="font-mono tracking-widest">{configs.label}</span>

        {confidence !== undefined && (
          <span className="ml-1 text-[11px] px-1.5 py-0.2 rounded bg-surface-base/80 text-editorial-secondary font-mono border border-editorial-hairline font-normal">
            {confidence}% CONF
          </span>
        )}
      </div>

      {rationale && (
        <span className="text-xs text-editorial-secondary font-sans italic max-w-xs px-1">
          {rationale}
        </span>
      )}
    </div>
  );
};
