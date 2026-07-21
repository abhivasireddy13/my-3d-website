# NEXUS AI — Production Deployment Guide

> **Target**: A single Linux VPS (2 vCPU / 4 GB RAM minimum) running
> Docker + Compose, with a public domain name pointing at it.
> Caddy handles TLS automatically via Let's Encrypt.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [DNS configuration](#2-dns-configuration)
3. [Server setup](#3-server-setup)
4. [Clone and configure](#4-clone-and-configure)
5. [First deploy](#5-first-deploy)
6. [Seed demo data](#6-seed-demo-data)
7. [n8n workflow activation](#7-n8n-workflow-activation)
8. [End-to-end verification](#8-end-to-end-verification)
9. [Vercel frontend (optional)](#9-vercel-frontend-optional)
10. [CI/CD with GitHub Actions](#10-cicd-with-github-actions)
11. [Monitoring and logs](#11-monitoring-and-logs)
12. [Backup and restore](#12-backup-and-restore)
13. [Horizontal scaling notes](#13-horizontal-scaling-notes)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Prerequisites

| Requirement | Minimum | Notes |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Debian 12 also works |
| CPU | 2 vCPU | 4 vCPU recommended for Superset |
| RAM | 4 GB | 8 GB comfortable with all services |
| Disk | 20 GB SSD | 40 GB if you expect large CSV uploads |
| Docker | 24+ | `curl -fsSL https://get.docker.com | sh` |
| Docker Compose | v2.20+ | Bundled with Docker Desktop / Docker Engine v24 |
| Domain | Any registrar | A/AAAA record must point to the VPS IP |
| Ports open | 80, 443 | Via firewall / security group |

---

## 2. DNS configuration

Create these DNS records at your registrar (replace `203.0.113.10` with your VPS IP):

```
nexus.example.com.  A  203.0.113.10
```

Caddy will automatically provision a Let's Encrypt certificate once port 80
is reachable. No additional DNS challenge configuration is needed.

---

## 3. Server setup

```bash
# 1. Install Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in

# 2. Enable the Docker daemon at boot
sudo systemctl enable --now docker

# 3. (Recommended) enable automatic security updates
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure --priority=low unattended-upgrades

# 4. Open firewall ports
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp    # HTTP/3 (optional)
sudo ufw enable
```

---

## 4. Clone and configure

```bash
cd /opt
sudo git clone https://github.com/<your-org>/nexus-ai.git
sudo chown -R $USER:$USER nexus-ai
cd nexus-ai

# Copy the template and fill in every CHANGE_ME value
cp .env.example .env.prod
nano .env.prod          # or your preferred editor
```

### Critical values to change

| Variable | What to set |
|---|---|
| `DOMAIN` | `nexus.example.com` (your real domain) |
| `POSTGRES_PASSWORD` | Strong random password: `openssl rand -hex 20` |
| `MONGO_INITDB_ROOT_PASSWORD` | Strong random password |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `N8N_WEBHOOK_SECRET` | `openssl rand -hex 20` |
| `SUPERSET_SECRET_KEY` | `openssl rand -base64 42` |
| `SUPERSET_ADMIN_PASSWORD` | Strong password |
| `ALLOWED_ORIGINS` | `https://nexus.example.com` |
| `NEXT_PUBLIC_API_URL` | `https://nexus.example.com` |
| `ANTHROPIC_API_KEY` | From https://console.anthropic.com (optional) |

---

## 5. First deploy

```bash
cd /opt/nexus-ai

# Validate the compose config (catch typos/missing vars before starting)
docker compose -f docker-compose.prod.yml --env-file .env.prod config --quiet

# Pull base images and build custom images
docker compose -f docker-compose.prod.yml --env-file .env.prod build

# Start everything (detached)
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Watch logs until all services are healthy (~2-3 minutes)
docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f
```

Check health status:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
```

All services should show `healthy` (except `backup` which is always `running`).

---

## 6. Seed demo data

Once all services are healthy, seed 12 months of realistic sales data:

```bash
# From the VPS, via the running backend container:
docker exec nexus-ai-backend-1 python -m app.scripts.seed_demo_data

# Or point the script at the public URL from any machine:
NEXUS_API=https://nexus.example.com \
NEXUS_ML_API=http://VPS_INTERNAL_IP:8100 \
  python backend/app/scripts/seed_demo_data.py
```

The script is idempotent — safe to run multiple times.

---

## 7. n8n workflow activation

On first deploy, n8n has no user account. Run these once:

```bash
# 1. Import the 6 bundled workflows
docker exec nexus-ai-n8n-1 n8n import:workflow --separate --input=/workflows

# 2. Set up the owner account (replace with your chosen credentials)
N8N_URL="https://nexus.example.com"   # or http://VPS_IP:5678 if not behind Caddy
curl -s -X POST "$N8N_URL/rest/owner/setup" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@nexus.ai","firstName":"Nexus","lastName":"Admin","password":"YourPassword!"}'

# 3. Activate all workflows (using the Node script bundled in the repo)
docker exec nexus-ai-n8n-1 node -e "
const http = require('http');
const loginData = JSON.stringify({emailOrLdapLoginId:'admin@nexus.ai',password:'YourPassword!'});
const req = http.request({host:'localhost',port:5678,path:'/rest/login',method:'POST',
  headers:{'Content-Type':'application/json','Content-Length':loginData.length}}, res => {
  let body=''; const cookie=(res.headers['set-cookie']||[]).map(c=>c.split(';')[0]).join('; ');
  res.on('data',d=>body+=d); res.on('end',()=>{
    http.get({host:'localhost',port:5678,path:'/rest/workflows',headers:{'Cookie':cookie}},res2=>{
      let b2=''; res2.on('data',d=>b2+=d); res2.on('end',()=>{
        const wfs=JSON.parse(b2).data||[];
        wfs.forEach(w=>{
          http.get({host:'localhost',port:5678,path:'/rest/workflows/'+w.id,headers:{'Cookie':cookie}},res3=>{
            let b3=''; res3.on('data',d=>b3+=d); res3.on('end',()=>{
              const vId=JSON.parse(b3).data.versionId;
              const body=JSON.stringify({versionId:vId});
              const actReq=http.request({host:'localhost',port:5678,path:'/rest/workflows/'+w.id+'/activate',
                method:'POST',headers:{'Cookie':cookie,'Content-Type':'application/json','Content-Length':body.length}},
                res4=>{let b4='';res4.on('data',d=>b4+=d);res4.on('end',()=>{
                  const r=JSON.parse(b4);console.log((r.data&&r.data.active?'ACTIVE':'FAILED'),w.name);
                })});actReq.write(body);actReq.end();
            });
          });
        });
      });
    });
  });
}); req.write(loginData); req.end();
"
```

---

## 8. End-to-end verification

```bash
# Run the bundled E2E script against the live deployment
NEXUS_API=https://nexus.example.com python e2e_verify.py
```

Expected: `All E2E checks PASSED!`

---

## 9. Vercel frontend (optional)

If you prefer to host the Next.js frontend on Vercel and everything else
on the VPS:

```bash
# 1. Install Vercel CLI
npm i -g vercel

# 2. Set the environment variables in Vercel dashboard:
#    NEXT_PUBLIC_API_URL      = https://nexus.example.com
#    NEXT_PUBLIC_SUPERSET_URL = https://nexus.example.com/superset
#    BACKEND_URL              = https://nexus.example.com   (used by Next.js API routes)
#    INTERNAL_SECRET          = <same as N8N_WEBHOOK_SECRET in .env.prod>

# 3. Deploy from the frontend directory
cd frontend
vercel --prod
```

Also add `https://your-vercel-app.vercel.app` to `ALLOWED_ORIGINS` in `.env.prod`
and restart the backend container.

---

## 10. CI/CD with GitHub Actions

The repository includes:
- `.github/workflows/ci.yml` — runs on every PR: pytest, next build, compose config
- `.github/workflows/cd.yml` — runs on merge to main: builds and pushes images to GHCR

### Required repository secrets / variables

| Name | Where | Value |
|---|---|---|
| `GITHUB_TOKEN` | Auto-provided | Used to push to GHCR |
| `NEXT_PUBLIC_API_URL` | Repository Variable | Your public API URL |
| `NEXT_PUBLIC_SUPERSET_URL` | Repository Variable | Your Superset URL |

### VPS auto-deploy (uncomment the `deploy` job in `cd.yml`)

Add these secrets:

| Secret | Value |
|---|---|
| `SSH_HOST` | VPS IP or hostname |
| `SSH_USER` | Deploy user (e.g. `ubuntu`) |
| `SSH_KEY` | Private key (`ssh-keygen -t ed25519`) |

---

## 11. Monitoring and logs

### View logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f backend

# Filter by correlation_id (JSON logs)
docker compose -f docker-compose.prod.yml logs backend | \
  grep '"correlation_id":"abc123"'
```

### Health endpoints

| Endpoint | Service |
|---|---|
| `GET /health` | Backend (FastAPI) |
| `GET /health` (port 8100) | ML service |
| `GET /healthz` (port 5678) | n8n |
| `GET /health` (port 8088) | Superset |

### Recommended metrics to alert on

- Backend 5xx rate > 1 % → PagerDuty / Opsgenie
- Backend p99 latency > 2 s
- Postgres disk usage > 80 %
- Backup container last success > 25 h

For a lightweight setup, ship container logs to **Grafana Cloud** (free tier)
using the Loki Docker logging driver:

```bash
docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions
```

Then add to each service in `docker-compose.prod.yml`:
```yaml
logging:
  driver: loki
  options:
    loki-url: "https://logs-prod-us-central1.grafana.net/loki/api/v1/push"
    loki-username: "<your-tenant-id>"
    loki-password: "<your-api-key>"
```

---

## 12. Backup and restore

### Automated backups

The `backup` container runs `pg_dump` + `mongodump` daily at 02:00 UTC.
Backup files are stored in the `backupdata` Docker named volume and pruned
after `BACKUP_RETENTION_DAYS` (default 7).

### Manual backup

```bash
# Postgres
docker exec nexus-ai-backup-1 /backup.sh

# Or pg_dump directly
docker exec nexus-ai-postgres-1 \
  pg_dump -U nexus nexus | gzip > ~/nexus_$(date +%F).sql.gz

# MongoDB
docker exec nexus-ai-mongo-1 \
  mongodump --username nexus --password <pw> --authenticationDatabase admin \
  --archive --gzip > ~/nexus_mongo_$(date +%F).gz
```

### List existing backups

```bash
docker run --rm -v nexus-ai_backupdata:/backups alpine ls -lh /backups
```

### Restore PostgreSQL

```bash
# 1. Copy the dump to the container
docker cp nexus_20260101_020000/postgres_nexus.sql.gz nexus-ai-postgres-1:/tmp/

# 2. Drop and recreate the database
docker exec -it nexus-ai-postgres-1 \
  psql -U nexus -c "DROP DATABASE nexus; CREATE DATABASE nexus;"

# 3. Restore
docker exec nexus-ai-postgres-1 \
  sh -c "gunzip -c /tmp/postgres_nexus.sql.gz | psql -U nexus nexus"
```

### Restore MongoDB

```bash
docker cp nexus_20260101_020000/mongo.tar.gz nexus-ai-mongo-1:/tmp/
docker exec nexus-ai-mongo-1 sh -c \
  "cd /tmp && tar xzf mongo.tar.gz && \
   mongorestore --username nexus --password <pw> --authenticationDatabase admin \
   --drop /tmp/mongo/"
```

### Restore test

Run the restore procedure monthly to verify backup validity:

```bash
# Start an isolated test database container
docker run -d --name pg-restore-test \
  -e POSTGRES_USER=nexus -e POSTGRES_PASSWORD=test -e POSTGRES_DB=nexus \
  postgres:16-alpine

# Copy the most recent backup
LATEST=$(docker run --rm -v nexus-ai_backupdata:/b alpine \
  ls -1t /b | head -1)
docker run --rm -v nexus-ai_backupdata:/b --network container:pg-restore-test \
  postgres:16-alpine sh -c \
  "gunzip -c /b/${LATEST}/postgres_nexus.sql.gz | \
   psql -h localhost -U nexus nexus"

# Spot-check a table
docker exec pg-restore-test psql -U nexus nexus -c "SELECT COUNT(*) FROM upload_jobs;"
docker rm -f pg-restore-test
```

---

## 13. Horizontal scaling notes

The following services are **stateless** and can be scaled horizontally
behind a load balancer:

| Service | Stateless? | Notes |
|---|---|---|
| `backend` | Yes | Session state in Redis; file uploads in shared `storage` volume |
| `ml-service` | Yes | Model artifacts in shared `mlflowdata` volume |
| `frontend` | Yes | No server-side state; SSR proxy reads cookies |
| `caddy` | Yes (mostly) | Caddy stores TLS certs in `caddy_data`; use a shared NFS volume or a Caddy cluster in HA mode |

**Stateful services** (scale with care):

| Service | Notes |
|---|---|
| `postgres` | Use managed RDS / Cloud SQL or a Patroni cluster |
| `mongo` | Use a replica set or MongoDB Atlas |
| `redis` | Use Redis Sentinel or ElastiCache |
| `n8n` | Multi-main mode requires a license; use single instance or queue mode |

To run 3 backend replicas:
```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod \
  up -d --scale backend=3
```

Caddy automatically load-balances to all healthy backend replicas.

---

## 14. Troubleshooting

### Service fails to start

```bash
docker compose -f docker-compose.prod.yml logs <service>
```

| Symptom | Likely cause | Fix |
|---|---|---|
| `FATAL: database "nexus" does not exist` | Postgres not initialised | Remove `pgdata` volume and restart |
| `connection refused` on startup | Dependency not yet healthy | Increase `start_period` in healthcheck |
| `No module named '...'` | Image not rebuilt after requirements change | `docker compose build <service>` |
| `ModuleNotFoundError: pydantic_settings` | Stale ml-service image | `docker compose build ml-service` |

### Caddy TLS fails

```bash
docker logs nexus-ai-caddy-1 | grep -i "error\|tls\|cert"
```

- Ensure ports 80 and 443 are open in the firewall.
- Ensure the domain A record resolves to the VPS IP.
- Caddy retries certificate issuance automatically; wait 5 minutes.

### Backend returns 500

```bash
docker logs nexus-ai-backend-1 | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        r = json.loads(line)
        if r.get('level') in ('ERROR', 'CRITICAL'):
            print(r['timestamp'], r['message'], r.get('exception', ''))
    except: pass
"
```

### Database migration fails on startup

```bash
docker exec nexus-ai-backend-1 alembic history
docker exec nexus-ai-backend-1 alembic current
docker exec nexus-ai-backend-1 alembic upgrade head
```

If a migration is broken, roll back:
```bash
docker exec nexus-ai-backend-1 alembic downgrade -1
```

### Pipeline stuck in "validating" forever

- n8n webhooks not registered → check n8n is healthy and workflows are active.
- The backend ETL runs locally regardless of n8n; only predictions require n8n.
- Check `workflow_logs` in MongoDB: `docker exec nexus-ai-mongo-1 mongosh`

### Reset admin password

```bash
docker exec nexus-ai-backend-1 python -c "
from app.db.postgres import SessionLocal
from app.models.user import User
from app.core.security import hash_password
db = SessionLocal()
u = db.query(User).filter(User.email == 'admin@nexus.ai').first()
u.hashed_password = hash_password('NewPassword123!')
db.commit()
print('Password reset OK')
"
```

### Disk space full

```bash
# Remove dangling images and stopped containers
docker system prune -f

# Check volume sizes
docker system df -v

# Emergency: remove old backup snapshots
docker run --rm -v nexus-ai_backupdata:/b alpine \
  find /b -mindepth 1 -maxdepth 1 -type d -mtime +3 -exec rm -rf {} \;
```
