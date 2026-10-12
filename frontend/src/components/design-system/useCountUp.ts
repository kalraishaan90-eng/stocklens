import { useState, useEffect } from 'react';

interface UseCountUpOptions {
  end: number;
  start?: number;
  duration?: number; // ms
  decimals?: number;
  prefix?: string;
  suffix?: string;
}

export function useCountUp({
  end,
  start = 0,
  duration = 900,
  decimals = 2,
  prefix = '',
  suffix = '',
}: UseCountUpOptions) {
  const [value, setValue] = useState(start);

  useEffect(() => {
    // Check for prefers-reduced-motion
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setValue(end);
      return;
    }

    let startTime: number | null = null;
    let frameId: number;

    const easeOutCubic = (x: number): number => {
      return 1 - Math.pow(1 - x, 3);
    };

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      const easedProgress = easeOutCubic(progress);
      const current = start + (end - start) * easedProgress;

      setValue(current);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      } else {
        setValue(end);
      }
    };

    frameId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [end, start, duration]);

  const formatted = `${prefix}${value.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}${suffix}`;

  return { value, formatted };
}
