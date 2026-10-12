import React, { useState } from 'react';
import {
  Button,
  CompanyInput,
  MetricCard,
  ScoreRing,
  VerdictBadge,
  Tabs,
  Tooltip,
  Skeleton,
  EmptyState,
  ErrorState,
  DisclaimerBar,
  SectionHeader,
  TerminalChart,
} from './index';
import { SAMPLE_CHART_DATA } from './TerminalChart';
import {
  ArrowLeft,
  Copy,
  Check,
  Sparkles,
  Sliders,
  ShieldCheck,
  Layers,
  Activity,
  BarChart3,
  ExternalLink,
  Info,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

export const DesignSystemShowcase: React.FC = () => {
  // Navigation / Interactive States
  const [activeTab, setActiveTab] = useState('overview');
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  // Input states
  const [companyA, setCompanyA] = useState('HAL');
  const [companyB, setCompanyB] = useState('MAZDOCK');

  // Interactive Score Ring state
  const [demoScore, setDemoScore] = useState(82);

  // Metrics animation trigger key
  const [metricsKey, setMetricsKey] = useState(0);

  // Error simulation state
  const [isRetrying, setIsRetrying] = useState(false);
  const [showErrorToast, setShowErrorToast] = useState(false);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(id);
    setTimeout(() => setCopiedToken(null), 2000);
  };

  const handleRetrySim = () => {
    setIsRetrying(true);
    setTimeout(() => {
      setIsRetrying(false);
      setShowErrorToast(true);
      setTimeout(() => setShowErrorToast(false), 3000);
    }, 1200);
  };

  return (
    <div className="min-h-screen bg-[#0A0B0D] text-editorial-primary font-sans antialiased selection:bg-gold/25 selection:text-editorial-primary film-grain-overlay relative pb-28">
      {/* Top Fixed Utility Navigation Bar */}
      <header className="sticky top-0 z-40 bg-[#0A0B0D]/90 backdrop-blur-xl border-b border-editorial-hairline px-4 sm:px-8 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <a
            href="/"
            className="inline-flex items-center gap-2 text-xs font-mono text-editorial-secondary hover:text-editorial-primary transition-colors py-1 px-2.5 rounded bg-surface-card border border-editorial-hairline hover:border-editorial-subtle"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Return to App</span>
          </a>
          <span className="h-4 w-[1px] bg-editorial-hairline hidden sm:inline-block" />
          <div className="flex items-center gap-2">
            <span className="font-serif text-lg font-normal tracking-tight text-editorial-primary">
              StockLens
            </span>
            <span className="text-[10px] font-mono uppercase tracking-widest text-gold bg-gold/10 px-2 py-0.5 rounded border border-gold/25 font-bold">
              Design System Spec
            </span>
          </div>
        </div>

        {/* Quick Anchor Jump Links */}
        <nav className="hidden lg:flex items-center gap-4 text-xs font-mono text-editorial-secondary">
          <a href="#typography" className="hover:text-editorial-primary transition-colors">
            01 Type
          </a>
          <a href="#tokens" className="hover:text-editorial-primary transition-colors">
            02 Tokens
          </a>
          <a href="#buttons" className="hover:text-editorial-primary transition-colors">
            03 Controls
          </a>
          <a href="#inputs" className="hover:text-editorial-primary transition-colors">
            04 Inputs
          </a>
          <a href="#metrics" className="hover:text-editorial-primary transition-colors">
            05 Metrics
          </a>
          <a href="#verdicts" className="hover:text-editorial-primary transition-colors">
            06 Verdicts
          </a>
          <a href="#charts" className="hover:text-editorial-primary transition-colors">
            07 Charts
          </a>
          <a href="#states" className="hover:text-editorial-primary transition-colors">
            08 States
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <span className="text-[11px] font-mono text-gain flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-gain/10 border border-gain/20">
            <CheckCircle2 className="w-3 h-3" />
            <span>WCAG AAA Ready</span>
          </span>
        </div>
      </header>

      {/* Hero Showcase Section with Radial Glow */}
      <section className="relative pt-16 pb-20 px-4 sm:px-8 max-w-7xl mx-auto hero-radial-glow overflow-hidden">
        <div className="relative z-10 max-w-4xl space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-card border border-gold/30 text-xs font-mono text-gold shadow-glow-gold">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Editorial Financial Terminal Aesthetic</span>
          </div>

          <h1 className="font-serif text-5xl sm:text-7xl lg:text-hero font-normal tracking-tight text-editorial-primary leading-[1.02]">
            Precision Engineering <br />
            <span className="italic font-light text-editorial-secondary">meets</span> Haute Horlogerie.
          </h1>

          <p className="text-base sm:text-lg text-editorial-secondary font-sans max-w-2xl leading-relaxed">
            Constructed for high-density market comparison without SaaS cliches. Near-black warm
            surfaces (#0A0B0D, #101215), hairline 1px borders, display serifs, tabular numerals,
            and accessible financial semantics.
          </p>

          <div className="pt-2 flex flex-wrap items-center gap-4 text-xs font-mono text-editorial-muted">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-card border border-editorial-hairline">
              <span className="w-2 h-2 rounded-full bg-[#0A0B0D] border border-editorial-hairline" />
              <span>Base #0A0B0D</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-card border border-editorial-hairline">
              <span className="w-2 h-2 rounded-full bg-gold" />
              <span>Co. 1 Champagne #C9A96A</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-card border border-editorial-hairline">
              <span className="w-2 h-2 rounded-full bg-cyan" />
              <span>Co. 2 Steel #6FB7D6</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-card border border-editorial-hairline">
              <span className="w-2 h-2 rounded-full bg-gain" />
              <span>Gain #2FD08A</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-surface-card border border-editorial-hairline">
              <span className="w-2 h-2 rounded-full bg-loss" />
              <span>Loss #FF5A4D</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 space-y-20">
        {/* ========================================================================= */}
        {/* SECTION 01: TYPOGRAPHY & EDITORIAL SCALE */}
        {/* ========================================================================= */}
        <section id="typography" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="01"
            title="Typography & Scale Hierarchy"
            subtitle="Distinct font roles: Display Serif for editorial headlines, Inter for functional UI chrome, JetBrains Mono with tabular numbers for all prices and percentages."
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Display Serif */}
            <div className="p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-4">
              <div className="flex items-center justify-between border-b border-editorial-hairline pb-2">
                <span className="text-xs font-mono text-gold uppercase tracking-wider">
                  Editorial Headline Font
                </span>
                <span className="text-[11px] font-mono text-editorial-muted">Fraunces / Playfair</span>
              </div>
              <div className="space-y-3">
                <div className="font-serif text-4xl text-editorial-primary tracking-tight">
                  Mazagon Dock vs HAL
                </div>
                <div className="font-serif italic text-2xl text-editorial-secondary">
                  Two-year trailing relative returns
                </div>
                <p className="text-xs text-editorial-muted font-mono leading-relaxed pt-2 border-t border-editorial-hairline/60">
                  Applied to hero titles, section headings, and school science fair report verdicts.
                  Tight tracking (-0.03em).
                </p>
              </div>
            </div>

            {/* JetBrains Mono Tabular */}
            <div className="p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-4">
              <div className="flex items-center justify-between border-b border-editorial-hairline pb-2">
                <span className="text-xs font-mono text-gold uppercase tracking-wider">
                  Financial Tabular Mono
                </span>
                <span className="text-[11px] font-mono text-editorial-muted">JetBrains Mono</span>
              </div>
              <div className="space-y-3">
                <div className="font-mono text-3xl font-bold tracking-tight text-editorial-primary font-tabular">
                  ₹4,892.40 <span className="text-gain text-lg font-semibold">+18.42%</span>
                </div>
                <div className="font-mono text-sm text-editorial-secondary space-y-1 font-tabular">
                  <div className="flex justify-between">
                    <span>24-Month CAGR:</span>
                    <span className="text-editorial-primary font-bold">148.62%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Max Drawdown:</span>
                    <span className="text-loss font-bold">-21.30%</span>
                  </div>
                </div>
                <p className="text-xs text-editorial-muted font-mono leading-relaxed pt-2 border-t border-editorial-hairline/60">
                  `font-feature-settings: "tnum" 1` ensures columnar digit alignment without horizontal jitter.
                </p>
              </div>
            </div>

            {/* Inter UI Sans */}
            <div className="p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-4">
              <div className="flex items-center justify-between border-b border-editorial-hairline pb-2">
                <span className="text-xs font-mono text-gold uppercase tracking-wider">
                  Functional Interface Sans
                </span>
                <span className="text-[11px] font-mono text-editorial-muted">Inter</span>
              </div>
              <div className="space-y-2 text-sm text-editorial-secondary leading-relaxed">
                <p className="text-editorial-primary font-medium">
                  High-contrast microcopy, form controls, and table structures.
                </p>
                <p className="text-xs">
                  Engineered with comfortable 1.5 line heights and distinct visual hierarchy for
                  labels, tooltips, and explanatory callouts.
                </p>
                <p className="text-xs text-editorial-muted font-mono pt-4 border-t border-editorial-hairline/60">
                  Sub-pixel anti-aliasing with warm text tinting (#F2F0EB / #9A9A94).
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 02: COLOR TOKENS & WCAG CONTRAST */}
        {/* ========================================================================= */}
        <section id="tokens" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="02"
            title="Design Tokens & WCAG Contrast"
            subtitle="Curated palette avoiding generic SaaS purple gradients. Every primary text and semantic token is verified for WCAG AA / AAA compliance against the near-black background."
          />

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {/* Base */}
            <div
              onClick={() => copyToClipboard('#0A0B0D', 'base')}
              className="group p-4 rounded-card bg-[#0A0B0D] border border-editorial-hairline shadow-hairline cursor-pointer hover:border-gold/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-[#0A0B0D] border border-editorial-hairline mb-3" />
              <div className="text-xs font-mono font-bold text-editorial-primary flex items-center justify-between">
                <span>Base Dark</span>
                {copiedToken === 'base' ? <Check className="w-3 h-3 text-gold" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#0A0B0D</div>
              <div className="text-[10px] font-mono text-editorial-secondary mt-1">Background</div>
            </div>

            {/* Surface */}
            <div
              onClick={() => copyToClipboard('#101215', 'surface')}
              className="group p-4 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline cursor-pointer hover:border-gold/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-surface-card border border-editorial-hairline mb-3" />
              <div className="text-xs font-mono font-bold text-editorial-primary flex items-center justify-between">
                <span>Surface</span>
                {copiedToken === 'surface' ? <Check className="w-3 h-3 text-gold" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#101215</div>
              <div className="text-[10px] font-mono text-editorial-secondary mt-1">Card Containers</div>
            </div>

            {/* Champagne Gold */}
            <div
              onClick={() => copyToClipboard('#C9A96A', 'gold')}
              className="group p-4 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline cursor-pointer hover:border-gold/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-gold mb-3 flex items-center justify-center text-base font-bold text-xs font-mono">
                Co. 1
              </div>
              <div className="text-xs font-mono font-bold text-gold flex items-center justify-between">
                <span>Champagne</span>
                {copiedToken === 'gold' ? <Check className="w-3 h-3 text-gold" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#C9A96A</div>
              <div className="text-[10px] font-mono text-gain mt-1">7.4:1 AAA Pass</div>
            </div>

            {/* Steel Cyan */}
            <div
              onClick={() => copyToClipboard('#6FB7D6', 'cyan')}
              className="group p-4 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline cursor-pointer hover:border-cyan/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-cyan mb-3 flex items-center justify-center text-base font-bold text-xs font-mono">
                Co. 2
              </div>
              <div className="text-xs font-mono font-bold text-cyan flex items-center justify-between">
                <span>Steel Cyan</span>
                {copiedToken === 'cyan' ? <Check className="w-3 h-3 text-cyan" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#6FB7D6</div>
              <div className="text-[10px] font-mono text-gain mt-1">8.8:1 AAA Pass</div>
            </div>

            {/* Refined Emerald Gain */}
            <div
              onClick={() => copyToClipboard('#2FD08A', 'gain')}
              className="group p-4 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline cursor-pointer hover:border-gain/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-gain mb-3 flex items-center justify-center text-base font-bold text-xs font-mono">
                +GAIN
              </div>
              <div className="text-xs font-mono font-bold text-gain flex items-center justify-between">
                <span>Gain Emerald</span>
                {copiedToken === 'gain' ? <Check className="w-3 h-3 text-gain" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#2FD08A</div>
              <div className="text-[10px] font-mono text-gain mt-1">9.1:1 AAA Pass</div>
            </div>

            {/* Muted Vermilion Loss */}
            <div
              onClick={() => copyToClipboard('#FF5A4D', 'loss')}
              className="group p-4 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline cursor-pointer hover:border-loss/40 transition-all"
            >
              <div className="w-full h-12 rounded bg-loss mb-3 flex items-center justify-center text-white font-bold text-xs font-mono">
                -LOSS
              </div>
              <div className="text-xs font-mono font-bold text-loss flex items-center justify-between">
                <span>Loss Vermilion</span>
                {copiedToken === 'loss' ? <Check className="w-3 h-3 text-loss" /> : <Copy className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />}
              </div>
              <div className="text-[11px] font-mono text-editorial-muted">#FF5A4D</div>
              <div className="text-[10px] font-mono text-gain mt-1">6.2:1 AA Pass</div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 03: BUTTONS & INTERACTIVE CONTROLS */}
        {/* ========================================================================= */}
        <section id="buttons" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="03"
            title="Buttons & Interactive Controls"
            subtitle="Tactile luxury interactions. Micro-borders, 200ms ease-out transitions, explicit focus-visible rings in champagne gold, and loading states."
          />

          <div className="p-8 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-8">
            {/* Variants row */}
            <div className="space-y-3">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Button Variants
              </span>
              <div className="flex flex-wrap items-center gap-4">
                <Button variant="primary">Primary Editorial</Button>
                <Button variant="ghost">Ghost Trigger</Button>
                <Button variant="outline">Wireframe Outline</Button>
                <Button variant="champagne">Champagne Accent</Button>
                <Button variant="cyan">Steel Cyan Accent</Button>
              </div>
            </div>

            {/* Sizes & Icons */}
            <div className="space-y-3 border-t border-editorial-hairline pt-6">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Sizes & Icon Integration
              </span>
              <div className="flex flex-wrap items-center gap-4">
                <Button size="sm" leftIcon={<Sparkles className="w-3.5 h-3.5" />}>
                  Small (32px)
                </Button>
                <Button size="md" leftIcon={<BarChart3 className="w-4 h-4" />}>
                  Medium (40px)
                </Button>
                <Button size="lg" rightIcon={<ExternalLink className="w-4 h-4" />}>
                  Large (48px)
                </Button>
                <Button size="md" isLoading>
                  Processing Analysis
                </Button>
                <Button size="md" disabled>
                  Disabled
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 04: COMPANY INPUT WITH AUTOCOMPLETE */}
        {/* ========================================================================= */}
        <section id="inputs" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="04"
            title="Search & Company Autocomplete"
            subtitle="Dual-equity inputs with company ticker chips, keyboard navigation (ArrowUp/Down, Enter), and NSE/BSE stock catalog suggestions."
          />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-8 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline">
            <div className="space-y-4">
              <CompanyInput
                label="Primary Target Equity"
                accent="gold"
                accentNumber={1}
                value={companyA}
                onChange={setCompanyA}
                placeholder="Search symbol (e.g. HAL, RELIANCE, TCS)..."
              />
              <p className="text-xs text-editorial-muted font-mono">
                Assigned Company 1 Champagne Gold palette (#C9A96A). Try typing "BEL" or "TCS".
              </p>
            </div>

            <div className="space-y-4">
              <CompanyInput
                label="Benchmark Comparison Equity"
                accent="cyan"
                accentNumber={2}
                value={companyB}
                onChange={setCompanyB}
                placeholder="Search symbol (e.g. MAZDOCK, INFY, SBIN)..."
              />
              <p className="text-xs text-editorial-muted font-mono">
                Assigned Company 2 Steel Cyan palette (#6FB7D6). Accessible ticker chip with clear trigger.
              </p>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 05: FINANCIAL METRICS & SPARKLINES */}
        {/* ========================================================================= */}
        <section id="metrics" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="05"
            title="Metric Cards & Sparklines"
            subtitle="Tabular monospace numerals, animated count-up effects, semantic delta pills (+GAIN / -LOSS), and tiny SVG area sparklines."
            action={
              <Button
                variant="outline"
                size="sm"
                leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
                onClick={() => setMetricsKey((prev) => prev + 1)}
              >
                Re-animate Numbers
              </Button>
            }
          />

          <div key={metricsKey} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <MetricCard
              label="2-Year Trailing CAGR"
              value={148.65}
              suffix="%"
              decimals={2}
              delta={24.8}
              deltaPeriod="vs benchmark"
              deltaLabel="OUTPERFORM"
              sparklineData={[30, 35, 42, 48, 55, 62, 78, 92, 110, 130, 148]}
              accent="company1"
              tooltipText="Compound Annual Growth Rate across 24 calendar months."
            />

            <MetricCard
              label="Annualized Volatility"
              value={32.4}
              suffix="%"
              decimals={1}
              delta={-6.2}
              deltaPeriod="lower risk"
              deltaLabel="STABLE"
              sparklineData={[48, 45, 42, 40, 38, 36, 35, 34, 33, 32]}
              accent="gain"
              tooltipText="Standard deviation of logarithmic returns annualized."
            />

            <MetricCard
              label="Sharpe Ratio (Risk-Adj)"
              value={2.84}
              decimals={2}
              delta={0.92}
              deltaPeriod="above 1.0 hurdle"
              deltaLabel="EXCEPTIONAL"
              sparklineData={[1.1, 1.4, 1.6, 1.9, 2.1, 2.3, 2.6, 2.84]}
              accent="company2"
              tooltipText="Excess return per unit of total risk relative to risk-free rate."
            />

            <MetricCard
              label="Maximum Peak-to-Trough Drawdown"
              value={-21.3}
              suffix="%"
              decimals={1}
              delta={-4.5}
              deltaPeriod="during Aug '24 correction"
              deltaLabel="DRAWDOWN"
              sparklineData={[-5, -8, -6, -12, -15, -19, -21.3]}
              accent="loss"
              tooltipText="Largest observed percentage loss from peak to subsequent trough."
            />
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 06: VERDICTS & SCORE RINGS */}
        {/* ========================================================================= */}
        <section id="verdicts" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="06"
            title="Score Rings & Verdict Badges"
            subtitle="Strict accessibility requirement: Never rely on colour alone. Each verdict badge combines a distinct geometric shape, distinct iconography, and semantic border line styles (solid vs dashed)."
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Interactive Score Ring */}
            <div className="p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-4">
              <div className="flex items-center justify-between border-b border-editorial-hairline pb-2">
                <span className="text-xs font-mono text-gold uppercase tracking-wider">
                  Animated Score Ring (0-100)
                </span>
                <span className="text-xs font-mono text-editorial-primary font-bold">
                  {demoScore}/100
                </span>
              </div>

              <div className="py-2 flex justify-center">
                <ScoreRing
                  score={demoScore}
                  size={150}
                  label="Algorithmic Health"
                  sublabel="Growth vs Risk Profile"
                />
              </div>

              {/* Slider to interactively test score ring transitions */}
              <div className="pt-2 space-y-1.5 border-t border-editorial-hairline/60">
                <div className="flex justify-between text-[11px] font-mono text-editorial-secondary">
                  <span>Simulate Score:</span>
                  <span>{demoScore}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={demoScore}
                  onChange={(e) => setDemoScore(Number(e.target.value))}
                  className="w-full accent-gold h-1.5 bg-surface-raised rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>

            {/* Distinct Verdict Badges Demonstration */}
            <div className="lg:col-span-2 p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-6">
              <div className="flex items-center justify-between border-b border-editorial-hairline pb-2">
                <span className="text-xs font-mono text-gold uppercase tracking-wider">
                  Shape & Line-Style Differentiated Badges
                </span>
                <span className="text-[11px] font-mono text-gain">Accessible for Daltonism</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {/* BUY */}
                <div className="p-4 rounded-lg bg-surface-raised border border-editorial-hairline space-y-3">
                  <div className="text-[10px] font-mono uppercase text-editorial-muted">
                    Pointed Shield Pill • Solid Border
                  </div>
                  <VerdictBadge
                    verdict="BUY"
                    confidence={88}
                    rationale="High CAGR with steady 3-month moving average support."
                  />
                  <p className="text-[11px] text-editorial-secondary pt-2">
                    Refined Emerald (#2FD08A) + Double Upward Chevron + Solid Hairline.
                  </p>
                </div>

                {/* HOLD */}
                <div className="p-4 rounded-lg bg-surface-raised border border-editorial-hairline space-y-3">
                  <div className="text-[10px] font-mono uppercase text-editorial-muted">
                    Rectangular Pill • Dashed Border
                  </div>
                  <VerdictBadge
                    verdict="HOLD"
                    confidence={64}
                    rationale="Valuation fair; moving average showing consolidation."
                  />
                  <p className="text-[11px] text-editorial-secondary pt-2">
                    Champagne Gold (#C9A96A) + Scale Icon + Dashed Outline.
                  </p>
                </div>

                {/* AVOID */}
                <div className="p-4 rounded-lg bg-surface-raised border border-editorial-hairline space-y-3">
                  <div className="text-[10px] font-mono uppercase text-editorial-muted">
                    Faceted Warning Block • Thick Anchor
                  </div>
                  <VerdictBadge
                    verdict="AVOID"
                    confidence={79}
                    rationale="Excessive volatility with price breaking below 3M MA."
                  />
                  <p className="text-[11px] text-editorial-secondary pt-2">
                    Muted Vermilion (#FF5A4D) + Octagon Alert + Solid Accent Bar.
                  </p>
                </div>
              </div>

              {/* Design Philosophy Callout */}
              <div className="p-4 rounded-lg bg-base border border-editorial-hairline/80 flex items-start gap-3">
                <Info className="w-4 h-4 text-gold shrink-0 mt-0.5" />
                <p className="text-xs text-editorial-secondary leading-relaxed font-sans">
                  <strong className="text-editorial-primary font-medium">Design System Rule:</strong>{' '}
                  Color is never used as the sole carrier of semantic meaning. Users with protanopia,
                  deuteranopia, or viewing in monochrome print can immediately distinguish recommendations
                  by geometry (chamfer vs rectangle vs block), border pattern (solid vs dashed), and
                  symbolic iconography.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 07: CINEMATIC FINANCIAL CHART ENGINE */}
        {/* ========================================================================= */}
        <section id="charts" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="07"
            title="Cinematic Financial Chart Style"
            subtitle="Eliminating gridline clutter. 1.5px hairline strokes, 3-Month Moving Average rendered as dashed lines, soft area gradients, crosshairs, and a mandatory 'Rebased to 100' normalization toggle."
          />

          <TerminalChart
            data={SAMPLE_CHART_DATA}
            company1Name="Hindustan Aeronautics Ltd"
            company1Symbol="HAL"
            company2Name="Mazagon Dock Shipbuilders"
            company2Symbol="MAZDOCK"
            height={440}
          />
        </section>

        {/* ========================================================================= */}
        {/* SECTION 08: TABS, TOOLTIPS & DISCLAIMERS */}
        {/* ========================================================================= */}
        <section className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="08"
            title="Tabs, Tooltips & Legal Notice"
            subtitle="Regulatory-compliant disclaimer bars, keyboard-navigable ARIA tablists, and hover/focus tooltips."
          />

          <div className="p-8 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline space-y-8">
            {/* Tabs Showcase */}
            <div className="space-y-4">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Tab Styles (Underline & Raised Pill)
              </span>

              <div className="flex flex-col sm:flex-row gap-6 items-start">
                <Tabs
                  variant="underline"
                  activeTab={activeTab}
                  onChange={setActiveTab}
                  tabs={[
                    { id: 'overview', label: 'Technical Trajectory', count: '24M' },
                    { id: 'metrics', label: 'Risk Ratios', count: 4 },
                    { id: 'news', label: 'News Attribution', count: 12 },
                  ]}
                />

                <Tabs
                  variant="pill"
                  activeTab={activeTab}
                  onChange={setActiveTab}
                  tabs={[
                    { id: 'overview', label: 'Trajectory' },
                    { id: 'metrics', label: 'Risk' },
                    { id: 'news', label: 'News' },
                  ]}
                />
              </div>
            </div>

            {/* Tooltips */}
            <div className="space-y-3 border-t border-editorial-hairline pt-6">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Interactive Accessible Tooltips
              </span>
              <div className="flex flex-wrap items-center gap-6">
                <Tooltip content="3-Month rolling moving average calculated over calendar close days." position="top">
                  <span className="inline-flex items-center gap-1.5 text-xs font-mono text-gold border-b border-gold/40 border-dashed pb-0.5 cursor-help">
                    <Info className="w-3.5 h-3.5" />
                    <span>Hover/Focus for MA Rule</span>
                  </span>
                </Tooltip>

                <Tooltip content="Normalizes both stock initial prices to 100 on Day 0." position="bottom">
                  <span className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan border-b border-cyan/40 border-dashed pb-0.5 cursor-help">
                    <Info className="w-3.5 h-3.5" />
                    <span>Rebased Explanation</span>
                  </span>
                </Tooltip>

                <Tooltip content="Verified against NSE official circular archives." position="right">
                  <span className="inline-flex items-center gap-1.5 text-xs font-mono text-gain border-b border-gain/40 border-dashed pb-0.5 cursor-help">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Exchange Data Provenance</span>
                  </span>
                </Tooltip>
              </div>
            </div>

            {/* Disclaimer Bar */}
            <div className="space-y-3 border-t border-editorial-hairline pt-6">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Legal & Regulatory Compliance Bar
              </span>
              <DisclaimerBar />
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 09: SYSTEM FEEDBACK STATES */}
        {/* ========================================================================= */}
        <section id="states" className="space-y-8 scroll-mt-20">
          <SectionHeader
            number="09"
            title="System Feedback & Loading States"
            subtitle="Subdued luxury skeleton loaders, cinematic empty states, and diagnostic error recovery frames with retry handlers."
          />

          <div className="space-y-6">
            {/* Skeleton Loaders */}
            <div className="space-y-3">
              <span className="text-xs font-mono uppercase tracking-wider text-editorial-muted">
                Skeleton Placeholders (Warm Subdued Shimmer)
              </span>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                <Skeleton variant="metricCard" />
                <Skeleton variant="metricCard" />
                <Skeleton variant="metricCard" />
              </div>
            </div>

            {/* Empty State & Error State Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
              <EmptyState
                title="Awaiting Equity Pair Selection"
                description="Input any two NSE or BSE symbols into the terminal header to render 24-month technical trajectories, Sharpe ratios, and catalyst verification."
                actionLabel="Load Benchmark Pair (HAL vs Mazagon)"
                onAction={() => {
                  setCompanyA('HAL');
                  setCompanyB('MAZDOCK');
                }}
              />

              <ErrorState
                title="Exchange Rate Limiting Throttling"
                message="Upstream market data latency exceeded 4,000ms threshold during 2-year candle fetch. Local cached datasets remain verified and operational."
                technicalDetails="HTTP 429: Too Many Requests\nEndpoint: /api/historical/HAL.NS\nRetry-After: 30s\nFallback available: OFFLINE_DEMO_CACHE"
                onRetry={handleRetrySim}
                isRetrying={isRetrying}
                onLaunchOffline={() => alert('Switched to guaranteed Offline Demo dataset')}
              />
            </div>

            {showErrorToast && (
              <div className="p-3 rounded-lg bg-gain/10 border border-gain/30 text-gain text-xs font-mono flex items-center gap-2 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4" />
                <span>Diagnostics recovered: Connection re-established successfully.</span>
              </div>
            )}
          </div>
        </section>

        {/* ========================================================================= */}
        {/* SECTION 10: CSS TOKEN DICTIONARY */}
        {/* ========================================================================= */}
        <section className="space-y-6 pt-6 border-t border-editorial-hairline">
          <SectionHeader
            number="10"
            title="Tailwind & CSS Tokens Reference"
            subtitle="Direct CSS variable bindings declared in frontend/src/styles/tokens.css."
          />

          <div className="p-6 rounded-card bg-surface-card border border-editorial-hairline shadow-hairline overflow-x-auto">
            <pre className="font-mono text-xs text-editorial-secondary leading-relaxed">
{`/* frontend/src/styles/tokens.css */
--bg-base: #0A0B0D;              /* Near-black base */
--bg-surface: #101215;           /* Card containers */
--bg-raised: #171A1F;            /* Elevated dropdowns & chips */
--border-hairline: rgba(255, 255, 255, 0.07);
--text-primary: #F2F0EB;         /* Warm off-white */
--text-secondary: #9A9A94;       /* Secondary captions */
--text-muted: #5E5F5A;           /* Low-contrast details */
--color-gain: #2FD08A;           /* Refined emerald */
--color-loss: #FF5A4D;           /* Muted vermilion */
--color-neutral: #C9A96A;        /* Champagne gold */
--company1-accent: #C9A96A;      /* Co. 1 Champagne Gold */
--company2-accent: #6FB7D6;      /* Co. 2 Steel Cyan */`}
            </pre>
          </div>
        </section>
      </main>

      {/* Floating Design System Switcher Pill (Fixed in Bottom Right) */}
      <aside aria-label="Developer utilities" className="fixed bottom-6 right-6 z-50 flex items-center gap-2 p-1.5 rounded-full bg-surface-card/95 border border-gold/40 shadow-2xl backdrop-blur-xl">
        <a
          href="/"
          className="px-3.5 py-1.5 rounded-full text-xs font-mono font-semibold bg-gold text-base hover:bg-gold-light transition-colors flex items-center gap-1.5 shadow-md"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Live App</span>
        </a>
        <a
          href="#top"
          className="px-2.5 py-1.5 rounded-full text-xs font-mono text-editorial-secondary hover:text-editorial-primary transition-colors"
        >
          Top ↑
        </a>
      </aside>
    </div>
  );
};
