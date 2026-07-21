"use client";

import { useEffect, useState, useCallback } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Recommendation {
  recommendation_id: string;
  actions: string[];
  model_used: string | null;
  triggered_by: string | null;
  metric_delta: number | null;
  confidence_score: number | null;
  status: string;
  error_message: string | null;
  created_at: string;
}

interface Prediction {
  prediction_id: string;
  upload_job_id: string | null;
  model_name: string;
  model_version: string | null;
  prediction_value: number | null;
  is_anomaly: boolean | null;
  created_at: string;
  recommendation: Recommendation | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function triggerLabel(triggered_by: string | null): string {
  if (triggered_by === "anomaly_detected") return "Anomaly Detected";
  if (triggered_by === "forecast_decline") return "Forecast Decline";
  return triggered_by ?? "Unknown trigger";
}

function confidenceLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= 0.9) return "High";
  if (score >= 0.6) return "Medium";
  return "Low (fallback)";
}

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    generated: "bg-emerald-900 text-emerald-300 border-emerald-700",
    fallback: "bg-amber-900 text-amber-300 border-amber-700",
    failed: "bg-red-900 text-red-300 border-red-700",
  };
  const cls = styles[status] ?? "bg-slate-700 text-slate-300 border-slate-600";
  return (
    <span className={`text-xs px-2 py-0.5 rounded border font-mono ${cls}`}>
      {status}
    </span>
  );
}

function AnomalyBadge({ is_anomaly }: { is_anomaly: boolean | null }) {
  if (is_anomaly === true)
    return (
      <span className="text-xs px-2 py-0.5 rounded border bg-red-900 text-red-300 border-red-700 font-mono">
        ANOMALY
      </span>
    );
  if (is_anomaly === false)
    return (
      <span className="text-xs px-2 py-0.5 rounded border bg-slate-700 text-slate-400 border-slate-600 font-mono">
        OK
      </span>
    );
  return null;
}

function RecommendationPanel({ rec }: { rec: Recommendation }) {
  return (
    <div className="mt-3 bg-slate-900 border border-slate-700 rounded-lg p-4">
      <div className="flex flex-wrap items-center gap-3 mb-3">
        <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wide">
          AI Recommendation
        </span>
        <StatusBadge status={rec.status} />
        {rec.triggered_by && (
          <span className="text-xs text-slate-400">
            Trigger:{" "}
            <span className="text-slate-200">{triggerLabel(rec.triggered_by)}</span>
          </span>
        )}
        {rec.metric_delta !== null && (
          <span className="text-xs text-slate-400">
            Change:{" "}
            <span
              className={rec.metric_delta < 0 ? "text-red-400" : "text-emerald-400"}
            >
              {(rec.metric_delta * 100).toFixed(1)}%
            </span>
          </span>
        )}
        <span className="text-xs text-slate-400">
          Confidence:{" "}
          <span className="text-slate-200">{confidenceLabel(rec.confidence_score)}</span>
        </span>
        {rec.model_used && (
          <span className="text-xs text-slate-500 font-mono">{rec.model_used}</span>
        )}
      </div>

      <ol className="space-y-2">
        {rec.actions.map((action, i) => (
          <li key={i} className="flex gap-2 text-sm text-slate-200">
            <span className="shrink-0 w-5 h-5 rounded-full bg-cyan-800 text-cyan-200 text-xs flex items-center justify-center font-bold">
              {i + 1}
            </span>
            {action}
          </li>
        ))}
      </ol>

      {rec.error_message && (
        <p className="mt-2 text-xs text-red-400">
          Error: {rec.error_message}
        </p>
      )}
    </div>
  );
}

function PredictionCard({ pred }: { pred: Prediction }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-semibold text-slate-100 text-sm">{pred.model_name}</span>
          {pred.model_version && (
            <span className="text-xs text-slate-500 font-mono">v{pred.model_version}</span>
          )}
          <AnomalyBadge is_anomaly={pred.is_anomaly} />
          {pred.recommendation && (
            <span className="text-xs px-2 py-0.5 rounded border bg-cyan-900 text-cyan-300 border-cyan-700">
              has recommendation
            </span>
          )}
        </div>
        <div className="text-right">
          {pred.prediction_value !== null && (
            <span className="text-lg font-bold text-slate-100">
              {pred.prediction_value.toFixed(2)}
            </span>
          )}
          <p className="text-xs text-slate-500">{formatDate(pred.created_at)}</p>
        </div>
      </div>

      {pred.upload_job_id && (
        <p className="mt-1 text-xs text-slate-500 font-mono">
          Job: {pred.upload_job_id.substring(0, 8)}…
        </p>
      )}

      {pred.recommendation && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 text-xs text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
          >
            {expanded ? "Hide recommendations" : "Show recommendations"}
          </button>
          {expanded && <RecommendationPanel rec={pred.recommendation} />}
        </div>
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "100" });
      const resp = await fetch(`/api/predictions?${params}`, { cache: "no-store" });
      if (resp.status === 401) {
        setError("Session expired — please log in again.");
        return;
      }
      if (!resp.ok) {
        setError(`Failed to load predictions (${resp.status})`);
        return;
      }
      const data = await resp.json();
      setPredictions(data.predictions ?? []);
      setTotal(data.total ?? 0);
    } catch (e) {
      setError("Network error — could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = predictions.filter((p) => {
    if (filter === "anomaly") return p.is_anomaly === true;
    if (filter === "recommended") return p.recommendation !== null;
    return true;
  });

  const withRecs = predictions.filter((p) => p.recommendation !== null).length;
  const anomalies = predictions.filter((p) => p.is_anomaly === true).length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-100">ML Predictions</h1>
            <p className="text-sm text-slate-400 mt-1">
              AI-powered insights generated after each pipeline run
            </p>
          </div>
          <button
            onClick={load}
            disabled={loading}
            className="text-sm px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-50 text-slate-200 border border-slate-600"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: "Total predictions", value: total },
            { label: "With recommendations", value: withRecs },
            { label: "Anomalies detected", value: anomalies },
          ].map(({ label, value }) => (
            <div
              key={label}
              className="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center"
            >
              <p className="text-3xl font-bold text-cyan-400">{value}</p>
              <p className="text-xs text-slate-400 mt-1">{label}</p>
            </div>
          ))}
        </div>

        {/* Filter tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { key: "all", label: `All (${total})` },
            { key: "recommended", label: `With recommendations (${withRecs})` },
            { key: "anomaly", label: `Anomalies (${anomalies})` },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setFilter(key)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                filter === key
                  ? "bg-cyan-700 border-cyan-600 text-white"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        {error && (
          <div className="bg-red-950 border border-red-800 text-red-300 rounded-lg p-4 mb-6 text-sm">
            {error}
          </div>
        )}

        {loading && (
          <div className="text-center text-slate-400 py-16 text-sm">
            Loading predictions…
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center text-slate-500 py-16">
            <p className="text-4xl mb-3">🤖</p>
            <p className="text-sm">
              {filter === "all"
                ? "No predictions yet — run a pipeline to generate them."
                : `No predictions match the "${filter}" filter.`}
            </p>
          </div>
        )}

        {!loading && !error && filtered.length > 0 && (
          <div className="space-y-4">
            {filtered.map((pred) => (
              <PredictionCard key={pred.prediction_id} pred={pred} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
