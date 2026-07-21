export default function Dashboard() {
  return (
    <main className="p-8 space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
        <a
          href="/upload"
          className="rounded-xl border bg-white p-6 hover:shadow-md transition-shadow space-y-1"
        >
          <p className="font-semibold text-slate-800">Upload CSV</p>
          <p className="text-sm text-slate-500">Start a new data pipeline</p>
        </a>
        <div className="rounded-xl border bg-white p-6 space-y-1 opacity-50 cursor-not-allowed">
          <p className="font-semibold text-slate-800">KPI Cards</p>
          <p className="text-sm text-slate-500">Coming in Phase 8</p>
        </div>
      </div>
    </main>
  );
}
