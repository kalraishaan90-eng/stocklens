import React, { useState, useRef, ReactNode, useId } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delayMs?: number;
  className?: string;
}

export const Tooltip: React.FC<TooltipProps> = ({
  content,
  children,
  position = 'top',
  delayMs = 150,
  className,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const timeoutRef = useRef<number | null>(null);
  const tooltipId = useId();

  const show = () => {
    timeoutRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delayMs);
  };

  const hide = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    setIsVisible(false);
  };

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }[position];

  return (
    <div
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      <div aria-describedby={isVisible ? tooltipId : undefined}>{children}</div>

      {isVisible && (
        <div
          id={tooltipId}
          role="tooltip"
          className={twMerge(
            clsx(
              'absolute z-50 px-2.5 py-1.5 rounded-md bg-surface-raised border border-editorial-hairline text-editorial-primary text-xs font-sans shadow-2xl pointer-events-none whitespace-normal min-w-[120px] max-w-xs animate-fadeIn backdrop-blur-md',
              positionClasses,
              className
            )
          )}
        >
          {content}
        </div>
      )}
    </div>
  );
};
