
interface AuthLayoutProps {
  children: React.ReactNode;
}

export function AuthLeftPanel() {
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
        <div className="pointer-events-none absolute inset-0 rounded-[24px] border border-mars-orange/10" aria-hidden />
      </div>

      {/* Single tagline */}
      <p className="relative z-10 mt-6 max-w-md text-center text-sm tracking-wide text-text-muted/80">
        Every mission begins with understanding the terrain.
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