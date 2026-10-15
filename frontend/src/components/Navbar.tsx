import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Activity, BarChart2, FileText, Info, ShieldCheck, AlertCircle } from 'lucide-react';
import { checkHealth } from '../lib/api';
import { HealthResponse } from '../lib/types';

const NAV_LINKS = [
  { to: '/', label: 'Home', icon: Activity },
  { to: '/analysis', label: 'Analysis', icon: BarChart2 },
  { to: '/report', label: 'Report', icon: FileText },
  { to: '/about', label: 'About', icon: Info },
];

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchHealth = async () => {
    try {
      const res = await checkHealth();
      setHealth(res);
      setHealthError(false);
    } catch {
      setHealthError(true);
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const getActivePair = () => {
    try {
      const p = JSON.parse(localStorage.getItem('stocklens.active_pair') || '{}');
      if (p.c1 && p.c2) return p;
    } catch {
      // ignore
    }
    return null;
  };
  const activePair = getActivePair();

  const resolveNavUrl = (to: string) => {
    if (activePair) {
      if (to === '/analysis') return `/analysis?c1=${encodeURIComponent(activePair.c1)}&c2=${encodeURIComponent(activePair.c2)}&demo=${Boolean(activePair.demo)}`;
      if (to === '/report') return `/report?c1=${encodeURIComponent(activePair.c1)}&c2=${encodeURIComponent(activePair.c2)}&demo=${Boolean(activePair.demo)}`;
    }
    return to;
  };

  return (
    <header className="sticky top-0 z-50 bg-base/95 backdrop-blur-md border-b border-editorial-hairline text-editorial-primary">
      <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2">
        {/* Brand */}
        <Link
          to="/"
          className="flex items-center gap-2 sm:gap-3 group shrink-0"
          aria-label="StockLens home"
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-md bg-pepper/15 border border-pepper/35 flex items-center justify-center text-pepper group-hover:bg-pepper/25 transition-colors">
            <BarChart2 className="w-4 h-4 sm:w-5 sm:h-5" aria-hidden="true" />
          </div>
          <div className="leading-tight">
            <span className="font-serif text-lg sm:text-xl tracking-tight text-editorial-primary">
              StockLens
            </span>
            <p className="hidden sm:block text-[11px] text-editorial-muted">
              Dual equity analytics · verified attribution
            </p>
          </div>
        </Link>

        {/* Navigation: labels collapse to icons below sm so 390px never overflows */}
        <nav aria-label="Primary" className="flex items-center gap-0.5 sm:gap-1">
          {NAV_LINKS.map((link) => {
            const Icon = link.icon;
            const targetUrl = resolveNavUrl(link.to);
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={targetUrl}
                aria-current={isActive ? 'page' : undefined}
                className={`flex items-center gap-1.5 px-2 sm:px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-pepper/15 text-pepper border border-pepper/35'
                    : 'text-editorial-secondary hover:text-editorial-primary hover:bg-surface-hover border border-transparent'
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                <span className="hidden md:inline">{link.label}</span>
                <span className="sr-only md:hidden">{link.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Backend Health Badge (retry is a real button: keyboard accessible) */}
        <div className="flex items-center shrink-0">
          {loading ? (
            <span className="text-xs px-2.5 py-1 rounded-full bg-surface-raised text-editorial-muted border border-editorial-hairline animate-pulse">
              Connecting…
            </span>
          ) : healthError ? (
            <button
              type="button"
              onClick={fetchHealth}
              title="Backend offline — click to retry"
              aria-label="Backend offline. Retry health check"
              className="inline-flex items-center gap-1 text-xs px-2 sm:px-2.5 py-1 rounded-full bg-loss-muted text-loss border border-loss-border hover:bg-loss/20 transition-colors"
            >
              <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">Offline</span>
            </button>
          ) : (
            <span
              title={`API: ${health?.service} v${health?.version}`}
              className="inline-flex items-center gap-1.5 text-xs px-2 sm:px-2.5 py-1 rounded-full bg-gain-muted text-gain border border-gain-border"
            >
              <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden sm:inline">API OK</span>
            </span>
          )}
        </div>
      </div>
    </header>
  );
};
