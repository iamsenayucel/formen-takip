import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutGrid, Factory, Users, HardHat, Target, FileText, Presentation,
  LogOut, Moon, Sun, Sparkles, SearchCheck, Repeat2,
  Menu, X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { usePermissions } from "../context/PermissionContext";
import { useTheme } from "../context/ThemeContext";
import { PerformanceLeadersPanel } from "./PerformanceLeadersPanel";
import type { Permission } from "../auth/permissions";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutGrid;
  permission: Permission;
}

interface NavSection {
  label: string | null;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  { label: null, items: [{ to: "/", label: "Genel Bakış", icon: LayoutGrid, permission: "overview.view" }] },
  {
    label: "Performans",
    items: [
      { to: "/plants", label: "Tesisler", icon: Factory, permission: "performance.view" },
      { to: "/groups", label: "Gruplar", icon: Users, permission: "performance.view" },
      { to: "/foremen", label: "Formenler", icon: HardHat, permission: "performance.view" },
      { to: "/kpis", label: "KPI Analizi", icon: Target, permission: "performance.view" },
    ],
  },
  {
    label: "Operasyonel Zekâ",
    items: [
      { to: "/anomalies", label: "Tespitler", icon: SearchCheck, permission: "operational_intelligence.view" },
      { to: "/shift-analysis", label: "Vardiya Analizi", icon: Repeat2, permission: "operational_intelligence.view" },
      { to: "/improvement-works", label: "Operational Impact+", icon: Sparkles, permission: "operational_intelligence.view" },
    ],
  },
  {
    label: "Çıktılar",
    items: [
      { to: "/executive-summary", label: "Yönetici Özeti", icon: Presentation, permission: "overview.view" },
      { to: "/reports", label: "Raporlar", icon: FileText, permission: "outputs.view" },
    ],
  },
];

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { can, isLoading } = usePermissions();
  const visibleSections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: isLoading ? [] : section.items.filter((item) => can(item.permission)),
  })).filter((section) => section.items.length > 0);

  return (
    <nav className="flex flex-1 flex-col gap-3 overflow-y-auto px-2.5 py-3">
      {visibleSections.map((section, sIdx) => (
        <div key={section.label ?? `section-${sIdx}`} className="flex flex-col gap-0.5">
          {section.label && (
            <p
              className="text-label px-3 pb-1 pt-0.5"
              style={{ color: "var(--sidebar-muted)" }}
            >
              {section.label}
            </p>
          )}
          {section.items.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={onNavigate}
                title={item.label}
                className={({ isActive }) =>
                  `relative flex min-w-0 items-center gap-2.5 rounded-md py-1.5 pl-3 pr-2.5 text-[13px] font-medium transition-colors ${
                    isActive
                      ? ""
                      : "sidebar-nav-item text-[var(--sidebar-text)] hover:text-[var(--sidebar-text-hover)]"
                  }`
                }
                style={({ isActive }) =>
                  isActive ? { background: "var(--sidebar-active-bg)", color: "var(--sidebar-text-active)" } : undefined
                }
              >
                {({ isActive }) =>
                  <>
                    {isActive && (
                      <span
                        aria-hidden="true"
                        className="absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-r-full"
                        style={{ background: "var(--sidebar-active-indicator)" }}
                      />
                    )}
                    <Icon size={16} strokeWidth={1.75} className="shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </>
                }
              </NavLink>
            );
          })}
          {section.label === "Çıktılar" && (
            <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--sidebar-border)" }}>
              <PerformanceLeadersPanel onNavigate={onNavigate} />
            </div>
          )}
        </div>
      ))}
    </nav>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileNavOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileNavOpen]);

  return (
    <div className="flex min-h-screen bg-[var(--page-bg)]">
      <aside
        className="hidden w-[var(--sidebar-width)] shrink-0 flex-col md:flex"
        style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
      >
        <div className="px-4 py-4" style={{ borderBottom: "1px solid var(--sidebar-border)" }}>
          <div className="rounded-md p-2" style={{ background: "#ffffff" }}>
            <img src="/logo.png" alt="CORVUS Logo" className="h-auto w-full" />
          </div>
        </div>
        <NavLinks />
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileNavOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="absolute inset-y-0 left-0 flex w-64 flex-col shadow-xl"
            style={{ background: "var(--sidebar-bg)", borderRight: "1px solid var(--sidebar-border)" }}
          >
            <div
              className="flex items-center justify-between px-4 py-3.5"
              style={{ borderBottom: "1px solid var(--sidebar-border)" }}
            >
              <div className="rounded-md p-1.5" style={{ background: "#ffffff" }}>
                <img src="/logo.png" alt="CORVUS Logo" className="h-auto w-[170px]" />
              </div>
              <button
                onClick={() => setMobileNavOpen(false)}
                aria-label="Menüyü kapat"
                className="flex items-center justify-center rounded-md p-1.5 transition-colors hover:bg-[var(--sidebar-active-bg)]"
                style={{ color: "var(--sidebar-text)" }}
              >
                <X size={18} strokeWidth={1.75} />
              </button>
            </div>
            <NavLinks onNavigate={() => setMobileNavOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-h-screen min-w-0 flex-1 flex-col">
        <header
          className="flex items-center justify-between gap-3 bg-[var(--surface)] px-[var(--space-page-padding)] py-[var(--space-header-y)]"
          style={{ borderBottom: "1px solid var(--border)" }}
        >
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setMobileNavOpen(true)}
              aria-label="Menüyü aç"
              className="flex items-center justify-center rounded-md border p-1.5 transition-colors hover:bg-[var(--page-bg)] md:hidden"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <Menu size={18} strokeWidth={1.75} />
            </button>
            <span
              className="text-metadata hidden items-center gap-1.5 rounded border px-2 py-1 uppercase sm:inline-flex"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
              title="SAP entegrasyonu bu ortamda aktif değildir."
            >
              Sentetik Veri Kaynağı — Demo
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-4">
            <button
              onClick={toggleTheme}
              title={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
              aria-label={theme === "dark" ? "Açık temaya geç" : "Koyu temaya geç"}
              className="flex items-center justify-center rounded-md border p-1.5 transition-colors hover:bg-[var(--page-bg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              {theme === "dark" ? <Sun size={15} strokeWidth={1.75} /> : <Moon size={15} strokeWidth={1.75} />}
            </button>
            <div className="hidden text-right leading-tight sm:block">
              <div className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{user?.fullName}</div>
              {user?.email && <div className="text-metadata" style={{ color: "var(--text-muted)" }}>{user.email}</div>}
            </div>
            <button
              onClick={() => {
                void logout();
              }}
              className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-[var(--page-bg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--focus-ring)]/40"
              style={{ borderColor: "var(--border-strong)", color: "var(--text-secondary)" }}
            >
              <LogOut size={14} strokeWidth={1.75} />
              <span className="hidden sm:inline">Çıkış Yap</span>
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-x-hidden p-[var(--space-page-padding)]">{children}</main>
      </div>
    </div>
  );
}
