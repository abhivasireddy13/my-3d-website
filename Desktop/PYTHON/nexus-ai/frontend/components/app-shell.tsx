"use client";

import { useCallback, useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Upload,
  Sparkles,
  FileText,
  Users,
  Activity,
  LogOut,
  Menu,
  X,
  ShieldCheck,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

// ─── Types ────────────────────────────────────────────────────────────────────

interface User {
  id: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
}

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
  roles?: string[]; // undefined = all roles
  exact?: boolean;
}

// ─── Navigation structure ─────────────────────────────────────────────────────

const NAV_ITEMS: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    icon: <BarChart3 size={18} />,
  },
  {
    href: "/upload",
    label: "Upload CSV",
    icon: <Upload size={18} />,
  },
  {
    href: "/predictions",
    label: "Predictions",
    icon: <Sparkles size={18} />,
    roles: ["analyst", "admin"],
  },
  {
    href: "/reports",
    label: "Reports",
    icon: <FileText size={18} />,
    roles: ["analyst", "admin"],
  },
];

const ADMIN_ITEMS: NavItem[] = [
  {
    href: "/admin",
    label: "Users & Jobs",
    icon: <Users size={18} />,
    roles: ["admin"],
    exact: true,
  },
  {
    href: "/admin/trace",
    label: "Trace Jobs",
    icon: <Activity size={18} />,
    roles: ["admin"],
  },
];

// ─── Role badge colours ───────────────────────────────────────────────────────

const ROLE_VARIANT: Record<string, "default" | "info" | "secondary"> = {
  admin: "default",
  analyst: "info",
  viewer: "secondary",
};

// ─── Main component ───────────────────────────────────────────────────────────

interface AppShellProps {
  children: React.ReactNode;
  breadcrumb?: { label: string; href?: string }[];
  /** Override the className of the scrollable main element (e.g. for full-height iframe layouts) */
  mainClassName?: string;
}

export default function AppShell({ children, breadcrumb, mainClassName }: AppShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // ── Fetch current user ────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    fetch("/api/auth/me", { cache: "no-store" })
      .then((r) => {
        if (r.status === 401) { router.push("/login"); return null; }
        return r.json();
      })
      .then((d) => { if (!cancelled && d) setUser(d); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoadingUser(false); });
    return () => { cancelled = true; };
  }, [router]);

  // ── Logout ────────────────────────────────────────────────────────────────
  const handleLogout = useCallback(async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
  }, [router]);

  // ── Nav link active state ─────────────────────────────────────────────────
  const isActive = (item: NavItem) =>
    item.exact ? pathname === item.href : pathname.startsWith(item.href);

  // ── Filter nav items by role ──────────────────────────────────────────────
  const visibleNav = NAV_ITEMS.filter(
    (item) => !item.roles || !user || item.roles.includes(user.role)
  );
  const visibleAdmin = ADMIN_ITEMS.filter(
    (item) => !item.roles || user?.role === "admin"
  );

  // ─── Sidebar content ──────────────────────────────────────────────────────
  const Sidebar = () => (
    <aside className="flex h-full w-60 flex-col border-r border-slate-200 bg-white">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900 text-white text-xs font-bold">
          N
        </div>
        <span className="font-semibold text-slate-900 tracking-tight">NEXUS AI</span>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {visibleNav.map((item) => (
          <a
            key={item.href}
            href={item.href}
            onClick={() => setSidebarOpen(false)}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              isActive(item)
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
            )}
          >
            {item.icon}
            {item.label}
            {isActive(item) && (
              <ChevronRight size={14} className="ml-auto" />
            )}
          </a>
        ))}

        {/* Admin section */}
        {visibleAdmin.length > 0 && (
          <>
            <div className="pt-4 pb-1">
              <div className="flex items-center gap-2 px-3">
                <ShieldCheck size={13} className="text-slate-400" />
                <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">
                  Admin
                </span>
              </div>
            </div>
            {visibleAdmin.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive(item)
                    ? "bg-slate-900 text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )}
              >
                {item.icon}
                {item.label}
              </a>
            ))}
          </>
        )}
      </nav>

      {/* Footer: user info + logout */}
      <div className="border-t border-slate-200 p-3">
        {loadingUser ? (
          <div className="h-10 animate-pulse rounded-md bg-slate-100" />
        ) : user ? (
          <div className="flex items-center gap-2">
            <div className="flex-1 min-w-0">
              <p className="truncate text-xs font-medium text-slate-800">{user.email}</p>
              <div className="mt-0.5">
                <Badge variant={ROLE_VARIANT[user.role] ?? "secondary"} className="text-[10px] px-1.5 py-0">
                  {user.role}
                </Badge>
              </div>
            </div>
            <button
              onClick={handleLogout}
              aria-label="Log out"
              className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : null}
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:flex-shrink-0">
        <Sidebar />
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 flex w-60 lg:hidden">
            <Sidebar />
          </div>
        </>
      )}

      {/* Main area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile topbar */}
        <header className="flex h-14 items-center gap-3 border-b border-slate-200 bg-white px-4 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100"
          >
            <Menu size={20} />
          </button>
          <span className="font-semibold text-slate-900">NEXUS AI</span>
        </header>

        {/* Breadcrumb bar */}
        {breadcrumb && breadcrumb.length > 0 && (
          <div className="flex items-center gap-1.5 border-b border-slate-200 bg-white px-6 py-2.5 text-xs text-slate-500">
            {breadcrumb.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <ChevronRight size={12} />}
                {crumb.href ? (
                  <a href={crumb.href} className="hover:text-slate-800 transition-colors">
                    {crumb.label}
                  </a>
                ) : (
                  <span className="text-slate-800 font-medium">{crumb.label}</span>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Page content */}
        <main className={mainClassName ?? "flex-1 overflow-y-auto p-6"}>{children}</main>
      </div>
    </div>
  );
}
