import React, { ButtonHTMLAttributes, forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'outline' | 'champagne' | 'cyan';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    // Base editorial styling: crisp hairline borders, 8px grid alignment, max 12px radius, smooth 200ms ease-out
    const baseStyles =
      'inline-flex items-center justify-center font-medium font-sans select-none tracking-tight transition-all duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-base disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98]';

    const sizes = {
      sm: 'text-xs px-3 py-1.5 rounded-md gap-1.5 h-8',
      md: 'text-sm px-4 py-2 rounded-lg gap-2 h-10',
      lg: 'text-base px-6 py-2.5 rounded-xl gap-2.5 h-12',
    };

    const variants = {
      // Primary: High-contrast luxury warm off-white surface with deep near-black text
      primary:
        'bg-editorial-primary text-base font-semibold hover:bg-white hover:shadow-hairline shadow-sm border border-editorial-primary/20',
      // Ghost: Near-invisible rest state with hairline border revealing on hover
      ghost:
        'bg-transparent text-editorial-secondary hover:text-editorial-primary hover:bg-surface-raised border border-transparent hover:border-editorial-hairline',
      // Outline: Deliberate editorial wireframe with hairline border
      outline:
        'bg-surface-card text-editorial-primary border border-editorial-hairline hover:border-editorial-subtle hover:bg-surface-raised shadow-hairline-sm',
      // Champagne Gold Accent (Company 1 / Neutral Highlight)
      champagne:
        'bg-gold text-base font-semibold hover:bg-gold-light border border-gold/40 shadow-glow-gold',
      // Steel Cyan Accent (Company 2)
      cyan:
        'bg-cyan text-base font-semibold hover:bg-cyan-light border border-cyan/40 shadow-glow-cyan',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={twMerge(clsx(baseStyles, sizes[size], variants[variant], className))}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 animate-spin text-current shrink-0" />
        ) : (
          leftIcon && <span className="shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && <span className="shrink-0">{rightIcon}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
