"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Download, FileText, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDate, formatRelative } from "@/lib/utils";

interface Report {
  report_id: string;
  job_id: string;
  filename: string | null;
  download_url: string;
  generated_at: string | null;
  notified_at: string | null;
  status: string;
}

interface ReportsResponse {
  total: number;
  page: number;
  per_page: number;
  reports: Report[];
}

const BACKEND_PUBLIC = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
const PER_PAGE = 15;

export default function ReportsPage() {
  const router = useRouter();
  const [data, setData] = useState<ReportsResponse | null>(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`/api/reports?page=${p}&per_page=${PER_PAGE}`, {
        cache: "no-store",
      });
      if (resp.status === 401) { router.push("/login"); return; }
      if (!resp.ok) { setError(`Failed to load reports (${resp.status})`); return; }
      setData(await resp.json());
    } catch {
      setError("Network error — could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => { load(page); }, [load, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PER_PAGE)) : 1;

  return (
    <AppShell breadcrumb={[{ label: "Reports" }]}>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
            <p className="text-sm text-slate-500 mt-1">
              PDF pipeline summaries — download or share with stakeholders.
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={() => load(page)} disabled={loading}>
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
            Refresh
          </Button>
        </div>

        {/* Stats card */}
        <Card>
          <CardContent className="flex items-center gap-8 py-5">
            <div>
              <p className="text-3xl font-bold text-slate-900">{data?.total ?? "—"}</p>
              <p className="text-xs text-slate-500">Total reports</p>
            </div>
            <div className="h-10 w-px bg-slate-200" />
            <div>
              <p className="text-3xl font-bold text-slate-900">
                {data?.reports.filter((r) => r.status === "ready").length ?? "—"}
              </p>
              <p className="text-xs text-slate-500">Ready this page</p>
            </div>
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Loading skeletons */}
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        )}

        {/* Reports table */}
        {!loading && data && data.reports.length > 0 && (
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50">
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      File
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Generated
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Notified
                    </th>
                    <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {data.reports.map((report) => (
                    <tr
                      key={report.report_id}
                      className="hover:bg-slate-50 transition-colors"
                    >
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <FileText size={16} className="text-slate-400 shrink-0" />
                          <div>
                            <p className="font-medium text-slate-800">
                              {report.filename ?? "Unknown file"}
                            </p>
                            <p className="text-xs text-slate-400 font-mono">
                              {report.job_id.substring(0, 8)}…
                            </p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        <span title={formatDate(report.generated_at)}>
                          {formatRelative(report.generated_at)}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-slate-500 text-xs">
                        {report.notified_at ? (
                          <span title={formatDate(report.notified_at)}>
                            {formatRelative(report.notified_at)}
                          </span>
                        ) : (
                          <span className="text-slate-300">—</span>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        <Badge
                          variant={report.status === "ready" ? "success" : "destructive"}
                        >
                          {report.status}
                        </Badge>
                      </td>
                      <td className="px-5 py-4 text-right">
                        {report.status === "ready" && (
                          <a
                            href={`${BACKEND_PUBLIC}${report.download_url}`}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-700 transition-colors"
                          >
                            <Download size={12} />
                            Download PDF
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3">
                <p className="text-xs text-slate-500">
                  Page {page} of {totalPages} ({data.total} reports)
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    <ChevronLeft size={14} />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}

        {/* Empty state */}
        {!loading && data?.total === 0 && (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 py-20 text-center">
            <FileText size={40} className="text-slate-300 mb-3" />
            <p className="text-slate-500 font-medium">No reports generated yet</p>
            <p className="text-sm text-slate-400 mt-1">
              Upload a CSV file and complete the pipeline to generate your first report.
            </p>
            <a
              href="/upload"
              className="mt-4 inline-flex items-center justify-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              Upload CSV
            </a>
          </div>
        )}
      </div>
    </AppShell>
  );
}
