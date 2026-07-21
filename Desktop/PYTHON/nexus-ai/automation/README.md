# Automation Workflows (n8n)

Import these via n8n UI: Settings -> Import from File, or copy into the mounted `/workflows` volume and import from there.

| File | Trigger | Purpose | Calls |
|---|---|---|---|
| 01-data-validation.json | webhook `validate-upload` (from backend `POST /uploads`) | schema/null/duplicate/business-rule checks | callback to `backend:8000/internal/pipeline-callback` |
| 02-data-cleaning-etl.json (build next) | on validation success | standardize, dedupe, load into Postgres dimensional model, audit copy to Mongo | Postgres node, Mongo node |
| 03-ml-trigger.json (build next) | on ETL success | call ML service predict endpoints, write `fact_predictions` | `ml-service:8100`, Postgres node |
| 04-dashboard-refresh.json (build next) | on prediction write | refresh Power BI dataset / invalidate Superset cache | Power BI REST API or Superset API |
| 05-report-generation.json (build next) | on prediction write | assemble PDF/Excel report | backend report endpoint |
| 06-notifications.json (build next) | on pipeline complete or anomaly flagged | email/Slack notify | Email/Slack node |

Only workflow 01 is scaffolded as a real, importable n8n JSON file (minimal but valid: webhook -> function -> callback). The rest are described here with their trigger/inputs/outputs so Claude Code (or you, in the n8n UI) can build them node-by-node — see `docs/BUILD_PROMPTS.md` Prompt 3-6.

Every workflow must:
1. Accept/propagate a `job_id` (the `correlation_id`) through every node.
2. Write a step entry to MongoDB `workflow_logs` on start and completion.
3. Call the backend's `/internal/pipeline-callback` with the new status on completion/failure.
