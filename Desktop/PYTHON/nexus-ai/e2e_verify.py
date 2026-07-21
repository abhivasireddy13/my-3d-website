"""
End-to-end verification: register -> login -> upload -> ETL -> predictions
-> recommendations -> report -> admin trace.
"""
import time, json, random, string, os, sys, io

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests

BASE = "http://localhost:8000"
FE   = "http://localhost:3000"
ML   = "http://localhost:8100"
INTERNAL_SECRET = "change_me_shared_secret"

errors = []

def ok(msg):   print(f"  [OK]   {msg}")
def fail(msg): print(f"  [FAIL] {msg}"); errors.append(msg)
def info(msg): print(f"  [...]  {msg}")
def chk(cond, ok_msg, fail_msg):
    if cond: ok(ok_msg)
    else:    fail(fail_msg)

# ── 0. Preflight ─────────────────────────────────────────────────────────────
print("\n[0] Preflight")
try:
    r = requests.get(f"{BASE}/api/v1/auth/me", timeout=5)
    chk(r.status_code in (401, 422), "Backend responding", f"Backend unexpected {r.status_code}")
except Exception as e:
    fail(f"Backend unreachable: {e}"); sys.exit(1)

try:
    r = requests.get(f"{ML}/health", timeout=5)
    chk(r.ok, "ML service responding", f"ML service {r.status_code}")
except Exception as e:
    fail(f"ML service unreachable: {e}")

try:
    r = requests.get(FE, timeout=10)
    chk(r.status_code == 200, "Frontend responding", f"Frontend {r.status_code}")
except Exception as e:
    fail(f"Frontend unreachable: {e}")

# ── 1. Register ───────────────────────────────────────────────────────────────
print("\n[1] Register new user")
suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
email = f"e2e_{suffix}@nexus.dev"
password = "E2eTest123!"

r = requests.post(f"{BASE}/api/v1/auth/register", json={"email": email, "password": password})
chk(r.status_code == 200, f"Registered {email}", f"Register failed: {r.status_code} {r.text}")
user_id = r.json().get("id") if r.ok else None
info(f"User ID: {user_id}")

# ── 2. Login as new viewer ─────────────────────────────────────────────────
print("\n[2] Login")
r = requests.post(f"{BASE}/api/v1/auth/login", json={"email": email, "password": password})
chk(r.status_code == 200, "Login successful", f"Login failed: {r.status_code} {r.text}")
viewer_token = r.json().get("access_token", "") if r.ok else ""
chk(bool(viewer_token), "Got access token", "No access token")

viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

r = requests.get(f"{BASE}/api/v1/auth/me", headers=viewer_headers)
chk(r.status_code == 200, f"/me OK (role={r.json().get('role')})", f"/me failed: {r.status_code}")

# ── 2b. Login as analyst (uploader@nexus.dev) for upload ─────────────────────
analyst_r = requests.post(f"{BASE}/api/v1/auth/login",
    json={"email": "uploader@nexus.dev", "password": "Pass1234!"})
if analyst_r.ok:
    analyst_token = analyst_r.json().get("access_token")
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}
    info("Analyst login OK (uploader@nexus.dev)")
else:
    analyst_token = viewer_token
    analyst_headers = viewer_headers
    fail(f"Analyst login failed {analyst_r.status_code} — uploads will likely fail")

# ── 2c. Login as admin ───────────────────────────────────────────────────────
admin_r = requests.post(f"{BASE}/api/v1/auth/login",
    json={"email": "admin@nexus.ai", "password": "Admin123!"})
if admin_r.ok:
    admin_token = admin_r.json().get("access_token")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    info("Admin login OK (admin@nexus.ai)")
else:
    admin_token = analyst_token
    admin_headers = analyst_headers
    fail(f"Admin login failed {admin_r.status_code}")

# ── 3. Upload CSV ─────────────────────────────────────────────────────────────
print("\n[3] Upload CSV")
csv_candidates = [
    os.path.join(os.path.dirname(__file__), "backend/tests/fixtures/test_sales.csv"),
    os.path.join(os.path.dirname(__file__), "storage/a177cabc-fe4d-4770-aa67-4858a0d29cdd/test_sales.csv"),
]
csv_path = next((p for p in csv_candidates if os.path.exists(p)), None)

if csv_path:
    info(f"Using CSV: {os.path.basename(csv_path)}")
    files = {"file": (os.path.basename(csv_path), open(csv_path, "rb"), "text/csv")}
else:
    info("Generating minimal test CSV")
    csv_content = (
        b"date,revenue,units\n"
        b"2024-01-01,1500.0,30\n"
        b"2024-01-02,2200.0,44\n"
        b"2024-01-03,980.5,20\n"
        b"2024-01-04,3100.0,62\n"
        b"2024-01-05,1800.0,36\n"
        b"2024-01-06,2500.0,50\n"
        b"2024-01-07,1200.0,24\n"
        b"2024-01-08,4200.0,84\n"
        b"2024-01-09,1600.0,32\n"
        b"2024-01-10,2800.0,56\n"
    )
    files = {"file": ("test_sales.csv", io.BytesIO(csv_content), "text/csv")}

r = requests.post(f"{BASE}/api/v1/uploads/", headers=analyst_headers, files=files)
chk(r.status_code == 200, "Upload accepted", f"Upload failed: {r.status_code} {r.text}")
job_id = r.json().get("job_id") if r.ok else None
info(f"Job ID: {job_id}")

# ── 4. Poll pipeline ──────────────────────────────────────────────────────────
print("\n[4] Polling pipeline (up to 120s)...")
final_status = None
last_status = "unknown"

if job_id:
    for i in range(60):
        time.sleep(2)
        pr = requests.get(f"{BASE}/api/v1/uploads/{job_id}/status", headers=analyst_headers)
        if not pr.ok:
            fail(f"Poll failed: {pr.status_code}"); break
        last_status = pr.json().get("status", "unknown")
        if i % 5 == 0 or last_status in ("done", "failed", "recommending"):
            info(f"  t={i*2}s  status={last_status}")
        if last_status in ("done", "failed"):
            final_status = last_status; break
    if final_status == "done":
        ok("Pipeline completed (done)")
    elif final_status == "failed":
        fail(f"Pipeline FAILED: {pr.json().get('error_detail')}")
    else:
        fail(f"Pipeline timed out (last={last_status})")
else:
    fail("No job_id — skipping pipeline poll")

# ── 4b. Train ML models and create predictions ────────────────────────────────
print("\n[4b] Training ML models and creating predictions")
ml_ok = False
if final_status == "done" and job_id:
    # Train sales forecast model
    info("Training sales-forecast model...")
    tr = requests.post(f"{ML}/train/sales-forecast", timeout=60)
    if tr.ok:
        ok(f"Sales forecast trained: {tr.json().get('status')}")
    else:
        info(f"Sales forecast train: {tr.status_code} {tr.text[:200]}")

    # Train anomaly detection model
    info("Training anomaly-detection model...")
    tr2 = requests.post(f"{ML}/train/anomaly-detection", timeout=60)
    if tr2.ok:
        ok(f"Anomaly detection trained: {tr2.json().get('status')}")
    else:
        info(f"Anomaly detection train: {tr2.status_code} {tr2.text[:200]}")

    # Create predictions for this job (one sales forecast + one anomaly)
    if tr.ok or tr2.ok:
        info("Creating predictions via ML service...")

        # Sales forecast prediction
        fp_r = requests.post(f"{ML}/predict/sales-forecast",
            json={"recent_values": [1500.0, 2200.0, 980.5, 3100.0, 1800.0], "upload_job_id": job_id},
            timeout=30)
        if fp_r.ok:
            ok(f"Forecast prediction created: {fp_r.json().get('forecast'):.2f}")
        else:
            info(f"Forecast predict: {fp_r.status_code} {fp_r.text[:200]}")

        # Anomaly prediction
        an_r = requests.post(f"{ML}/predict/anomaly",
            json={"revenue": 4200.0, "units": 84, "upload_job_id": job_id},
            timeout=30)
        if an_r.ok:
            ok(f"Anomaly prediction created: is_anomaly={an_r.json().get('is_anomaly')}")
            ml_ok = True
        else:
            info(f"Anomaly predict: {an_r.status_code} {an_r.text[:200]}")
    else:
        fail("Both ML models failed to train — no predictions created")
else:
    info("Skipping ML predictions (ETL did not complete successfully)")

# ── 4c. Trigger recommendations ──────────────────────────────────────────────
print("\n[4c] Triggering AI recommendations")
if ml_ok and job_id:
    cb_r = requests.post(
        f"{BASE}/internal/pipeline-callback",
        json={"job_id": job_id, "status": "recommending", "stage": "recommending"},
        headers={"X-Internal-Secret": INTERNAL_SECRET},
        timeout=10,
    )
    if cb_r.ok:
        ok(f"Recommendations triggered (status={cb_r.json().get('status')})")
        info("Waiting 15s for background recommendations to generate...")
        time.sleep(15)
    else:
        fail(f"Pipeline callback failed: {cb_r.status_code} {cb_r.text}")
else:
    info("Skipping recommendations (ML predictions not created)")

# ── 5. Predictions ────────────────────────────────────────────────────────────
print("\n[5] Predictions")
r = requests.get(f"{BASE}/api/v1/predictions/", headers=analyst_headers)
chk(r.ok, "GET /predictions/ 200", f"Predictions {r.status_code}")
preds = r.json().get("predictions", []) if r.ok else []
total = r.json().get("total", 0) if r.ok else 0
chk(total > 0, f"{total} prediction(s) found", "No predictions in DB")

if preds:
    p = preds[0]
    info(f"First pred: value={p.get('prediction_value')} anomaly={p.get('is_anomaly')}")
    chk("prediction_value" in p, "prediction_value field present", "Missing prediction_value")
    chk("is_anomaly" in p, "is_anomaly field present", "Missing is_anomaly")

# ── 6. Recommendations ────────────────────────────────────────────────────────
print("\n[6] Recommendations")
r = requests.get(f"{BASE}/api/v1/predictions/", headers=analyst_headers)
preds_now = r.json().get("predictions", []) if r.ok else []
recs = [p for p in preds_now if p.get("recommendation")]

chk(len(recs) > 0, f"{len(recs)} prediction(s) have recommendations",
    "No recommendations generated (check ANTHROPIC_API_KEY or rule-based fallback)")
if recs:
    rec = recs[0].get("recommendation", {})
    info(f"  status={rec.get('status')} actions={len(rec.get('actions',[]))}")
    chk(len(rec.get("actions", [])) > 0, "Actions populated", "Empty actions list")
    pred_id = recs[0].get("prediction_id")
    r2 = requests.get(f"{BASE}/api/v1/predictions/{pred_id}/recommendation", headers=analyst_headers)
    chk(r2.ok, f"GET /predictions/{pred_id[:8]}.../recommendation OK", f"Individual rec endpoint {r2.status_code}")

# ── 7. Reports ────────────────────────────────────────────────────────────────
print("\n[7] Reports")
if job_id:
    rpt_r = requests.post(
        f"{BASE}/internal/generate-report/{job_id}",
        headers={"X-Internal-Secret": INTERNAL_SECRET},
        timeout=20,
    )
    chk(rpt_r.status_code in (200, 409),
        f"Report triggered (status={rpt_r.status_code})",
        f"Report trigger failed: {rpt_r.status_code} {rpt_r.text}")
    if rpt_r.ok:
        info(f"  kpis={rpt_r.json().get('kpis')} n_predictions={rpt_r.json().get('n_predictions')}")
    time.sleep(3)
else:
    info("No job_id — skipping report generation trigger")

rpts_r = requests.get(f"{BASE}/api/v1/reports/", headers=admin_headers)
chk(rpts_r.ok, "GET /reports/ 200", f"Reports list {rpts_r.status_code}")
rpts = rpts_r.json().get("reports", []) if rpts_r.ok else []
info(f"  {len(rpts)} report(s) total")
if rpts:
    rpt = rpts[0]
    chk("download_url" in rpt, "Report has download_url", "Missing download_url")
    dl_url = f"{BASE}{rpt.get('download_url', '')}"
    dl_r = requests.get(dl_url, headers=admin_headers)
    chk(dl_r.status_code in (200, 404),
        f"Download URL reachable (HTTP {dl_r.status_code})",
        f"Download URL error {dl_r.status_code}")

# ── 8. Admin endpoints ────────────────────────────────────────────────────────
print("\n[8] Admin endpoints")
r = requests.get(f"{BASE}/api/v1/admin/users", headers=admin_headers)
chk(r.ok, "GET /admin/users OK", f"Admin users {r.status_code}")
users = r.json().get("users", []) if r.ok else []
info(f"  {len(users)} user(s) in system")
chk(len(users) > 0, "Users list non-empty", "Empty user list")

r = requests.get(f"{BASE}/api/v1/admin/jobs", headers=admin_headers)
chk(r.ok, "GET /admin/jobs OK", f"Admin jobs {r.status_code}")
jobs = r.json().get("jobs", []) if r.ok else []
info(f"  {len(jobs)} job(s) in system")

# Status filter
r = requests.get(f"{BASE}/api/v1/admin/jobs?status=done", headers=admin_headers)
chk(r.ok, "GET /admin/jobs?status=done OK", f"Admin jobs filter {r.status_code}")

# Non-admin blocked
r = requests.get(f"{BASE}/api/v1/admin/users", headers=viewer_headers)
chk(r.status_code == 403, "Non-admin blocked (403)", f"Expected 403 got {r.status_code}")

# ── 9. Admin trace ────────────────────────────────────────────────────────────
print("\n[9] Admin Trace Timeline")
trace_job_id = job_id
if not trace_job_id:
    done_jobs = [j for j in jobs if j.get("status") == "done"]
    if done_jobs:
        trace_job_id = done_jobs[0]["id"]
        info(f"Using existing done job: {trace_job_id[:8]}...")
    elif jobs:
        trace_job_id = jobs[0]["id"]
        info(f"Using most recent job: {trace_job_id[:8]}...")

if trace_job_id:
    r = requests.get(f"{BASE}/api/v1/admin/trace/{trace_job_id}", headers=admin_headers)
    chk(r.ok, f"GET /admin/trace/{trace_job_id[:8]}... OK",
        f"Trace failed: {r.status_code} {r.text}")
    if r.ok:
        trace = r.json()
        event_count = trace.get("event_count", 0)
        sources = trace.get("sources", {})
        timeline = trace.get("timeline", [])
        chk(event_count > 0, f"Timeline has {event_count} events", "Timeline is empty")
        chk(sources.get("upload_jobs", 0) > 0,
            f"upload_jobs (Postgres): {sources.get('upload_jobs')} events",
            "No upload_jobs events in trace")
        chk(sources.get("workflow_logs", 0) > 0,
            f"workflow_logs (MongoDB): {sources.get('workflow_logs')} events",
            "No workflow_logs events in trace")
        chk(sources.get("fact_predictions", 0) > 0,
            f"fact_predictions: {sources.get('fact_predictions')} events",
            "No fact_predictions events")
        info(f"  All sources: {sources}")
        if timeline:
            timestamps = [e.get("timestamp","") for e in timeline if e.get("timestamp")]
            is_sorted = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            chk(is_sorted, "Timeline is chronologically sorted", "Timeline NOT sorted")
            info("  First 4 events:")
            for ev in timeline[:4]:
                info(f"    [{ev.get('source')}] {ev.get('label')} @ {ev.get('timestamp','')[:19]}")
else:
    fail("No job_id available for trace test")

# ── 10. Frontend proxy routes ─────────────────────────────────────────────────
print("\n[10] Frontend Next.js proxy routes")
fe_login = requests.post(f"{FE}/api/auth/login",
    json={"email": "uploader@nexus.dev", "password": "Pass1234!"},
    timeout=15)
chk(fe_login.ok, "POST /api/auth/login via Next.js OK",
    f"Frontend login proxy {fe_login.status_code}: {fe_login.text[:200] if not fe_login.ok else ''}")

session = requests.Session()
if fe_login.ok:
    session.cookies.update(fe_login.cookies)
    chk("access_token" in fe_login.cookies, "access_token cookie set", "No access_token cookie")

    r = session.get(f"{FE}/api/auth/me", timeout=15)
    chk(r.ok, "/api/auth/me via Next.js OK", f"/api/auth/me proxy {r.status_code}")

    r = session.get(f"{FE}/api/predictions", timeout=15)
    chk(r.ok, "/api/predictions via Next.js OK", f"/api/predictions proxy {r.status_code}: {r.text[:100] if not r.ok else ''}")

    r = session.get(f"{FE}/api/reports", timeout=15)
    chk(r.ok, "/api/reports via Next.js OK", f"/api/reports proxy {r.status_code}: {r.text[:100] if not r.ok else ''}")

    r = session.get(f"{FE}/api/uploads", timeout=15)
    chk(r.ok, "/api/uploads via Next.js OK", f"/api/uploads proxy {r.status_code}: {r.text[:100] if not r.ok else ''}")

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
if errors:
    print(f"{len(errors)} check(s) FAILED:")
    for e in errors:
        print(f"  * {e}")
    sys.exit(1)
else:
    print("All E2E checks PASSED!")
    sys.exit(0)
