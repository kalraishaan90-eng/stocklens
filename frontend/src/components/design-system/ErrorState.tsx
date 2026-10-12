import React, { useState } from 'react';
import { AlertCircle, RefreshCw, ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Button } from './Button';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  technicalDetails?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
  onLaunchOffline?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Analysis Interruption Encountered',
  message = 'Unable to establish a low-latency connection to the exchange feed or historical database. This can happen if upstream market APIs are throttling requests.',
  technicalDetails,
  onRetry,
  isRetrying = false,
  onLaunchOffline,
  className,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div
      role="alert"
      className={twMerge(
        clsx(
          'p-8 rounded-card bg-surface-card border border-loss/30 shadow-hairline relative overflow-hidden',
          className
        )
      )}
    >
      {/* Top Warning Strip */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-xl bg-loss/10 border border-loss/30 flex items-center justify-center shrink-0 text-loss shadow-sm">
          <AlertCircle className="w-6 h-6 stroke-[2]" />
        </div>

        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-loss bg-loss/10 px-2 py-0.5 rounded border border-loss/20">
              Diagnostic Fault
            </span>
          </div>

          <h3 className="font-serif text-xl font-normal text-editorial-primary tracking-tight">
            {title}
          </h3>

          <p className="text-sm text-editorial-secondary font-sans leading-relaxed max-w-2xl">
            {message}
          </p>

          {/* Action Row */}
          <div className="pt-3 flex flex-wrap items-center gap-3">
            {onRetry && (
              <Button
                variant="primary"
                size="sm"
                onClick={onRetry}
                isLoading={isRetrying}
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              >
                Retry Analysis
              </Button>
            )}

            {onLaunchOffline && (
              <Button
                variant="outline"
                size="sm"
                onClick={onLaunchOffline}
              >
                Switch to Offline Demo Mode
              </Button>
            )}

            {technicalDetails && (
              <button
                type="button"
                onClick={() => setShowDetails(!showDetails)}
                className="inline-flex items-center gap-1 text-xs font-mono text-editorial-muted hover:text-editorial-secondary transition-colors ml-auto cursor-pointer"
              >
                <Terminal className="w-3.5 h-3.5" />
                <span>{showDetails ? 'Hide Diagnostics' : 'Inspect Stack'}</span>
                {showDetails ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            )}
          </div>

          {/* Technical Diagnostics Drawer */}
          {showDetails && technicalDetails && (
            <div className="mt-4 p-3.5 rounded-lg bg-base border border-editorial-hairline text-[11px] font-mono text-loss-light overflow-x-auto whitespace-pre-wrap leading-relaxed animate-fadeIn">
              {technicalDetails}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
