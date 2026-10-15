import React, { useRef, KeyboardEvent } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface TabItem {
  id: string;
  label: string;
  count?: number | string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  variant?: 'underline' | 'pill';
  size?: 'sm' | 'md';
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  variant = 'underline',
  size = 'md',
  className,
}) => {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
    const enabledIndices = tabs
      .map((t, idx) => (!t.disabled ? idx : null))
      .filter((idx): idx is number => idx !== null);

    const pos = enabledIndices.indexOf(currentIndex);
    let nextIndex = currentIndex;

    if (e.key === 'ArrowRight') {
      e.preventDefault();
      nextIndex = enabledIndices[(pos + 1) % enabledIndices.length];
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      nextIndex = enabledIndices[(pos - 1 + enabledIndices.length) % enabledIndices.length];
    } else if (e.key === 'Home') {
      e.preventDefault();
      nextIndex = enabledIndices[0];
    } else if (e.key === 'End') {
      e.preventDefault();
      nextIndex = enabledIndices[enabledIndices.length - 1];
    }

    if (nextIndex !== currentIndex) {
      onChange(tabs[nextIndex].id);
      tabRefs.current[nextIndex]?.focus();
    }
  };

  return (
    <div
      role="tablist"
      aria-orientation="horizontal"
      className={twMerge(
        clsx(
          'flex items-center gap-1 font-sans',
          variant === 'underline' && 'border-b border-editorial-hairline pb-0',
          variant === 'pill' && 'p-1 bg-surface-card border border-editorial-hairline rounded-lg',
          className
        )
      )}
    >
      {tabs.map((tab, idx) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            ref={(el) => (tabRefs.current[idx] = el)}
            role="tab"
            aria-selected={isActive}
            disabled={tab.disabled}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(tab.id)}
            onKeyDown={(e) => handleKeyDown(e, idx)}
            className={clsx(
              'relative flex items-center gap-2 font-medium transition-all duration-200 cursor-pointer select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pepper rounded-md',
              size === 'sm' ? 'px-3 py-1.5 text-xs' : 'px-4 py-2 text-sm',
              variant === 'underline' && [
                'border-b-2 -mb-[2px] transition-colors',
                isActive
                  ? 'border-pepper text-editorial-primary font-semibold'
                  : 'border-transparent text-editorial-secondary hover:text-editorial-primary hover:border-editorial-hairline',
              ],
              variant === 'pill' && [
                isActive
                  ? 'bg-surface-raised text-editorial-primary shadow-sm border border-editorial-hairline/80 font-semibold'
                  : 'text-editorial-secondary hover:text-editorial-primary hover:bg-surface-subtle border border-transparent',
              ],
              tab.disabled && 'opacity-40 cursor-not-allowed pointer-events-none'
            )}
          >
            {tab.icon && <span className="shrink-0">{tab.icon}</span>}
            <span>{tab.label}</span>

            {tab.count !== undefined && (
              <span
                className={clsx(
                  'text-[10px] font-mono px-1.5 py-0.2 rounded-full border',
                  isActive
                    ? 'bg-pepper/20 text-pepper border-pepper/30 font-bold'
                    : 'bg-surface-raised text-editorial-muted border-editorial-hairline'
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
