"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  UploadCloud,
  Cpu,
  BarChart2,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Circle,
  RefreshCw,
  Copy,
  CheckCheck,
} from "lucide-react";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

type EventSource = "upload_jobs" | "workflow_logs" | "fact_predictions" | "fact_recommendations";

interface TimelineEvent {
  timestamp: string;
  source: EventSource;
  event_type: string;
  label: string;
  icon: string;
  data: Record<string, unknown>;
}

interface TraceJob {
  id: string;
  filename: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  error_detail: unknown;
}

interface SourceCounts {
  upload_jobs: number;
  workflow_logs: number;
  fact_predictions: number;
  fact_recommendations: number;
}

interface TraceResponse {
  job_id: string;
  job: TraceJob;
  event_count: number;
  sources: SourceCounts;
  timeline: TimelineEvent[];
}

// ─── Source config ────────────────────────────────────────────────────────────

const SOURCE_CONFIG: Record<
  EventSource,
  { label: string; colorClass: string; bgClass: string; icon: React.ReactNode }
> = {
  upload_jobs: {
    label: "PostgreSQL / upload_jobs",
    colorClass: "text-blue-600",
    bgClass: "bg-blue-500",
    icon: <UploadCloud size={14} />,
  },
  workflow_logs: {
    label: "MongoDB / workflow_logs",
    colorClass: "text-orange-600",
    bgClass: "bg-orange-500",
    icon: <Cpu size={14} />,
  },
  fact_predictions: {
    label: "PostgreSQL / fact_predictions",
    colorClass: "text-purple-600",
    bgClass: "bg-purple-500",
    icon: <BarChart2 size={14} />,
  },
  fact_recommendations: {
    label: "PostgreSQL / fact_recommendations",
    colorClass: "text-emerald-600",
    bgClass: "bg-emerald-500",
    icon: <Sparkles size={14} />,
  },
};

const STATUS_VARIANT: Record<string, "success" | "destructive" | "info" | "warning" | "purple" | "indigo" | "secondary"> = {
  done: "success",
  failed: "destructive",
  validating: "info",
  cleaning: "warning",
  storing: "warning",
  modeling: "purple",
  recommending: "indigo",
  pending: "secondary",
};

// ─── Data panel ───────────────────────────────────────────────────────────────

function DataPanel({ data }: { data: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setOpen(!open)}
        className="text-xs text-slate-400 hover:text-slate-600 transition-colors"
      >
        {open ? "▲ hide data" : "▼ show data"}
      </button>
      {open && (
        <pre className="mt-1.5 rounded bg-slate-100 p-2 text-xs text-slate-700 overflow-x-auto whitespace-pre-wrap break-all max-h-48">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

// ─── Icon mapper ──────────────────────────────────────────────────────────────

function IconForEvent({ icon, source }: { icon: string; source: EventSource }) {
  const cfg = SOURCE_CONFIG[source];
  const emoji: Record<string, React.ReactNode> = {
    upload: <UploadCloud size={16} />,
    status: <Circle size={16} />,
    complete: <CheckCircle2 size={16} />,
    error: <AlertCircle size={16} />,
    workflow: <Cpu size={16} />,
    prediction: <BarChart2 size={16} />,
    recommendation: <Sparkles size={16} />,
  };
  return (
    <span className={cfg.colorClass}>
      {emoji[icon] ?? <Circle size={16} />}
    </span>
  );
}

// ─── Timeline event row ───────────────────────────────────────────────────────

function TimelineRow({ event, index }: { event: TimelineEvent; index: number }) {
  const cfg = SOURCE_CONFIG[event.source] ?? SOURCE_CONFIG.upload_jobs;

  return (
    <div className="flex gap-4 group">
      {/* Dot + line */}
      <div className="flex flex-col items-center">
        <div
          className={`mt-0.5 h-3 w-3 shrink-0 rounded-full ring-2 ring-white ${cfg.bgClass}`}
        />
        <div className="w-px flex-1 bg-slate-200 group-last:hidden" />
      </div>

      {/* Content */}
      <div className="pb-6 min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <IconForEvent icon={event.icon} source={event.source} />
          <span className="font-medium text-slate-800 text-sm">{event.label}</span>
          <Badge
            className={`text-[10px] px-1.5 py-0 ${cfg.colorClass} border-current`}
            variant="outline"
          >
            {event.source.replace("_", " ")}
          </Badge>
        </div>
        <p className="mt-0.5 text-xs text-slate-400">
          {formatDate(event.timestamp)}
        </p>
        <DataPanel data={event.data as Record<string, unknown>} />
      </div>
    </div>
  );
}

// ─── Source legend ────────────────────────────────────────────────────────────

function SourceLegend({ counts }: { counts: SourceCounts }) {
  return (
    <div className="flex flex-wrap gap-4">
      {(Object.entries(SOURCE_CONFIG) as [EventSource, typeof SOURCE_CONFIG[EventSource]][]).map(
        ([key, cfg]) => (
          <div key={key} className="flex items-center gap-1.5 text-xs text-slate-600">
            <div className={`h-2.5 w-2.5 rounded-full ${cfg.bgClass}`} />
            <span>{cfg.label}</span>
            <span className="font-semibold text-slate-900">({counts[key]})</span>
          </div>
        )
      )}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function TracePage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();

  const [data, setData] = useState<TraceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/admin/trace/${jobId}`, { cache: "no-store" });
      if (resp.status === 401) { router.push("/login"); return; }
      if (resp.status === 403) { router.push("/dashboard"); return; }
      if (resp.status === 404) { setError("Job not found."); return; }
      if (!resp.ok) { setError(`Error ${resp.status}`); return; }
      setData(await resp.json());
    } catch {
      setError("Network error.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [jobId]);

  const copyId = () => {
    navigator.clipboard.writeText(jobId ?? "").then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <AppShell
      breadcrumb={[
        { label: "Admin", href: "/admin" },
        { label: "Trace" },
        { label: (jobId ?? "").substring(0, 8) + "…" },
      ]}
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Back */}
        <button
          onClick={() => router.push("/admin")}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft size={14} />
          Back to Admin
        </button>

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Pipeline Trace</h1>
            <div className="flex items-center gap-2 mt-1">
              <code className="text-xs text-slate-500 font-mono">{jobId}</code>
              <button onClick={copyId} className="text-slate-400 hover:text-slate-700 transition-colors">
                {copied ? <CheckCheck size={12} /> : <Copy size={12} />}
              </button>
            </div>
            {data?.job.filename && (
              <p className="text-sm text-slate-600 mt-1 font-medium">{data.job.filename}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {data?.job.status && (
              <Badge variant={STATUS_VARIANT[data.job.status] ?? "secondary"}>
                {data.job.status}
              </Badge>
            )}
            <Button variant="outline" size="sm" onClick={load} disabled={loading}>
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            </Button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex gap-4">
                <Skeleton className="h-3 w-3 rounded-full mt-0.5 shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-4 w-48" />
                  <Skeleton className="h-3 w-32" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Stats strip */}
        {!loading && data && (
          <>
            {/* Summary cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: "Total events", value: data.event_count },
                { label: "DB events", value: data.sources.upload_jobs },
                { label: "Workflow logs", value: data.sources.workflow_logs },
                { label: "Predictions", value: data.sources.fact_predictions },
              ].map(({ label, value }) => (
                <Card key={label}>
                  <CardContent className="py-3 px-4">
                    <p className="text-xl font-bold text-slate-900">{value}</p>
                    <p className="text-xs text-slate-500">{label}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Source legend */}
            <Card>
              <CardContent className="py-4">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
                  Data sources
                </p>
                <SourceLegend counts={data.sources} />
              </CardContent>
            </Card>

            {/* ── TIMELINE ───────────────────────────────────────────────────── */}
            <Card>
              <CardHeader className="border-b border-slate-200 pb-3">
                <CardTitle className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <span>End-to-End Timeline</span>
                  <Badge variant="secondary">{data.event_count} events</Badge>
                </CardTitle>
                <p className="text-xs text-slate-400 mt-0.5">
                  Every event for this job, ordered chronologically across all data sources.
                </p>
              </CardHeader>
              <CardContent className="pt-5">
                {data.timeline.length === 0 ? (
                  <p className="text-sm text-slate-400 py-4 text-center">No events found.</p>
                ) : (
                  <div>
                    {data.timeline.map((ev, i) => (
                      <TimelineRow key={`${ev.source}-${i}`} event={ev} index={i} />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Job metadata */}
            <details className="rounded-lg border border-slate-200 overflow-hidden">
              <summary className="cursor-pointer select-none px-5 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors">
                Raw job metadata
              </summary>
              <pre className="px-5 pb-4 pt-2 text-xs text-slate-700 bg-slate-50 overflow-x-auto whitespace-pre-wrap break-all">
                {JSON.stringify(data.job, null, 2)}
              </pre>
            </details>
          </>
        )}
      </div>
    </AppShell>
  );
}
