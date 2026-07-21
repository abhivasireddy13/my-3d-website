"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  RefreshCw,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Filter,
  X,
} from "lucide-react";
import AppShell from "@/components/app-shell";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

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
  region: string | null;
  is_anomaly: boolean | null;
  created_at: string;
  recommendation: Recommendation | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function confidenceLabel(score: number | null) {
  if (score === null) return "—";
  if (score >= 0.9) return "High";
  if (score >= 0.6) return "Medium";
  return "Low";
}

function triggerLabel(t: string | null) {
  if (t === "anomaly_detected") return "Anomaly Detected";
  if (t === "forecast_decline") return "Forecast Decline";
  return t ?? "—";
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function RecommendationPanel({ rec }: { rec: Recommendation }) {
  const statusVariant =
    rec.status === "generated" ? "success" : rec.status === "fallback" ? "warning" : "destructive";

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Sparkles size={14} className="text-emerald-600" />
        <span className="text-xs font-semibold text-slate-700 uppercase tracking-wide">
          AI Recommendation
        </span>
        <Badge variant={statusVariant}>{rec.status}</Badge>
        {rec.triggered_by && (
          <span className="text-xs text-slate-500">
            Trigger: <span className="text-slate-700">{triggerLabel(rec.triggered_by)}</span>
          </span>
        )}
        {rec.metric_delta !== null && (
          <span className="text-xs text-slate-500">
            Delta:{" "}
            <span className={rec.metric_delta < 0 ? "text-red-600" : "text-emerald-600"}>
              {(rec.metric_delta * 100).toFixed(1)}%
            </span>
          </span>
        )}
        <span className="text-xs text-slate-500">
          Confidence: <span className="text-slate-700">{confidenceLabel(rec.confidence_score)}</span>
        </span>
        {rec.model_used && (
          <span className="text-xs text-slate-400 font-mono">{rec.model_used}</span>
        )}
      </div>

      <ol className="space-y-1.5">
        {rec.actions.map((action, i) => (
          <li key={i} className="flex gap-2.5 text-sm text-slate-700">
            <span className="shrink-0 mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
              {i + 1}
            </span>
            {action}
          </li>
        ))}
      </ol>

      {rec.error_message && (
        <p className="text-xs text-red-500">Error: {rec.error_message}</p>
      )}
    </div>
  );
}

function PredictionCard({ pred }: { pred: Prediction }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-900 text-sm">{pred.model_name}</span>
            {pred.model_version && (
              <span className="text-xs text-slate-400 font-mono">v{pred.model_version}</span>
            )}
            {pred.region && (
              <Badge variant="secondary">{pred.region}</Badge>
            )}
            {pred.is_anomaly === true && (
              <Badge variant="destructive" className="flex items-center gap-1">
                <AlertTriangle size={10} />
                Anomaly
              </Badge>
            )}
            {pred.is_anomaly === false && (
              <Badge variant="success" className="flex items-center gap-1">
                <CheckCircle2 size={10} />
                OK
              </Badge>
            )}
            {pred.recommendation && (
              <Badge variant="purple">has recommendation</Badge>
            )}
          </div>

          <div className="text-right">
            {pred.prediction_value !== null && (
              <span className="text-xl font-bold text-slate-900">
                {pred.prediction_value.toFixed(2)}
              </span>
            )}
            <p className="text-xs text-slate-400 mt-0.5">{formatDate(pred.created_at)}</p>
          </div>
        </div>

        {pred.upload_job_id && (
          <p className="mt-1 text-xs text-slate-400 font-mono">
            Job: {pred.upload_job_id.substring(0, 8)}…
          </p>
        )}

        {pred.recommendation && (
          <>
            <button
              onClick={() => setExpanded((v) => !v)}
              className="mt-2 flex items-center gap-1 text-xs text-emerald-600 hover:text-emerald-800 font-medium transition-colors"
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? "Hide" : "Show"} AI recommendation
            </button>
            {expanded && <RecommendationPanel rec={pred.recommendation} />}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function PredictionsPage() {
  const router = useRouter();
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterAnomaly, setFilterAnomaly] = useState<"all" | "anomaly" | "ok">("all");
  const [filterRec, setFilterRec] = useState<"all" | "with" | "without">("all");
  const [filterRegion, setFilterRegion] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/predictions?limit=200`, { cache: "no-store" });
      if (resp.status === 401) { router.push("/login"); return; }
      if (!resp.ok) { setError(`Failed to load predictions (${resp.status})`); return; }
      const data = await resp.json();
      setPredictions(data.predictions ?? []);
      setTotal(data.total ?? 0);
    } catch {
      setError("Network error — could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => { load(); }, [load]);

  // Derived filter values
  const regions = Array.from(
    new Set(predictions.map((p) => p.region).filter(Boolean) as string[])
  ).sort();

  const hasActiveFilters =
    filterAnomaly !== "all" ||
    filterRec !== "all" ||
    filterRegion !== "" ||
    filterDateFrom !== "" ||
    filterDateTo !== "";

  const clearFilters = () => {
    setFilterAnomaly("all");
    setFilterRec("all");
    setFilterRegion("");
    setFilterDateFrom("");
    setFilterDateTo("");
  };

  const filtered = predictions.filter((p) => {
    if (filterAnomaly === "anomaly" && p.is_anomaly !== true) return false;
    if (filterAnomaly === "ok" && p.is_anomaly !== false) return false;
    if (filterRec === "with" && !p.recommendation) return false;
    if (filterRec === "without" && p.recommendation) return false;
    if (filterRegion && p.region !== filterRegion) return false;
    if (filterDateFrom && p.created_at && p.created_at < filterDateFrom) return false;
    if (filterDateTo && p.created_at && p.created_at > filterDateTo + "T23:59:59") return false;
    return true;
  });

  const withRecs = predictions.filter((p) => p.recommendation !== null).length;
  const anomalies = predictions.filter((p) => p.is_anomaly === true).length;

  return (
    <AppShell breadcrumb={[{ label: "Predictions" }]}>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">ML Predictions</h1>
            <p className="text-sm text-slate-500 mt-1">
              AI-powered forecast values and anomaly detection from each pipeline run.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: "Total predictions", value: total },
            { label: "With recommendations", value: withRecs },
            { label: "Anomalies", value: anomalies },
          ].map(({ label, value }) => (
            <Card key={label}>
              <CardContent className="py-4 text-center">
                <p className="text-3xl font-bold text-slate-900">{value}</p>
                <p className="text-xs text-slate-500 mt-1">{label}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Filter size={13} />
            Filters
          </div>

          <Select
            value={filterAnomaly}
            onChange={(e) => setFilterAnomaly(e.target.value as typeof filterAnomaly)}
            className="h-8 text-xs w-36"
          >
            <option value="all">All status</option>
            <option value="anomaly">Anomalies only</option>
            <option value="ok">Normal only</option>
          </Select>

          <Select
            value={filterRec}
            onChange={(e) => setFilterRec(e.target.value as typeof filterRec)}
            className="h-8 text-xs w-44"
          >
            <option value="all">All recommendations</option>
            <option value="with">With recommendation</option>
            <option value="without">Without recommendation</option>
          </Select>

          {regions.length > 0 && (
            <Select
              value={filterRegion}
              onChange={(e) => setFilterRegion(e.target.value)}
              className="h-8 text-xs w-36"
            >
              <option value="">All regions</option>
              {regions.map((r) => <option key={r} value={r}>{r}</option>)}
            </Select>
          )}

          <div className="flex items-center gap-1 text-xs text-slate-500">
            <span>From</span>
            <Input
              type="date"
              value={filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
              className="h-8 text-xs w-36"
            />
          </div>
          <div className="flex items-center gap-1 text-xs text-slate-500">
            <span>To</span>
            <Input
              type="date"
              value={filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
              className="h-8 text-xs w-36"
            />
          </div>

          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="h-8 text-xs">
              <X size={12} />
              Clear
            </Button>
          )}

          <span className="ml-auto text-xs text-slate-400">
            {filtered.length} of {total} shown
          </span>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 w-full" />
            ))}
          </div>
        )}

        {/* Empty */}
        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 py-20 text-center">
            <Sparkles size={40} className="text-slate-300 mb-3" />
            <p className="text-slate-500 font-medium">
              {total === 0
                ? "No predictions yet — run a pipeline first."
                : "No predictions match the active filters."}
            </p>
            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="mt-2 text-sm text-slate-400 underline hover:text-slate-600"
              >
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* List */}
        {!loading && filtered.length > 0 && (
          <div className="space-y-3">
            {filtered.map((pred) => (
              <PredictionCard key={pred.prediction_id} pred={pred} />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
