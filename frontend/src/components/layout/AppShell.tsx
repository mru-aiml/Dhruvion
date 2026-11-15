import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  AlertTriangle,
  Bot,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileText,
  LayoutDashboard,
  Map,
  Microscope,
  Route,
  Settings,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import TopBar from "./TopBar";

interface NavItem {
  to: string;
  label: string;
  shortLabel: string;
  icon: typeof LayoutDashboard;
}

const NAV_SECTIONS: { label: string; items: NavItem[] }[] = [
  {
    label: "Operations",
    items: [
      { to: "/overview", label: "Mission Overview", shortLabel: "Overview", icon: LayoutDashboard },
      { to: "/missions", label: "Mission Management", shortLabel: "Missions", icon: ClipboardList },
      { to: "/map", label: "Martian Map", shortLabel: "Map", icon: Map },
      { to: "/routes", label: "Route Planner", shortLabel: "Routes", icon: Route },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/science", label: "Science Explorer", shortLabel: "Science", icon: Microscope },
      { to: "/assistant", label: "AI Mission Assistant", shortLabel: "Assistant", icon: Bot },
      { to: "/reports", label: "Mission Reports", shortLabel: "Reports", icon: FileText },
    ],
  },
  {
    label: "Safety",
    items: [
      {
        to: "/emergency",
        label: "Emergency Navigation",
        shortLabel: "Emergency",
        icon: AlertTriangle,
      },
    ],
  },
  {
    label: "System",
    items: [{ to: "/settings", label: "Settings", shortLabel: "Settings", icon: Settings }],
  },
];

export default function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem("dhruvion.sidebarCollapsed") === "true";
    } catch {
      return false;
    }
  });
  const location = useLocation();

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [mobileOpen]);

  const toggleCollapsed = () => {
    setCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem("dhruvion.sidebarCollapsed", String(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  };

  return (
    <div className="flex h-screen w-screen bg-canvas text-text-primary">
      <aside
        aria-label="Mission control navigation"
        className={clsx(
          "hidden shrink-0 border-r border-line/80 bg-[#0e0c0a] transition-[width] duration-200 md:flex md:flex-col",
          collapsed ? "w-[72px]" : "w-[252px]",
        )}
      >
        <SidebarContent collapsed={collapsed} onToggle={toggleCollapsed} />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="dialog" aria-modal="true" aria-label="Navigation menu">
          <button
            type="button"
            aria-label="Close navigation"
            className="absolute inset-0 bg-black/70 backdrop-blur-[2px]"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-[278px] flex-col border-r border-line bg-[#0e0c0a] shadow-2xl">
            <div className="flex items-center justify-between border-b border-line px-4 py-4">
              <Link to="/overview" className="flex items-center gap-2.5">
                <BrandMark />
                <span className="leading-tight">
                  <span className="block font-heading text-sm font-semibold tracking-[0.18em]">
                    DHRUVION
                  </span>
                  <span className="block text-[9px] uppercase tracking-[0.16em] text-text-muted">
                    Mission Control
                  </span>
                </span>
              </Link>
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation"
                className="grid h-9 w-9 place-items-center rounded-control border border-line text-text-secondary transition-colors hover:border-mars-orange/60 hover:text-text-primary"
              >
                <X size={18} />
              </button>
            </div>
            <SidebarContent collapsed={false} onToggle={() => setMobileOpen(false)} mobile />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar onMenu={() => setMobileOpen(true)} />
        <main className="dash-scroll relative flex-1 overflow-y-auto">
          <div className="dash-grid min-h-full">
            <div className="mx-auto w-full max-w-[1560px] px-4 py-5 sm:px-6 sm:py-6 lg:px-8">
              <div key={location.pathname} className="page-in">
                <Outlet />
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function BrandMark() {
  return (
    <span className="relative grid h-8 w-8 shrink-0 place-items-center border border-mars-orange/70 bg-mars-orange/[0.06] text-xs font-bold text-mars-orange">
      D
      <span aria-hidden className="absolute -right-px -top-px h-1.5 w-1.5 bg-mars-orange" />
    </span>
  );
}

function SidebarContent({
  collapsed,
  onToggle,
  mobile = false,
}: {
  collapsed: boolean;
  onToggle: () => void;
  mobile?: boolean;
}) {
  return (
    <>
      <div
        className={clsx(
          "flex h-16 shrink-0 items-center border-b border-line/80",
          collapsed ? "justify-center px-2" : "justify-between gap-2 px-4",
        )}
      >
        {collapsed ? (
          <Link to="/overview" aria-label="Dhruvion mission control">
            <BrandMark />
          </Link>
        ) : (
          <>
            <Link to="/overview" className="flex min-w-0 items-center gap-2.5">
              <BrandMark />
              <span className="min-w-0 leading-tight">
                <span className="block truncate font-heading text-[13px] font-semibold tracking-[0.2em]">
                  DHRUVION
                </span>
                <span className="block text-[9px] uppercase tracking-[0.16em] text-text-muted">
                  Mission Control
                </span>
              </span>
            </Link>
            <span className="flex items-center gap-1 text-[8px] uppercase tracking-[0.1em] text-safe-green">
              <span className="h-1.5 w-1.5 rounded-full bg-safe-green" />
              Ops
            </span>
          </>
        )}
      </div>

      <nav
        aria-label="Workspaces"
        className="dash-scroll flex-1 overflow-y-auto px-2 py-3"
      >
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-4 last:mb-0">
            {!collapsed && (
              <div className="mb-1.5 px-2 text-[9px] font-medium uppercase tracking-[0.18em] text-text-muted/80">
                {section.label}
              </div>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    title={collapsed ? item.label : undefined}
                    aria-label={collapsed ? item.label : undefined}
                    className={({ isActive }) =>
                      clsx(
                        "group relative flex h-9 items-center rounded-control text-[12px] transition-colors duration-150",
                        collapsed ? "justify-center px-2" : "gap-2.5 px-2.5",
                        isActive
                          ? "bg-mars-orange/[0.12] font-medium text-text-primary"
                          : "text-text-secondary hover:bg-surface2 hover:text-text-primary",
                      )
                    }
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && (
                          <span
                            aria-hidden
                            className="absolute left-0 top-1.5 h-6 w-0.5 rounded-full bg-mars-orange"
                          />
                        )}
                        <Icon
                          size={16}
                          aria-hidden
                          className={clsx(
                            "shrink-0 transition-colors",
                            isActive ? "text-mars-orange" : "text-text-muted group-hover:text-text-secondary",
                          )}
                        />
                        {!collapsed && <span className="truncate">{item.label}</span>}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 border-t border-line/80 p-2.5">
        {!collapsed && (
          <div className="mb-2 rounded-control border border-line/60 bg-surface1/70 px-2.5 py-2">
            <div className="flex items-center justify-between text-[9px] uppercase tracking-[0.12em] text-text-muted">
              <span>Gale Crater</span>
              <span className="text-text-secondary">DEMO-001</span>
            </div>
            <div className="mt-1.5 flex items-center gap-1.5 text-[9px] uppercase tracking-[0.1em] text-text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-warning-amber" />
              Partial dataset · simulated context
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={clsx(
            "flex h-8 w-full items-center rounded-control border border-transparent text-[10px] uppercase tracking-[0.1em] text-text-muted transition-colors hover:border-line/70 hover:bg-surface2 hover:text-text-secondary",
            collapsed ? "justify-center" : "justify-between px-2",
          )}
        >
          {!collapsed && <span>Collapse</span>}
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
        {mobile && !collapsed && (
          <div className="mt-1 text-center text-[8px] uppercase tracking-[0.16em] text-text-muted/70">
            Demo environment
          </div>
        )}
      </div>
    </>
  );
}
