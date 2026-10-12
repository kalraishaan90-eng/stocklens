import React, { ReactNode } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface SectionHeaderProps {
  number: string | number; // e.g. "01" or 1
  title: string;
  subtitle?: string;
  action?: ReactNode;
  align?: 'left' | 'center';
  className?: string;
}

export const SectionHeader: React.FC<SectionHeaderProps> = ({
  number,
  title,
  subtitle,
  action,
  align = 'left',
  className,
}) => {
  const formattedNumber = typeof number === 'number' ? String(number).padStart(2, '0') : number;

  return (
    <div
      className={twMerge(
        clsx(
          'w-full flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-4 border-b border-editorial-hairline/80 font-sans',
          align === 'center' && 'items-center text-center',
          className
        )
      )}
    >
      <div className="space-y-1.5 max-w-2xl">
        {/* Numbered Eyebrow */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-gold tracking-widest uppercase px-2 py-0.5 rounded bg-gold/10 border border-gold/25">
            {formattedNumber}
          </span>
          <span className="h-[1px] w-6 bg-gold/30" />
        </div>

        {/* Display Serif Title (36-48px scale) */}
        <h2 className="font-serif text-3xl sm:text-4xl lg:text-[42px] font-normal text-editorial-primary tracking-tight leading-[1.15]">
          {title}
        </h2>

        {/* Subtitle */}
        {subtitle && (
          <p className="text-sm text-editorial-secondary font-sans leading-relaxed pt-1">
            {subtitle}
          </p>
        )}
      </div>

      {/* Right Side Slot */}
      {action && <div className="shrink-0 flex items-center gap-3">{action}</div>}
    </div>
  );
};
