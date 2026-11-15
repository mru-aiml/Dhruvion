import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import {
  ArrowUpRight,
  Bell,
  BellOff,
  ChevronDown,
  FileText,
  LogOut,
  Menu,
  Settings as SettingsIcon,
  User,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";
import { clsx } from "clsx";
import { endpoints } from "../../services/api/endpoints";
import { useAuth } from "../../context/AuthContext";

interface Notification {
  id: string;
  text: string;
  read: boolean;
  link?: string;
}

const PAGE_LABELS: Record<string, string> = {
  "/overview": "Mission Overview",
  "/map": "Martian Map",
  "/routes": "Route Planner",
  "/science": "Science Explorer",
  "/emergency": "Emergency Navigation",
  "/assistant": "AI Mission Assistant",
  "/reports": "Mission Reports",
  "/settings": "Settings",
};

function NotificationDropdown({
  open,
  onClose,
  notifications,
  unread,
  onMarkRead,
  onMarkAllRead,
  onNavigate,
}: {
  open: boolean;
  onClose: () => void;
  notifications: Notification[];
  unread: number;
  onMarkRead: (id: string) => void;
  onMarkAllRead: () => void;
  onNavigate: (path: string) => void;
}) {
  if (!open) return null;

  return createPortal(
    <div
      role="menu"
      aria-label="Notifications"
      className="fixed right-4 top-16 z-[100] w-[calc(100vw-2rem)] max-w-[360px] border border-line bg-surface1 shadow-panel"
    >
      <div className="flex items-center justify-between border-b border-line/70 px-3.5 py-3">
        <div>
          <div className="text-micro text-mars-orange">Mission feed</div>
          <div className="mt-0.5 text-xs font-medium text-text-primary">
            Notifications
            {unread > 0 && (
              <span className="ml-1.5 text-text-muted">({unread} unread)</span>
            )}
          </div>
        </div>
        {notifications.length > 0 && (
          <button
            type="button"
            onClick={onMarkAllRead}
            className="text-[10px] uppercase tracking-[0.08em] text-text-muted transition-colors hover:text-text-secondary"
          >
            Mark all read
          </button>
        )}
      </div>
      <div className="dash-scroll max-h-72 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center px-4 py-8 text-center">
            <BellOff size={20} className="text-text-muted" aria-hidden />
            <div className="mt-2 text-xs font-medium text-text-secondary">
              No notifications yet
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
              Mission events and exported reports appear here.
            </p>
          </div>
        ) : (
          notifications.map((item) => (
            <button
              key={item.id}
              type="button"
              role="menuitem"
              onClick={() => {
                onMarkRead(item.id);
                if (item.link) onNavigate(item.link);
                onClose();
              }}
              className="flex w-full items-start gap-2.5 border-b border-line/40 px-3.5 py-2.5 text-left transition-colors last:border-b-0 hover:bg-surface2"
            >
              <span
                aria-hidden
                className={clsx(
                  "mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full",
                  item.read ? "bg-line" : "bg-mars-orange",
                )}
              />
              <span
                className={clsx(
                  "min-w-0 flex-1 text-[11px] leading-relaxed",
                  item.read ? "text-text-muted" : "text-text-secondary",
                )}
              >
                {item.text}
              </span>
              {item.link && (
                <ArrowUpRight size={12} className="mt-1 shrink-0 text-text-muted" />
              )}
            </button>
          ))
        )}
      </div>
      <div className="border-t border-line/60 px-3.5 py-2 text-[9px] uppercase tracking-[0.1em] text-text-muted">
        Stored on this device
      </div>
    </div>,
    document.body
  );
}

function ProfileDropdown({
  open,
  onClose,
  user,
  initials,
  onNavigate,
  onLogout,
}: {
  open: boolean;
  onClose: () => void;
  user: { full_name?: string | null; email?: string | null } | null;
  initials: string;
  onNavigate: (path: string) => void;
  onLogout: () => void;
}) {
  if (!open) return null;

  return createPortal(
    <div
      role="menu"
      aria-label="Operator menu"
      className="fixed right-4 top-16 z-[100] w-64 border border-line bg-surface1 shadow-panel"
    >
      <div className="border-b border-line/70 px-3.5 py-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-9 w-9 place-items-center rounded-full border border-mars-orange/40 bg-mars-orange/10 text-[11px] font-semibold text-mars-orange">
            {initials}
          </span>
          <div className="min-w-0">
            <div className="truncate text-xs font-medium text-text-primary">
              {user?.full_name ?? "Mission Operator"}
            </div>
            <div className="truncate text-[10px] text-text-muted">
              {user?.email ?? "Not signed in"}
            </div>
          </div>
        </div>
        <div className="mt-2 text-[9px] uppercase tracking-[0.12em] text-text-muted">
          Mission operator · Demo environment
        </div>
      </div>
      <div className="p-1.5">
        <button
          type="button"
          role="menuitem"
          onClick={() => {
            onNavigate("/settings");
            onClose();
          }}
          className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-xs text-text-secondary transition-colors hover:bg-surface2 hover:text-text-primary"
        >
          <SettingsIcon size={14} /> Settings
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={() => {
            onNavigate("/reports");
            onClose();
          }}
          className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-xs text-text-secondary transition-colors hover:bg-surface2 hover:text-text-primary"
        >
          <FileText size={14} /> Mission reports
        </button>
        <button
          type="button"
          role="menuitem"
          onClick={() => {
            onNavigate("/settings");
            onClose();
          }}
          className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-xs text-text-secondary transition-colors hover:bg-surface2 hover:text-text-primary"
        >
          <User size={14} /> Operator profile
        </button>
      </div>
      <div className="border-t border-line/70 p-1.5">
        <button
          type="button"
          role="menuitem"
          onClick={onLogout}
          className="flex w-full items-center gap-2 rounded-control px-2 py-2 text-left text-xs text-critical-red transition-colors hover:bg-critical-red/10"
        >
          <LogOut size={14} /> Sign out
        </button>
      </div>
    </div>,
    document.body
  );
}

export default function TopBar({ onMenu }: { onMenu: () => void }) {
  const [status, setStatus] = useState<"checking" | "ok" | "down">("checking");
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("dhruvion.notifications") || "[]");
    } catch {
      return [];
    }
  });
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const pageLabel = PAGE_LABELS[location.pathname] ?? "Mission Control";

  useEffect(() => {
    let active = true;
    const check = () => {
      endpoints
        .health()
        .then(() => active && setStatus("ok"))
        .catch(() => active && setStatus("down"));
    };
    check();
    const timer = window.setInterval(check, 60000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const handler = () => {
      try {
        setNotifications(JSON.parse(localStorage.getItem("dhruvion.notifications") || "[]"));
      } catch {
        /* ignore */
      }
    };
    window.addEventListener("dhruvion:notifications", handler);
    return () => window.removeEventListener("dhruvion:notifications", handler);
  }, []);

  useEffect(() => {
    const escape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setNotifOpen(false);
        setProfileOpen(false);
      }
    };
    document.addEventListener("keydown", escape);
    return () => document.removeEventListener("keydown", escape);
  }, []);

  // Close dropdowns on route change
  useEffect(() => {
    setNotifOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  // Handle outside clicks for dropdowns (using event delegation on document)
  useEffect(() => {
    const handler = (event: MouseEvent) => {
      // Close if clicking outside both dropdown areas
      const target = event.target as Node;
      const notifButton = document.querySelector('[aria-label^="Notifications"]');
      const profileButton = document.querySelector('[aria-label="Operator profile"]');

      const clickedNotifButton = notifButton?.contains(target);
      const clickedProfileButton = profileButton?.contains(target);

      // Check if click is inside portal-rendered dropdowns
      const notifDropdown = document.querySelector('[role="menu"][aria-label="Notifications"]');
      const profileDropdown = document.querySelector('[role="menu"][aria-label="Operator menu"]');

      const clickedInsideNotifDropdown = notifDropdown?.contains(target);
      const clickedInsideProfileDropdown = profileDropdown?.contains(target);

      if (!clickedNotifButton && !clickedInsideNotifDropdown) {
        setNotifOpen(false);
      }
      if (!clickedProfileButton && !clickedInsideProfileDropdown) {
        setProfileOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const persist = (next: Notification[]) => {
    setNotifications(next);
    try {
      localStorage.setItem("dhruvion.notifications", JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  const markRead = (id: string) =>
    persist(notifications.map((item) => (item.id === id ? { ...item, read: true } : item)));
  const markAllRead = () => persist(notifications.map((item) => ({ ...item, read: true })));
  const unread = notifications.filter((item) => !item.read).length;

  const handleLogout = async () => {
    await logout();
    setProfileOpen(false);
    navigate("/login", { replace: true });
  };

  const initials = user?.full_name
    ? user.full_name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("")
    : "OP";

  return (
    <header className="print-hide flex h-16 shrink-0 items-center justify-between gap-3 border-b border-line/80 bg-[#0e0c0a]/95 px-3 backdrop-blur md:px-5">
      <div className="flex min-w-0 items-center gap-2.5">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open navigation"
          className="grid h-9 w-9 shrink-0 place-items-center rounded-control border border-line text-text-secondary transition-colors hover:border-mars-orange/60 hover:text-text-primary md:hidden"
        >
          <Menu size={17} />
        </button>
        <div className="min-w-0">
          <div className="hidden text-[9px] uppercase tracking-[0.18em] text-text-muted sm:block">
            Mission Control
          </div>
          <div className="truncate font-heading text-sm font-semibold tracking-tight text-text-primary">
            {pageLabel}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <div className="hidden items-center gap-2 rounded-control border border-line/60 bg-surface1/60 px-2.5 py-1.5 xl:flex">
          <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-mars-orange" />
          <span className="text-[9px] font-medium uppercase tracking-[0.12em] text-text-secondary">
            MSN Alpha-1
          </span>
          <span className="h-3 w-px bg-line/80" />
          <span className="text-[9px] uppercase tracking-[0.1em] text-text-muted">
            Gale Crater
          </span>
        </div>

        <div
          className="hidden items-center gap-1.5 rounded-control border border-line/60 bg-surface1/60 px-2 py-1.5 text-[9px] uppercase tracking-[0.1em] sm:flex"
          title="Backend health endpoint"
        >
          {status === "ok" ? (
            <Wifi size={13} className="text-safe-green" aria-hidden />
          ) : status === "down" ? (
            <WifiOff size={13} className="text-critical-red" aria-hidden />
          ) : (
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-muted" />
          )}
          <span
            className={clsx(
              status === "ok"
                ? "text-safe-green"
                : status === "down"
                  ? "text-critical-red"
                  : "text-text-muted",
            )}
          >
            {status === "ok" ? "Data link active" : status === "down" ? "Data link down" : "Checking link"}
          </span>
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setNotifOpen((open) => !open);
              setProfileOpen(false);
            }}
            aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
            aria-haspopup="menu"
            aria-expanded={notifOpen}
            className="relative grid h-9 w-9 place-items-center rounded-control border border-transparent text-text-secondary transition-colors hover:border-line hover:bg-surface2 hover:text-text-primary"
          >
            <Bell size={17} />
            {unread > 0 && (
              <span className="absolute -right-0.5 -top-0.5 grid min-w-[15px] place-items-center rounded-full border border-[#0e0c0a] bg-critical-red px-1 text-[8px] font-bold leading-4 text-[#1b0707]">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>

          <NotificationDropdown
            open={notifOpen}
            onClose={() => setNotifOpen(false)}
            notifications={notifications}
            unread={unread}
            onMarkRead={markRead}
            onMarkAllRead={markAllRead}
            onNavigate={navigate}
          />
        </div>

        <span aria-hidden className="mx-0.5 hidden h-5 w-px bg-line/80 sm:block" />

        <div className="relative">
          <button
            type="button"
            onClick={() => {
              setProfileOpen((open) => !open);
              setNotifOpen(false);
            }}
            aria-label="Operator profile"
            aria-haspopup="menu"
            aria-expanded={profileOpen}
            className={clsx(
              "flex h-9 items-center gap-2 rounded-control border px-1.5 transition-colors sm:pr-2.5",
              profileOpen
                ? "border-mars-orange/50 bg-surface2"
                : "border-line/70 bg-surface1/60 hover:border-line hover:bg-surface2",
            )}
          >
            <span className="grid h-6 w-6 place-items-center rounded-full border border-mars-orange/40 bg-mars-orange/10 text-[9px] font-semibold text-mars-orange">
              {initials}
            </span>
            <span className="hidden max-w-[120px] truncate text-[11px] text-text-secondary sm:block">
              {user?.full_name ?? "Operator"}
            </span>
            <ChevronDown
              size={13}
              className={clsx(
                "hidden text-text-muted transition-transform sm:block",
                profileOpen && "rotate-180",
              )}
            />
          </button>

          <ProfileDropdown
            open={profileOpen}
            onClose={() => setProfileOpen(false)}
            user={user}
            initials={initials}
            onNavigate={navigate}
            onLogout={handleLogout}
          />
        </div>
      </div>
    </header>
  );
}
