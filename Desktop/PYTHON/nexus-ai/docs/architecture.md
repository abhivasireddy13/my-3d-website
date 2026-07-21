# NEXUS AI — Architecture

Single entry point rule: the frontend only ever talks to the backend. n8n, the ML
service, both databases, and the BI layer are internal and reached only via the
backend or via n8n orchestration. This is what makes the platform feel/behave
like one product instead of a pile of tools.

```
Next.js (3000) --HTTPS/JWT--> FastAPI backend (8000)
                                  |-- Postgres (5432)   structured business data
                                  |-- Mongo (27017)     raw uploads / logs / audit
                                  |-- Redis (6379)       job status cache
                                  |-- n8n (5678)         orchestration
                                        |-- ML service (8100)  predictions
                                        |-- Postgres/Mongo writes
                                        |-- BI refresh webhook
```

Every job carries a `job_id` (== `correlation_id`) from upload through validation,
cleaning, ETL, ML inference, recommendation, and notification. Trace it end to end
via `/admin/trace/{job_id}` (build in Phase 8) — this is the single feature that
proves the system is integrated end-to-end, not just modular.
