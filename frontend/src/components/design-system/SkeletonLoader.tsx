import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'rect' | 'circle' | 'metricCard' | 'chart';
  width?: string | number;
  height?: string | number;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className,
  variant = 'rect',
  width,
  height,
}) => {
  const baseClasses =
    'relative overflow-hidden bg-surface-raised/80 border border-editorial-hairline/50 before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_2s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/[0.04] before:to-transparent';

  const variantClasses = {
    text: 'h-4 rounded w-full my-1',
    rect: 'rounded-lg w-full h-full',
    circle: 'rounded-full shrink-0',
    metricCard: 'h-36 rounded-card w-full p-5',
    chart: 'h-72 rounded-card w-full p-6',
  }[variant];

  const style: React.CSSProperties = {
    width: width !== undefined ? width : undefined,
    height: height !== undefined ? height : undefined,
  };

  if (variant === 'metricCard') {
    return (
      <div
        style={style}
        className={twMerge(clsx(baseClasses, variantClasses, 'flex flex-col justify-between', className))}
      >
        <div className="flex justify-between items-center">
          <div className="w-24 h-3.5 bg-surface-subtle rounded" />
          <div className="w-4 h-4 bg-surface-subtle rounded-full" />
        </div>
        <div className="w-36 h-9 bg-surface-subtle rounded" />
        <div className="flex justify-between items-center pt-2 border-t border-editorial-hairline/40">
          <div className="w-20 h-4 bg-surface-subtle rounded" />
          <div className="w-16 h-3 bg-surface-subtle rounded" />
        </div>
      </div>
    );
  }

  if (variant === 'chart') {
    return (
      <div
        style={style}
        className={twMerge(clsx(baseClasses, variantClasses, 'flex flex-col justify-between', className))}
      >
        <div className="flex justify-between items-center mb-4">
          <div className="space-y-1.5">
            <div className="w-40 h-5 bg-surface-subtle rounded" />
            <div className="w-56 h-3 bg-surface-subtle rounded" />
          </div>
          <div className="w-24 h-7 bg-surface-subtle rounded-lg" />
        </div>
        <div className="flex-1 flex items-end gap-3 pt-6 pb-2">
          {[40, 65, 30, 85, 60, 45, 90, 75, 55, 70, 80, 95].map((h, i) => (
            <div
              key={i}
              className="flex-1 bg-surface-subtle/60 rounded-t"
              style={{ height: `${h}%` }}
            />
          ))}
        </div>
        <div className="flex justify-between pt-2 border-t border-editorial-hairline/40">
          <div className="w-12 h-3 bg-surface-subtle rounded" />
          <div className="w-12 h-3 bg-surface-subtle rounded" />
          <div className="w-12 h-3 bg-surface-subtle rounded" />
          <div className="w-12 h-3 bg-surface-subtle rounded" />
        </div>
      </div>
    );
  }

  return (
    <div
      style={style}
      className={twMerge(clsx(baseClasses, variantClasses, className))}
    />
  );
};
