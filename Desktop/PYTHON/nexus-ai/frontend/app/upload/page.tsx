"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

// ─── Pipeline step definitions ───────────────────────────────────────────────
const STEPS = [
  "Validating",
  "Cleaning",
  "Storing",
  "Modeling",
  "Recommending",
  "Done",
] as const;

const STATUS_TO_STEP: Record<string, number> = {
  pending: -1,
  validating: 0,
  cleaning: 1,
  storing: 2,
  modeling: 3,
  recommending: 4,
  done: 5,
};

// ─── Types ────────────────────────────────────────────────────────────────────
type PollResult = {
  job_id: string;
  status: string;
  error_detail: Record<string, unknown> | null;
};

type HistoryItem = {
  job_id: string;
  filename: string;
  status: string;
  created_at: string | null;
};

// ─── Main page ────────────────────────────────────────────────────────────────
export default function UploadPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const [jobId, setJobId] = useState<string | null>(null);
  const [poll, setPoll] = useState<PollResult | null>(null);

  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);

  // ── History fetch ───────────────────────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    const res = await fetch("/api/uploads");
    if (res.status === 401) { router.push("/login"); return; }
    if (!res.ok) return;
    const data = await res.json();
    setHistory(data.items ?? []);
    setHistoryTotal(data.total ?? 0);
  }, [router]);

  useEffect(() => { fetchHistory(); }, [fetchHistory]);

  // ── Status poll ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!jobId) return;

    const tick = async () => {
      const res = await fetch(`/api/uploads/${jobId}/status`);
      if (res.status === 401) { router.push("/login"); return; }
      if (!res.ok) return;
      const data: PollResult = await res.json();
      setPoll(data);
      if (data.status === "done" || data.status === "failed") {
        clearInterval(intervalRef.current!);
        intervalRef.current = null;
        fetchHistory();
      }
    };

    tick();
    intervalRef.current = setInterval(tick, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, router, fetchHistory]);

  // ── Drag-and-drop handlers ──────────────────────────────────────────────────
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) acceptFile(dropped);
  };

  const acceptFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setUploadError("Only CSV files are accepted.");
      return;
    }
    setUploadError("");
    setFile(f);
    setPoll(null);
    setJobId(null);
  };

  // ── Upload submit ───────────────────────────────────────────────────────────
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadError("");
    setPoll(null);
    setJobId(null);

    const form = new FormData();
    form.append("file", file);

    const res = await fetch("/api/uploads", { method: "POST", body: form });
    setUploading(false);

    if (res.status === 401) { router.push("/login"); return; }
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setUploadError(data.detail ?? "Upload failed.");
      return;
    }

    const data = await res.json();
    setFile(null);
    setJobId(data.job_id);
    fetchHistory(); // show the new job in history immediately
  };

  // ── Derived stepper state ───────────────────────────────────────────────────
  const activeStep = poll ? (STATUS_TO_STEP[poll.status] ?? -1) : -1;
  const isFailed = poll?.status === "failed";
  const isDone = poll?.status === "done";

  return (
    <main className="mx-auto max-w-3xl p-8 space-y-8">
      {/* Nav */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Upload CSV</h1>
        <a href="/dashboard" className="text-sm text-slate-500 hover:text-slate-800">
          ← Dashboard
        </a>
      </div>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        aria-label="File drop zone"
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && fileInputRef.current?.click()}
        className={[
          "rounded-xl border-2 border-dashed p-14 text-center cursor-pointer transition-colors select-none",
          dragOver
            ? "border-blue-500 bg-blue-50"
            : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50",
        ].join(" ")}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) acceptFile(f);
            e.target.value = "";
          }}
        />
        {file ? (
          <p className="font-medium text-slate-700">
            {file.name}{" "}
            <span className="text-slate-400 font-normal">
              ({(file.size / 1024).toFixed(1)} KB)
            </span>
          </p>
        ) : (
          <div className="space-y-1">
            <p className="text-slate-600 font-medium">
              Drag &amp; drop a CSV file here
            </p>
            <p className="text-slate-400 text-sm">or click to browse</p>
          </div>
        )}
      </div>

      {/* Upload button */}
      {file && !uploading && (
        <button
          onClick={handleUpload}
          className="rounded-lg bg-blue-600 px-6 py-2.5 text-white font-medium hover:bg-blue-700 transition-colors"
        >
          Upload &amp; Process
        </button>
      )}

      {uploading && (
        <p className="text-slate-500 animate-pulse">Uploading…</p>
      )}

      {uploadError && (
        <p className="text-red-600 text-sm">{uploadError}</p>
      )}

      {/* ── Pipeline stepper ─────────────────────────────────────────────── */}
      {poll && (
        <div className="rounded-xl border bg-white p-6 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-slate-700">
              Job{" "}
              <span className="font-mono text-slate-500 text-sm">
                {poll.job_id.slice(0, 8)}…
              </span>
            </h2>
            <StatusBadge status={poll.status} />
          </div>

          {isFailed ? (
            <div className="rounded-lg bg-red-50 border border-red-200 p-4 space-y-2">
              <p className="font-medium text-red-700">Pipeline failed</p>
              {poll.error_detail && (
                <pre className="text-sm text-red-600 whitespace-pre-wrap overflow-auto max-h-40">
                  {JSON.stringify(poll.error_detail, null, 2)}
                </pre>
              )}
            </div>
          ) : (
            <Stepper activeStep={activeStep} isDone={isDone} />
          )}

          {isDone && (
            <p className="text-green-600 font-medium text-sm">
              Processing complete — results are available.
            </p>
          )}
        </div>
      )}

      {/* ── Upload history ────────────────────────────────────────────────── */}
      {history.length > 0 && (
        <div className="rounded-xl border bg-white overflow-hidden">
          <div className="px-5 py-3 border-b bg-slate-50 flex items-center justify-between">
            <h2 className="font-semibold text-slate-700">Recent Uploads</h2>
            <span className="text-xs text-slate-400">{historyTotal} total</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b">
                <th className="px-5 py-2 font-medium">File</th>
                <th className="px-5 py-2 font-medium">Status</th>
                <th className="px-5 py-2 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.job_id} className="border-t hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-2.5 font-medium text-slate-800">
                    {item.filename}
                  </td>
                  <td className="px-5 py-2.5">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-5 py-2.5 text-slate-400 text-xs">
                    {item.created_at
                      ? new Date(item.created_at).toLocaleString()
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

// ─── Stepper component ────────────────────────────────────────────────────────
function Stepper({ activeStep, isDone }: { activeStep: number; isDone: boolean }) {
  return (
    <div className="relative pt-1">
      {/* Track */}
      <div className="absolute top-4 left-4 right-4 h-0.5 bg-slate-200" />
      {/* Progress fill */}
      <div
        className="absolute top-4 left-4 h-0.5 bg-green-400 transition-all duration-500"
        style={{
          width:
            isDone
              ? "calc(100% - 2rem)"
              : activeStep <= 0
              ? "0%"
              : `${(activeStep / (STEPS.length - 1)) * 100}%`,
        }}
      />
      {/* Step circles + labels */}
      <div className="relative flex justify-between">
        {STEPS.map((label, i) => {
          const isComplete = isDone || i < activeStep;
          const isActive = !isDone && i === activeStep;
          return (
            <div key={label} className="flex flex-col items-center gap-1.5 w-14">
              <div
                className={[
                  "z-10 w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300",
                  isComplete
                    ? "bg-green-500 text-white shadow-sm"
                    : isActive
                    ? "bg-blue-600 text-white ring-4 ring-blue-100 shadow-md"
                    : "bg-slate-200 text-slate-400",
                ].join(" ")}
              >
                {isComplete ? "✓" : i + 1}
              </div>
              <span
                className={[
                  "text-xs text-center leading-tight font-medium",
                  isComplete
                    ? "text-green-600"
                    : isActive
                    ? "text-blue-600"
                    : "text-slate-400",
                ].join(" ")}
              >
                {label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Status badge ──────────────────────────────────────────────────────────────
const BADGE_STYLES: Record<string, string> = {
  pending:      "bg-slate-100 text-slate-600",
  validating:   "bg-blue-100 text-blue-700",
  cleaning:     "bg-yellow-100 text-yellow-700",
  storing:      "bg-orange-100 text-orange-700",
  modeling:     "bg-purple-100 text-purple-700",
  recommending: "bg-indigo-100 text-indigo-700",
  done:         "bg-green-100 text-green-700",
  failed:       "bg-red-100 text-red-700",
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={[
        "inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold",
        BADGE_STYLES[status] ?? "bg-slate-100 text-slate-600",
      ].join(" ")}
    >
      {status}
    </span>
  );
}
