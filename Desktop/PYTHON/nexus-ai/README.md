# NEXUS AI — Enterprise Decision Intelligence Platform

One product, seven connected layers: Frontend -> Backend (single entry point) -> n8n automation -> PostgreSQL + MongoDB -> ML service -> Analytics (BI) -> Decision layer.

## Run locally
```
cp .env.example .env
docker compose up --build
```
- Frontend:  http://localhost:3000
- Backend:   http://localhost:8000/docs
- ML service: http://localhost:8100/docs
- n8n:       http://localhost:5678 (user/pass from .env)
- Postgres:  localhost:5432
- Mongo:     localhost:27017

## Build order
See `docs/BUILD_PROMPTS.md` for the exact ordered Claude Code prompts used to build this out phase by phase.

## Architecture
See `docs/architecture.md`.
