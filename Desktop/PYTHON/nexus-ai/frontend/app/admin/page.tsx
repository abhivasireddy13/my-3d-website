"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Users,
  UploadCloud,
  RefreshCw,
  Activity,
  ChevronLeft,
  ChevronRight,
  Search,
  AlertCircle,
} from "lucide-react";
import AppShell from "@/components/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { formatDate, formatRelative } from "@/lib/utils";

// ─── Types ────────────────────────────────────────────────────────────────────

interface User {
  id: string;
  email: string;
  role: string;
  created_at: string | null;
}

interface Job {
  id: string;
  filename: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  error_detail: unknown;
}

// ─── Status badge helper ──────────────────────────────────────────────────────

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

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={STATUS_VARIANT[status] ?? "secondary"}>
      {status}
    </Badge>
  );
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────

type Tab = "users" | "jobs";

// ─── Main page ────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("users");

  // Users state
  const [users, setUsers] = useState<User[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersSearch, setUsersSearch] = useState("");

  // Jobs state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsTotal, setJobsTotal] = useState(0);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobsPage, setJobsPage] = useState(1);
  const [jobsStatus, setJobsStatus] = useState("");
  const JOB_PER_PAGE = 20;

  const [error, setError] = useState<string | null>(null);

  // ── Load users ────────────────────────────────────────────────────────────
  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    setError(null);
    try {
      const resp = await fetch("/api/admin/users", { cache: "no-store" });
      if (resp.status === 401) { router.push("/login"); return; }
      if (resp.status === 403) { router.push("/dashboard"); return; }
      if (!resp.ok) { setError(`Failed to load users (${resp.status})`); return; }
      const data = await resp.json();
      setUsers(data.users ?? []);
      setUsersTotal(data.total ?? 0);
    } catch {
      setError("Network error.");
    } finally {
      setUsersLoading(false);
    }
  }, [router]);

  // ── Load jobs ─────────────────────────────────────────────────────────────
  const loadJobs = useCallback(async (p: number, status: string) => {
    setJobsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(p),
        per_page: String(JOB_PER_PAGE),
      });
      if (status) params.set("status", status);
      const resp = await fetch(`/api/admin/jobs?${params}`, { cache: "no-store" });
      if (resp.status === 401) { router.push("/login"); return; }
      if (resp.status === 403) { router.push("/dashboard"); return; }
      if (!resp.ok) { setError(`Failed to load jobs (${resp.status})`); return; }
      const data = await resp.json();
      setJobs(data.jobs ?? []);
      setJobsTotal(data.total ?? 0);
    } catch {
      setError("Network error.");
    } finally {
      setJobsLoading(false);
    }
  }, [router]);

  useEffect(() => { loadUsers(); }, [loadUsers]);
  useEffect(() => { loadJobs(jobsPage, jobsStatus); }, [loadJobs, jobsPage, jobsStatus]);

  const filteredUsers = usersSearch
    ? users.filter(
        (u) =>
          u.email.toLowerCase().includes(usersSearch.toLowerCase()) ||
          u.role.toLowerCase().includes(usersSearch.toLowerCase())
      )
    : users;

  const totalJobPages = Math.max(1, Math.ceil(jobsTotal / JOB_PER_PAGE));

  return (
    <AppShell breadcrumb={[{ label: "Admin" }]}>
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Admin Console</h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage users, monitor pipeline jobs, and investigate issues.
          </p>
        </div>

        {/* KPI strip */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: "Total users", value: usersTotal, icon: <Users size={18} /> },
            { label: "Total jobs", value: jobsTotal, icon: <UploadCloud size={18} /> },
            {
              label: "Completed",
              value: jobs.filter((j) => j.status === "done").length,
              icon: <Activity size={18} />,
            },
            {
              label: "Failed",
              value: jobs.filter((j) => j.status === "failed").length,
              icon: <AlertCircle size={18} />,
            },
          ].map(({ label, value, icon }) => (
            <Card key={label}>
              <CardContent className="flex items-center gap-3 py-4 px-5">
                <div className="text-slate-400">{icon}</div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{value}</p>
                  <p className="text-xs text-slate-500">{label}</p>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 border-b border-slate-200">
          {(["users", "jobs"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium transition-colors capitalize border-b-2 -mb-px ${
                tab === t
                  ? "border-slate-900 text-slate-900"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              {t === "users" ? `Users (${usersTotal})` : `Jobs (${jobsTotal})`}
            </button>
          ))}
        </div>

        {/* ── Users tab ──────────────────────────────────────────────────────── */}
        {tab === "users" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="relative flex-1 max-w-xs">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <Input
                  placeholder="Search users…"
                  className="pl-8"
                  value={usersSearch}
                  onChange={(e) => setUsersSearch(e.target.value)}
                />
              </div>
              <Button variant="outline" size="sm" onClick={loadUsers} disabled={usersLoading}>
                <RefreshCw size={14} className={usersLoading ? "animate-spin" : ""} />
              </Button>
            </div>

            {usersLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50">
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Email</th>
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Role</th>
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Joined</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredUsers.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-5 py-3 font-medium text-slate-800">{u.email}</td>
                          <td className="px-5 py-3">
                            <Badge
                              variant={
                                u.role === "admin" ? "default" : u.role === "analyst" ? "info" : "secondary"
                              }
                            >
                              {u.role}
                            </Badge>
                          </td>
                          <td className="px-5 py-3 text-slate-500 text-xs">
                            {formatDate(u.created_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filteredUsers.length === 0 && (
                    <p className="py-8 text-center text-sm text-slate-400">No users found.</p>
                  )}
                </div>
              </Card>
            )}
          </div>
        )}

        {/* ── Jobs tab ───────────────────────────────────────────────────────── */}
        {tab === "jobs" && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Select
                value={jobsStatus}
                onChange={(e) => { setJobsStatus(e.target.value); setJobsPage(1); }}
                className="w-44"
              >
                <option value="">All statuses</option>
                {["pending", "validating", "cleaning", "storing", "modeling", "recommending", "done", "failed"].map(
                  (s) => <option key={s} value={s}>{s}</option>
                )}
              </Select>
              <Button
                variant="outline"
                size="sm"
                onClick={() => loadJobs(jobsPage, jobsStatus)}
                disabled={jobsLoading}
              >
                <RefreshCw size={14} className={jobsLoading ? "animate-spin" : ""} />
              </Button>
            </div>

            {jobsLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
              </div>
            ) : (
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50">
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">File</th>
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Uploaded</th>
                        <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Updated</th>
                        <th className="px-5 py-3 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {jobs.map((job) => (
                        <tr key={job.id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-5 py-3">
                            <p className="font-medium text-slate-800">{job.filename}</p>
                            <p className="text-xs text-slate-400 font-mono">{job.id.substring(0, 8)}…</p>
                          </td>
                          <td className="px-5 py-3">
                            <StatusBadge status={job.status} />
                          </td>
                          <td className="px-5 py-3 text-slate-500 text-xs">
                            <span title={formatDate(job.created_at)}>{formatRelative(job.created_at)}</span>
                          </td>
                          <td className="px-5 py-3 text-slate-500 text-xs">
                            <span title={formatDate(job.updated_at)}>{formatRelative(job.updated_at)}</span>
                          </td>
                          <td className="px-5 py-3 text-right">
                            <a
                              href={`/admin/trace/${job.id}`}
                              className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
                            >
                              <Activity size={12} />
                              View Trace
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {jobs.length === 0 && (
                    <p className="py-8 text-center text-sm text-slate-400">No jobs found.</p>
                  )}
                </div>

                {/* Pagination */}
                {totalJobPages > 1 && (
                  <div className="flex items-center justify-between border-t border-slate-200 px-5 py-3">
                    <p className="text-xs text-slate-500">
                      Page {jobsPage} of {totalJobPages}
                    </p>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" disabled={jobsPage === 1} onClick={() => setJobsPage((p) => p - 1)}>
                        <ChevronLeft size={14} />
                      </Button>
                      <Button variant="outline" size="sm" disabled={jobsPage === totalJobPages} onClick={() => setJobsPage((p) => p + 1)}>
                        <ChevronRight size={14} />
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
