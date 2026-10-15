import React, { Suspense, lazy, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Home } from './pages/Home';
const Analysis = lazy(() => import('./pages/Analysis').then((module) => ({ default: module.Analysis })));
const Report = lazy(() => import('./pages/Report').then((module) => ({ default: module.Report })));
const About = lazy(() => import('./pages/About').then((module) => ({ default: module.About })));
const DesignSystemShowcase = lazy(() => import('./components/design-system/DesignSystemShowcase').then((module) => ({ default: module.DesignSystemShowcase })));

export function App() {
  return (
    <BrowserRouter>
      <StockLensApp />
    </BrowserRouter>
  );
}

function StockLensApp() {
  const location = useLocation();
  const navigate = useNavigate();
  const kiosk = new URLSearchParams(location.search).get('kiosk') === '1';

  useEffect(() => {
    if (location.pathname !== '/analysis' && document.body.classList.contains('presenter-mode')) {
      document.body.classList.remove('presenter-mode');
      window.dispatchEvent(new CustomEvent('stocklens:presenter-mode', { detail: false }));
    }
  }, [location.pathname]);

  useEffect(() => {
    document.body.classList.toggle('kiosk-mode', kiosk);
    if (!kiosk) return;
    let timeout: number;
    const reset = () => {
      window.clearTimeout(timeout);
      timeout = window.setTimeout(() => { void navigate('/'); }, 90000);
    };
    ['pointerdown', 'pointermove', 'keydown', 'touchstart', 'wheel'].forEach((event) =>
      window.addEventListener(event, reset, { passive: true })
    );
    reset();
    return () => {
      window.clearTimeout(timeout);
      ['pointerdown', 'pointermove', 'keydown', 'touchstart', 'wheel'].forEach((event) => window.removeEventListener(event, reset));
      document.body.classList.remove('kiosk-mode');
    };
  }, [kiosk, navigate]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = !!target?.closest('input, textarea, select, [contenteditable="true"]');
      if (!typing && event.key.toLowerCase() === 'p' && !event.ctrlKey && !event.metaKey && location.pathname === '/analysis') {
        const enabled = !document.body.classList.contains('presenter-mode');
        document.body.classList.toggle('presenter-mode', enabled);
        window.dispatchEvent(new CustomEvent('stocklens:presenter-mode', { detail: enabled }));
      }
      if (event.key === 'Escape' && document.body.classList.contains('presenter-mode')) {
        document.body.classList.remove('presenter-mode');
        window.dispatchEvent(new CustomEvent('stocklens:presenter-mode', { detail: false }));
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-base text-editorial-primary flex flex-col font-sans film-grain-overlay">
      <Navbar />
      <div className="flex-1">
        <Suspense fallback={<div className="min-h-[40vh] grid place-items-center text-sm text-editorial-muted">Loading section</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/analysis" element={<Analysis />} />
            <Route path="/report" element={<Report />} />
            <Route path="/about" element={<About />} />
            <Route path="/design-system" element={<DesignSystemShowcase />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}

export default App;
