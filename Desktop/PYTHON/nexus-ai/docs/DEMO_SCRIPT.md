# NEXUS AI — Interview Demo Script

**Format**: 3-minute cold-start walkthrough you can run in a browser tab.
**Pre-condition**: Docker stack is up, demo data is seeded (`seed_demo_data.py` already ran).

---

## Cue Sheet (3 minutes)

### 0:00 — Open the app, orient the interviewer (20 s)

> "This is NEXUS AI — a full-stack analytics platform I built from scratch.
> It ingests business CSV data, runs it through a multi-stage ETL pipeline,
> applies ML anomaly detection and forecasting, and surfaces AI-generated
> recommendations. Let me show you end to end."

Open **`http://localhost:3000/login`** and log in with `uploader@nexus.dev / Pass1234!`.

---

### 0:20 — Upload a CSV (35 s)

1. Click **Upload CSV** in the left nav (or navigate to `/upload`).
2. Drag-and-drop any CSV from the `storage/` folder (or the `test_sales.csv` from `backend/tests/fixtures/`).
3. **Point out**: the stepper — *Validating → Cleaning → Storing → Modeling → Recommending → Done* — updates in real time via polling.
4. The job completes in ~2 seconds because the ETL runs as a FastAPI `BackgroundTask` against the local filesystem.

> "The ETL validates schema, normalises types, deduplicates by date,
> writes to a star schema in Postgres, and audits every stage to MongoDB.
> All of this happens inside a single async pipeline without any external
> dependencies on n8n — n8n is wired up for the ML and notification stages."

---

### 1:00 — Predictions page (35 s)

1. Click **Predictions** in the nav (or `/predictions`).
2. Show the filter bar: anomaly status, recommendation status, region, date range.
3. Point out a row flagged `is_anomaly = true`.
4. Expand the **recommendation panel** on that row.

> "After the ML model flags an anomaly, the system calls Claude via the
> Anthropic API to generate 2–4 concrete business actions. When the API
> key isn't set, a rule-based fallback fires instead — no silent failures."

---

### 1:35 — Admin Trace Timeline (40 s)

1. Click **Admin** (visible because you're logged in as admin; viewer role is blocked at the middleware layer).
2. Click **View Trace** next to the job you just uploaded.
3. Walk through the timeline:
   - **Blue** dots = Postgres `upload_jobs` status transitions
   - **Orange** dots = MongoDB `workflow_logs` audit entries
   - **Purple** dots = `fact_predictions` ML outputs
   - **Green** dots = `fact_recommendations` AI actions

> "Every event from every data store is collapsed into a single chronological
> timeline. A support engineer can see in one glance exactly what happened
> across four different databases for any given pipeline run."

4. Click a purple dot → expand the raw JSON panel.
5. Copy the Job ID using the copy button.

---

### 2:15 — Reports and download (20 s)

1. Navigate to `/reports`.
2. Show the generated PDF report in the table.
3. Click **Download PDF** — the browser downloads the file.

> "The report is generated on-demand by the internal endpoint, combining
> KPIs from Postgres, ML predictions, and MongoDB recommendations into a
> ReportLab-generated PDF."

---

### 2:35 — Architecture summary (25 s)

> "The single entry point is Caddy — it terminates TLS and routes
> `/api/*` to FastAPI, everything else to Next.js. Services talk only on
> the internal Docker bridge network. The admin endpoints are protected
> by JWT role claims validated on both the Next.js middleware layer and
> the FastAPI layer — no client-side-only checks.
>
> GitHub Actions runs pytest, `next build`, and `docker compose config`
> on every PR before merge."

---

## Appendix — Interviewer Q&A

| Q | 30-second A |
|---|---|
| "How do you handle ML model versioning?" | MLflow tracks every training run, compares MAE/anomaly score, and automatically promotes the better model to the `production` alias. The predict endpoint always loads the `@production` alias — no manual promotion steps. |
| "What happens if the Anthropic API is down?" | The recommendation service catches the exception after 3 retries with exponential back-off, falls back to the rule-based generator, and stores the result with `status="fallback"`. The pipeline never blocks on the LLM. |
| "How would you scale this horizontally?" | Backend and frontend are stateless — sessions in Redis, files in a shared volume. Scale them with `docker compose --scale backend=3`. Caddy load-balances automatically. Postgres and MongoDB would move to managed services. |
| "How do you guarantee the pipeline completes?" | Every stage transition is written to Postgres (durable), every audit event to MongoDB. If the process crashes mid-run the job stays in its last-written status. A restart resumes from the dead-letter state visible in the admin trace. |

---

## Resume Bullets

> Pick the 3 that best match the role you're applying for. All are
> accurate descriptions of the code in this repository.

---

**1. Pipeline Orchestration & Event-Driven ETL**

> Designed and implemented a 6-stage ETL pipeline (validate → clean → store → model → recommend → notify) as a FastAPI `BackgroundTask` chain, with every stage transition audited to MongoDB and surfaced in a cross-database admin trace timeline spanning Postgres, MongoDB, and MLflow.

---

**2. MLOps — Model Registry, Promotion Logic, and Predictions API**

> Built an MLflow-backed model registry for sales-forecast (GradientBoostingRegressor) and anomaly-detection (IsolationForest); automated production promotion by comparing MAE and anomaly score across runs; exposed a predictions API that writes to `fact_predictions` and triggers Claude-powered recommendations with a rule-based fallback when the LLM is unavailable.

---

**3. System Design — Single Entry Point, Least-Privilege Service Boundaries**

> Architected a multi-service platform (Next.js → Caddy → FastAPI / n8n / ML service / Superset) with a single TLS-terminating reverse proxy as the only public surface; enforced least-privilege boundaries by validating JWT role claims independently on both the Next.js middleware layer and the FastAPI router guards, and isolated all inter-service traffic on an internal Docker bridge network with no published ports.
