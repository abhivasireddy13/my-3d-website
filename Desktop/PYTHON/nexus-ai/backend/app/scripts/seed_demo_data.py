"""
NEXUS AI — Demo data seed script
=================================
Generates 12 months of realistic multi-region sales data, uploads it through
the standard CSV pipeline, trains the ML models, runs predictions, triggers
AI recommendations, and generates a PDF report.

Run from the project root:
  # Against the running Docker stack (default):
  python -m backend.app.scripts.seed_demo_data

  # Override the backend URL:
  NEXUS_API=http://my-vps.example.com python -m backend.app.scripts.seed_demo_data

Idempotent: checks for existing demo uploads and skips if already present.
"""

import csv
import io
import json
import math
import os
import random
import sys
import time
from datetime import date, timedelta

# ── Dependency bootstrap ──────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

# ── Configuration ─────────────────────────────────────────────────────────────
BASE        = os.getenv("NEXUS_API",      "http://localhost:8000")
ML_BASE     = os.getenv("NEXUS_ML_API",   "http://localhost:8100")
ADMIN_EMAIL = os.getenv("NEXUS_ADMIN",    "admin@nexus.ai")
ADMIN_PASS  = os.getenv("NEXUS_ADMIN_PW", "Admin123!")
INT_SECRET  = os.getenv("NEXUS_INT_SECRET", "change_me_shared_secret")
SEED_MARKER = "NEXUS_DEMO_SEED_v1"      # tag stored in CSV filename to detect re-runs

# ── Logging helpers ───────────────────────────────────────────────────────────
def _ok(msg):  print(f"  [+] {msg}")
def _err(msg): print(f"  [!] {msg}", file=sys.stderr)
def _inf(msg): print(f"  ... {msg}")


# ── CSV generation ────────────────────────────────────────────────────────────

REGIONS = ["North", "South", "East", "West"]

def _base_revenue(day_of_year: int, region: str) -> float:
    """Return a realistic daily revenue with seasonality, trend, and noise."""
    # Long-run growth trend (~15 % annual)
    trend = 1.0 + 0.15 * (day_of_year / 365)

    # Seasonal sine wave: peaks in Dec (day ~355) and a smaller peak in summer
    seasonal = (
        1.0
        + 0.30 * math.sin(2 * math.pi * (day_of_year - 80) / 365)
        + 0.10 * math.sin(4 * math.pi * (day_of_year - 60) / 365)
    )

    # Region-level baseline multiplier
    region_mult = {"North": 1.0, "South": 0.85, "East": 1.15, "West": 0.95}[region]

    # Gaussian noise ±8 %
    noise = random.gauss(1.0, 0.08)

    base = 12_000 * trend * seasonal * region_mult * noise
    return round(max(base, 500.0), 2)


def _units(revenue: float) -> int:
    """Derive unit count from revenue with some independent noise."""
    return max(1, int(revenue / 45 * random.gauss(1.0, 0.05)))


def generate_csv() -> bytes:
    """Return CSV bytes with 12 months of daily rows across all regions."""
    start = date.today().replace(month=1, day=1) - timedelta(days=365)
    rows: list[dict] = []

    random.seed(42)          # deterministic output

    current = start
    day_num = 0
    while current < date.today():
        day_num += 1
        for region in REGIONS:
            rev = _base_revenue(day_num, region)
            rows.append({
                "date":    current.isoformat(),
                "region":  region,
                "revenue": rev,
                "units":   _units(rev),
            })
        current += timedelta(days=1)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["date", "region", "revenue", "units"])
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


# ── API helpers ───────────────────────────────────────────────────────────────

def _login(email: str, password: str, session: requests.Session) -> str:
    r = session.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": password}, timeout=15)
    r.raise_for_status()
    token = r.json()["access_token"]
    session.headers.update({"Authorization": f"Bearer {token}"})
    return token


def _already_seeded(session: requests.Session) -> bool:
    """Return True if a demo-seed upload already exists."""
    r = session.get(f"{BASE}/api/v1/admin/jobs", timeout=10)
    if not r.ok:
        return False
    jobs = r.json().get("jobs", [])
    return any(SEED_MARKER in (j.get("filename") or "") for j in jobs)


def _upload_csv(csv_bytes: bytes, session: requests.Session) -> str:
    """Upload CSV, return job_id."""
    files = {"file": (f"{SEED_MARKER}.csv", io.BytesIO(csv_bytes), "text/csv")}
    r = session.post(f"{BASE}/api/v1/uploads/", files=files, timeout=30)
    r.raise_for_status()
    job_id = r.json()["job_id"]
    _ok(f"Uploaded — job_id={job_id}")
    return job_id


def _poll_pipeline(job_id: str, session: requests.Session, timeout: int = 180) -> str:
    """Poll ETL status until done/failed or timeout. Returns final status."""
    deadline = time.time() + timeout
    last = "unknown"
    while time.time() < deadline:
        r = session.get(f"{BASE}/api/v1/uploads/{job_id}/status", timeout=10)
        if r.ok:
            last = r.json().get("status", "unknown")
            _inf(f"pipeline status={last}")
            if last in ("done", "failed"):
                return last
        time.sleep(3)
    return last


def _train_models() -> None:
    """Train both ML models — safe to call repeatedly (idempotent)."""
    _inf("Training sales-forecast model …")
    r = requests.post(f"{ML_BASE}/train/sales-forecast", timeout=120)
    if r.ok:
        _ok(f"sales-forecast trained (mae={r.json().get('mae', '?')})")
    else:
        _err(f"sales-forecast training: {r.status_code} {r.text[:200]}")

    _inf("Training anomaly-detection model …")
    r = requests.post(f"{ML_BASE}/train/anomaly-detection", timeout=120)
    if r.ok:
        _ok(f"anomaly-detection trained (score={r.json().get('mean_anomaly_score', '?')})")
    else:
        _err(f"anomaly-detection training: {r.status_code} {r.text[:200]}")


def _create_predictions(job_id: str) -> None:
    """Call the ML service to produce fact_predictions for this job."""
    # Sales forecast
    r = requests.post(
        f"{ML_BASE}/predict/sales-forecast",
        json={"recent_values": [12000, 13500, 11800, 14200, 13100], "upload_job_id": job_id},
        timeout=30,
    )
    if r.ok:
        _ok(f"Forecast prediction: {r.json().get('forecast', '?'):.2f}")
    else:
        _err(f"Forecast predict: {r.status_code} {r.text[:200]}")

    # Anomaly (inject a high-revenue outlier to guarantee a recommendation)
    r = requests.post(
        f"{ML_BASE}/predict/anomaly",
        json={"revenue": 95000.0, "units": 1800, "upload_job_id": job_id},
        timeout=30,
    )
    if r.ok:
        _ok(f"Anomaly prediction: is_anomaly={r.json().get('is_anomaly')}")
    else:
        _err(f"Anomaly predict: {r.status_code} {r.text[:200]}")


def _trigger_recommendations(job_id: str) -> None:
    r = requests.post(
        f"{BASE}/internal/pipeline-callback",
        json={"job_id": job_id, "status": "recommending", "stage": "recommending"},
        headers={"X-Internal-Secret": INT_SECRET},
        timeout=15,
    )
    if r.ok:
        _ok("Recommendations triggered (background task started)")
    else:
        _err(f"Recommendations trigger: {r.status_code} {r.text[:200]}")

    # Give the background task time to generate recommendations
    _inf("Waiting 20 s for recommendations …")
    time.sleep(20)


def _generate_report(job_id: str) -> None:
    r = requests.post(
        f"{BASE}/internal/generate-report/{job_id}",
        headers={"X-Internal-Secret": INT_SECRET},
        timeout=30,
    )
    if r.ok:
        data = r.json()
        _ok(f"Report generated — {data.get('n_predictions', 0)} predictions, "
            f"revenue={data.get('kpis', {}).get('total_revenue', '?')}")
    else:
        _err(f"Report generation: {r.status_code} {r.text[:200]}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n=== NEXUS AI — Demo Data Seed ===\n")

    session = requests.Session()

    # Authenticate as admin
    _inf("Logging in as admin …")
    try:
        _login(ADMIN_EMAIL, ADMIN_PASS, session)
        _ok(f"Authenticated as {ADMIN_EMAIL}")
    except Exception as exc:
        _err(f"Login failed: {exc}")
        sys.exit(1)

    # Idempotency guard
    if _already_seeded(session):
        _ok(f"Demo data already present ({SEED_MARKER}) — nothing to do.")
        sys.exit(0)

    # Generate and upload CSV
    _inf("Generating 12-month multi-region CSV …")
    csv_bytes = generate_csv()
    row_count = csv_bytes.count(b"\n") - 1
    _ok(f"Generated {row_count} rows ({len(csv_bytes) // 1024} KB)")

    job_id = _upload_csv(csv_bytes, session)

    # Wait for ETL
    _inf("Polling ETL pipeline …")
    status = _poll_pipeline(job_id, session)
    if status != "done":
        _err(f"Pipeline ended with status={status} — aborting ML steps")
        sys.exit(1)
    _ok("ETL pipeline completed")

    # Train ML models and create predictions
    _train_models()
    _create_predictions(job_id)

    # Recommendations + report
    _trigger_recommendations(job_id)
    _generate_report(job_id)

    print("\n=== Seed complete ===")
    print(f"  Job ID : {job_id}")
    print(f"  Rows   : {row_count}")
    print(f"  Visit  : {BASE.replace('http://', 'https://')}/dashboard\n")


if __name__ == "__main__":
    main()
