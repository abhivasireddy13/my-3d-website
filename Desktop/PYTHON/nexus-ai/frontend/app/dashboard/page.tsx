"use client";

import { useCallback, useEffect, useState } from "react";

// ─── Dashboard registry (matches backend DASHBOARDS list) ────────────────────
const SUPERSET_URL =
  process.env.NEXT_PUBLIC_SUPERSET_URL ?? "http://localhost:8088";

interface DashboardMeta {
  id: string;       // slug used in embed-token request
  name: string;
  description: string;
  icon: string;
}

const DASHBOARDS: DashboardMeta[] = [
  {
    id: "exec-overview",
    name: "Executive Overview",
    description: "Total revenue, revenue trend, and top regions at a glance.",
    icon: "📊",
  },
  {
    id: "sales-deep-dive",
    name: "Sales Deep Dive",
    description: "Actuals vs. forecast overlay by region and product.",
    icon: "📈",
  },
  {
    id: "anomaly-monitor",
    name: "Anomaly & Ops",
    description: "Flagged anomalies over time and pipeline job status.",
    icon: "🔍",
  },
];

interface DashboardToken {
  token: string;
  dashboard_id: string;
  expires_in: number;
}

type TokenState = "idle" | "loading" | "ready" | "error" | "auth";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState(0);
  const [tokens, setTokens] = useState<Record<string, DashboardToken | null>>({});
  const [states, setStates] = useState<Record<string, TokenState>>(
    Object.fromEntries(DASHBOARDS.map((d) => [d.id, "idle"]))
  );

  const fetchToken = useCallback(
    async (dashId: string, force = false) => {
      if (!force && states[dashId] === "loading") return;
      setStates((prev) => ({ ...prev, [dashId]: "loading" }));

      try {
        const resp = await fetch(
          `/api/analytics/embed-token?dashboard_id=${encodeURIComponent(dashId)}`,
          { cache: "no-store" }
        );

        if (resp.status === 401) {
          setStates((prev) => ({ ...prev, [dashId]: "auth" }));
          return;
        }
        if (!resp.ok) {
          setStates((prev) => ({ ...prev, [dashId]: "error" }));
          return;
        }

        const data: DashboardToken = await resp.json();
        setTokens((prev) => ({ ...prev, [dashId]: data }));
        setStates((prev) => ({ ...prev, [dashId]: "ready" }));
      } catch {
        setStates((prev) => ({ ...prev, [dashId]: "error" }));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  // Fetch token when the active tab changes (idle → loading)
  useEffect(() => {
    const dash = DASHBOARDS[activeTab];
    if (states[dash.id] === "idle") {
      fetchToken(dash.id);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Refresh tokens every 4 minutes (guest tokens expire in 5)
  useEffect(() => {
    const interval = setInterval(() => {
      const dash = DASHBOARDS[activeTab];
      fetchToken(dash.id, true);
    }, 4 * 60 * 1000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const activeDash = DASHBOARDS[activeTab];
  const tokenState = states[activeDash.id];
  const tokenData = tokens[activeDash.id];

  const iframeSrc =
    tokenState === "ready" && tokenData
      ? `${SUPERSET_URL}/superset/dashboard/${tokenData.dashboard_id}/?guest_token=${tokenData.token}&standalone=3`
      : null;

  return (
    <main className="flex flex-col h-screen bg-slate-50">
      {/* ── Header bar ── */}
      <div className="flex items-center gap-4 px-6 py-3 bg-white border-b border-slate-200 shadow-sm">
        <h1 className="text-lg font-bold text-slate-800 shrink-0">
          NEXUS AI — Analytics
        </h1>

        {/* Tab buttons */}
        <div className="flex gap-2 flex-1 overflow-x-auto">
          {DASHBOARDS.map((dash, i) => (
            <button
              key={dash.id}
              onClick={() => setActiveTab(i)}
              title={dash.description}
              className={[
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium whitespace-nowrap transition-colors",
                i === activeTab
                  ? "bg-slate-800 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200",
              ].join(" ")}
            >
              <span>{dash.icon}</span>
              {dash.name}
            </button>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => {
              setStates((p) => ({ ...p, [activeDash.id]: "idle" }));
              fetchToken(activeDash.id, true);
            }}
            title="Refresh dashboard token"
            className="px-3 py-1.5 text-sm rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors"
          >
            ↻ Refresh
          </button>
          <a
            href="/upload"
            className="px-3 py-1.5 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            + Upload CSV
          </a>
          <a
            href={`${SUPERSET_URL}/superset/dashboard/${activeDash.id}/`}
            target="_blank"
            rel="noreferrer"
            title="Open in Superset"
            className="px-3 py-1.5 text-sm rounded-lg border border-slate-200 text-slate-600 hover:border-slate-400 transition-colors"
          >
            Open ↗
          </a>
        </div>
      </div>

      {/* ── Dashboard iframe ── */}
      <div className="flex-1 relative overflow-hidden">
        {tokenState === "auth" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 text-slate-500">
            <p className="text-lg font-medium">Session expired</p>
            <a
              href="/login"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Log in to view dashboards
            </a>
          </div>
        )}

        {(tokenState === "loading" || tokenState === "idle") && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center space-y-3">
              <div className="inline-block w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-slate-500 text-sm">Loading {activeDash.name}…</p>
            </div>
          </div>
        )}

        {tokenState === "error" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-slate-500">
            <p className="text-lg font-medium">Analytics service unavailable</p>
            <p className="text-sm">
              Superset may still be initializing — allow ~2 min on first start.
            </p>
            <button
              onClick={() => {
                setStates((p) => ({ ...p, [activeDash.id]: "idle" }));
                fetchToken(activeDash.id, true);
              }}
              className="px-4 py-2 bg-slate-800 text-white rounded-lg hover:bg-slate-700"
            >
              Retry
            </button>
          </div>
        )}

        {iframeSrc && (
          /* key forces iframe remount so guest_token header is re-sent */
          <iframe
            key={iframeSrc}
            src={iframeSrc}
            title={activeDash.name}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads"
          />
        )}
      </div>

      {/* ── Status strip ── */}
      <div className="px-6 py-1.5 bg-white border-t border-slate-100 text-xs text-slate-400">
        {activeDash.icon} <strong>{activeDash.name}</strong> — {activeDash.description}
        {tokenData && <span className="ml-2 text-green-600">● Live</span>}
      </div>
    </main>
  );
}
