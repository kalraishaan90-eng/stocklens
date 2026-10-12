import React, { useState } from 'react';
import { ShieldAlert, ChevronDown, ChevronUp, Scale } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface DisclaimerBarProps {
  summary?: string;
  fullText?: string;
  sourceAttribution?: string;
  className?: string;
}

export const DisclaimerBar: React.FC<DisclaimerBarProps> = ({
  summary = 'Quantitative research platform. Not financial advice. Past stock performance does not assure future market returns.',
  fullText = 'StockLens is constructed for computational equity analysis, research demonstrations, and algorithmic study. All figures, correlations, volatility metrics, and moving averages are generated from live market data sets. Real news citations are attributed algorithmically without endorsement of causal liability. Users must consult registered investment advisors (SEBI/SEC) before executing financial capital allocations.',
  sourceAttribution = 'Data Feeds: Live Market Feeds via Yahoo Finance / Corporate-Adjusted OHLCV • Modeling Engine: StockLens Quant v1.4',
  className,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div
      role="contentinfo"
      className={twMerge(
        clsx(
          'w-full rounded-lg bg-surface-card/90 border border-editorial-hairline px-4 py-3 text-xs transition-all duration-200',
          className
        )
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-5 h-5 rounded bg-gold/10 border border-gold/30 flex items-center justify-center shrink-0 text-gold">
            <Scale className="w-3 h-3" />
          </div>

          <p className="text-editorial-secondary font-sans truncate text-xs">
            <strong className="text-gold font-medium font-mono uppercase tracking-wider mr-1.5">
              Notice:
            </strong>
            {summary}
          </p>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="inline-flex items-center gap-1 text-[11px] font-mono text-gold hover:text-gold-light shrink-0 transition-colors cursor-pointer select-none"
        >
          <span>{isExpanded ? 'Less' : 'Legal Disclosure'}</span>
          {isExpanded ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3 pt-3 border-t border-editorial-hairline space-y-2 text-[11px] text-editorial-secondary font-sans leading-relaxed animate-fadeIn">
          <p>{fullText}</p>
          <div className="font-mono text-[10px] text-editorial-muted pt-1 flex items-center gap-2">
            <ShieldAlert className="w-3 h-3 text-gold" />
            <span>{sourceAttribution}</span>
          </div>
        </div>
      )}
    </div>
  );
};
