import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(val: number, currency: string = 'INR'): string {
  const symbol = currency === 'INR' ? '₹' : '$';
  return `${symbol}${val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPct(val: number, includeSign: boolean = false): string {
  const sign = includeSign && val > 0 ? '+' : '';
  return `${sign}${val.toFixed(2)}%`;
}

/** Signed percent for metrics: '+7.3%' / '-4.2%' (never '+-4.2%'). */
export function fmtPctSigned(val: number, decimals: number = 1): string {
  if (!Number.isFinite(val)) return '—';
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(decimals)}%`;
}

export function formatNum(val: number, decimals: number = 2): string {
  return val.toFixed(decimals);
}
