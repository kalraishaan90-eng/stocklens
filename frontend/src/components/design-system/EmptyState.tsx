import React, { ReactNode } from 'react';
import { Layers, Compass } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Button } from './Button';

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  action?: ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Comparative Data Loaded',
  description = 'Select two equities using the search inputs above to initiate head-to-head volatility, moving average, and news-driven catalyst attribution.',
  icon,
  actionLabel,
  onAction,
  action,
  className,
}) => {
  return (
    <div
      className={twMerge(
        clsx(
          'flex flex-col items-center justify-center p-12 text-center rounded-card bg-surface-card border border-editorial-hairline shadow-hairline relative overflow-hidden',
          className
        )
      )}
    >
      {/* Subtle background ambient ring */}
      <div className="absolute w-72 h-72 rounded-full bg-gold/[0.02] border border-gold/[0.05] pointer-events-none -top-12 -right-12" />

      {/* Glyph / Icon Container */}
      <div className="w-16 h-16 rounded-2xl bg-surface-raised border border-editorial-hairline flex items-center justify-center mb-6 shadow-inner text-editorial-secondary relative">
        <div className="absolute inset-0 rounded-2xl bg-gold/[0.04] pointer-events-none" />
        {icon ? (
          icon
        ) : (
          <div className="relative">
            <Layers className="w-7 h-7 text-gold stroke-[1.5]" />
            <Compass className="w-4 h-4 text-editorial-muted absolute -bottom-1 -right-1" />
          </div>
        )}
      </div>

      {/* Serif Title & Editorial Copy */}
      <h3 className="font-serif text-2xl font-normal text-editorial-primary tracking-tight max-w-md mb-2">
        {title}
      </h3>

      <p className="text-sm text-editorial-secondary font-sans max-w-lg leading-relaxed mb-6">
        {description}
      </p>

      {/* Action CTA */}
      {action ? (
        action
      ) : actionLabel && onAction ? (
        <Button variant="primary" onClick={onAction}>
          {actionLabel}
        </Button>
      ) : null}
    </div>
  );
};
