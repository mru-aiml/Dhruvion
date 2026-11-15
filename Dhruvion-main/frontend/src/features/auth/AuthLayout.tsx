import { Triangle, Sparkles, Target } from "lucide-react";

const MISSION_TAGLINES = [
  "Precision navigation for the Red Planet.",
  "Where terrain intelligence meets traverse planning.",
  "Mission control for autonomous exploration.",
  "Charting the unknown, one sol at a time.",
];

function getRandomTagline() {
  return MISSION_TAGLINES[Math.floor(Math.random() * MISSION_TAGLINES.length)];
}

interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLeftPanel() {
  const tagline = getRandomTagline();

  return (
    <aside className="hidden lg:flex lg:w-1/2 min-h-screen flex-col items-center justify-center p-8 md:p-12 xl:p-16 relative">
      {/* Animated background */}
      <div className="absolute inset-0 starfield" aria-hidden="true" />

      {/* Mars video/poster */}
      <div className="relative z-10 w-full max-w-md md:max-w-lg xl:max-w-xl aspect-square">
        <video
          autoPlay
          loop
          muted
          playsInline
          poster="/videos/mars-poster.jpg"
          className="w-full h-full rounded-[24px] object-cover border border-line/40 shadow-[0_0_80px_rgba(240,107,61,0.15)] transition-all duration-500 hover:shadow-[0_0_120px_rgba(240,107,61,0.25)]"
          aria-label="Mars rotation visualization"
        >
          <source src="/videos/mars-rotation.webm" type="video/webm" />
        </video>
        <div className="pointer-events-none absolute inset-0 rounded-[24px] bg-gradient-to-t from-canvas/90 via-transparent to-transparent" aria-hidden />
        {/* Subtle corner accents */}
        <div className="pointer-events-none absolute inset-0 rounded-[24px] border border-mars-orange/10" aria-hidden />
      </div>

      {/* Brand mark */}
      <div className="mt-8 flex items-center gap-3">
        <span className="relative grid h-12 w-12 shrink-0 place-items-center border border-mars-orange/70 bg-mars-orange/[0.06] text-xl font-bold text-mars-orange">
          D
          <span aria-hidden className="absolute -right-px -top-px h-2 w-2 bg-mars-orange" />
        </span>
        <div className="leading-tight">
          <div className="font-heading text-xl md:text-2xl font-semibold tracking-[0.18em] text-text-primary">DHRUVION</div>
          <div className="text-[10px] md:text-[11px] uppercase tracking-[0.16em] text-text-muted">Mission Control</div>
        </div>
      </div>

      {/* Tagline */}
      <p className="mt-6 max-w-md text-center text-base md:text-lg leading-relaxed text-text-secondary">
        {tagline}
      </p>

      {/* Technical accents */}
      <div className="mt-8 flex flex-wrap items-center justify-center gap-3 md:gap-4 text-[9px] md:text-[10px] uppercase tracking-[0.12em] text-text-muted/60">
        <div className="flex items-center gap-1.5">
          <Triangle size={10} className="text-mars-orange/60" aria-hidden />
          Gale Crater · 5.4°S, 137.8°E
        </div>
        <span className="w-px h-6 bg-line/40 hidden md:block" aria-hidden />
        <div className="flex items-center gap-1.5">
          <Sparkles size={10} className="text-cyan/60" aria-hidden />
          MOLA-derived terrain
        </div>
        <span className="w-px h-6 bg-line/40 hidden md:block" aria-hidden />
        <div className="flex items-center gap-1.5">
          <Target size={10} className="text-amber/60" aria-hidden />
          Simulated context
        </div>
      </div>

      {/* Attribution */}
      <p className="mt-10 text-[9px] uppercase tracking-[0.08em] text-text-muted/50 text-center">
        Visualization: NASA Mars Trek / JPL · Not live telemetry
      </p>
    </aside>
  );
}

export function AuthRightPanel({ children }: AuthLayoutProps) {
  return (
    <main className="relative flex min-h-screen w-full lg:w-1/2 flex-col items-center justify-center px-6 py-8 md:py-10 lg:py-12 overflow-y-auto">
      <div className="w-full max-w-md mx-auto flex-1 flex flex-col">
        {children}
      </div>
    </main>
  );
}

export function AuthCard({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`panel p-5 md:p-7 ${className}`}>
      {children}
    </div>
  );
}

export function AuthHeader({ title, description }: { title: string; description: string }) {
  return (
    <div className="text-center mb-6 md:mb-8">
      <div className="text-micro text-mars-orange">DHRUVION</div>
      <h1 className="mt-2 font-heading text-2xl md:text-3xl font-semibold text-text-primary">{title}</h1>
      <p className="mt-1.5 text-sm md:text-base text-text-secondary">{description}</p>
    </div>
  );
}

export function AuthFooter({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`mt-6 ${className}`}>
      {children}
    </div>
  );
}

export function Divider() {
  return (
    <div className="my-5 flex items-center gap-3" role="separator">
      <span className="flex-1 h-px bg-line/60" aria-hidden />
      <span className="text-[9px] uppercase tracking-[0.1em] text-text-muted shrink-0">or</span>
      <span className="flex-1 h-px bg-line/60" aria-hidden />
    </div>
  );
}

export function BackLink({ className = "" }: { className?: string }) {
  return (
    <div className={`hidden lg:block mt-6 text-center ${className}`}>
      <Link to="/" className="text-xs text-text-muted hover:text-text-secondary underline transition-colors">
        Back to landing
      </Link>
    </div>
  );
}

export function MobileBackLink() {
  return (
    <div className="lg:hidden mb-6 text-center">
      <Link to="/" className="text-xs text-text-muted hover:text-text-secondary underline transition-colors">
        ← Back to landing
      </Link>
    </div>
  );
}

import { Link } from "react-router-dom";