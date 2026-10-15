import React, { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { ShieldCheck, Award, AlertTriangle } from 'lucide-react';

export interface ScoreRingProps {
  score: number; // 0 to 100
  size?: number; // diameter in px
  strokeWidth?: number;
  label?: string;
  sublabel?: string;
  accent?: 'auto' | 'gold' | 'cyan' | 'gain' | 'loss';
  showTier?: boolean;
  className?: string;
}

export const ScoreRing: React.FC<ScoreRingProps> = ({
  score,
  size = 140,
  strokeWidth = 9,
  label = 'Overall Score',
  sublabel,
  accent = 'auto',
  showTier = true,
  className,
}) => {
  const [animatedScore, setAnimatedScore] = useState(0);

  // Normalize score between 0 and 100
  const clampedScore = Math.max(0, Math.min(100, score));

  useEffect(() => {
    // Respect prefers-reduced-motion
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setAnimatedScore(clampedScore);
      return;
    }

    const timer = setTimeout(() => {
      setAnimatedScore(clampedScore);
    }, 100);
    return () => clearTimeout(timer);
  }, [clampedScore]);

  // Radius and circumference
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  // Determine accent color and tier
  let resolvedColor = '#C9A96A'; // default gold
  let tierLabel = 'BALANCED';
  let TierIcon = Award;

  if (accent === 'auto') {
    if (clampedScore >= 70) {
      resolvedColor = '#2FD08A'; // emerald
      tierLabel = 'OUTPERFORM';
      TierIcon = ShieldCheck;
    } else if (clampedScore >= 45) {
      resolvedColor = '#C9A96A'; // gold
      tierLabel = 'BALANCED';
      TierIcon = Award;
    } else {
      resolvedColor = '#CE1A1E'; // Thunder Mountain Longhorn Pepper
      tierLabel = 'UNDERPERFORM';
      TierIcon = AlertTriangle;
    }
  } else if (accent === 'gold') {
    resolvedColor = '#C9A96A';
    tierLabel = clampedScore >= 50 ? 'ADVANTAGE' : 'STABLE';
    TierIcon = Award;
  } else if (accent === 'cyan') {
    resolvedColor = '#6FB7D6';
    tierLabel = clampedScore >= 50 ? 'ADVANTAGE' : 'STABLE';
    TierIcon = Award;
  } else if (accent === 'gain') {
    resolvedColor = '#2FD08A';
    tierLabel = 'SUPERIOR';
    TierIcon = ShieldCheck;
  } else if (accent === 'loss') {
    resolvedColor = '#CE1A1E';
    tierLabel = 'DEFICIT';
    TierIcon = AlertTriangle;
  }

  const ringGradId = `score-ring-grad-${Math.round(score)}-${size}`;

  return (
    <div
      className={twMerge(
        clsx(
          'flex flex-col items-center justify-center p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline relative',
          className
        )
      )}
    >
      {/* SVG Ring Gauge */}
      <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className="transform -rotate-90 origin-center"
        >
          <defs>
            <linearGradient id={ringGradId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={resolvedColor} stopOpacity="0.7" />
              <stop offset="100%" stopColor={resolvedColor} stopOpacity="1" />
            </linearGradient>
          </defs>

          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth={strokeWidth}
          />

          {/* Animated score indicator */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="transparent"
            stroke={`url(#${ringGradId})`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>

        {/* Center Editorial Typography */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="flex items-baseline">
            <span className="font-mono text-3xl sm:text-4xl font-bold tracking-tight text-editorial-primary font-tabular">
              {Math.round(animatedScore)}
            </span>
            <span className="font-mono text-xs text-editorial-muted ml-0.5">/100</span>
          </div>
          <span className="text-[10px] font-mono uppercase tracking-widest text-editorial-secondary mt-0.5">
            SCORE
          </span>
        </div>
      </div>

      {/* Label and Tier */}
      <div className="mt-4 text-center space-y-1.5">
        <h4 className="text-sm font-semibold text-editorial-primary font-sans">
          {label}
        </h4>
        {sublabel && (
          <p className="text-xs text-editorial-secondary font-sans">{sublabel}</p>
        )}

        {showTier && (
          <div
            className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold border tracking-wider"
            style={{
              color: resolvedColor,
              borderColor: `${resolvedColor}40`,
              backgroundColor: `${resolvedColor}15`,
            }}
          >
            <TierIcon className="w-3 h-3 stroke-[2.5]" />
            <span>{tierLabel}</span>
          </div>
        )}
      </div>
    </div>
  );
};
