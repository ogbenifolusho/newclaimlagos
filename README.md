# CLAIM LAGOS

**Digital Intelligence, Digital Operations & Situation Room Platform**  
New Media Directorate · APC Lagos State Campaign Council · PBAT-KOH 2027

## Hosting Target
Hostinger KVM 2: 2 vCPU · 8 GB RAM · 100 GB NVMe · 8 TB bandwidth

## Stack (Resource-Optimised)
- **Frontend**: Next.js 15 + React + TypeScript + Tailwind + Leaflet
- **Backend**: FastAPI (Python) + SQLAlchemy async
- **DB**: PostgreSQL 16 + PostGIS
- **Cache/Queue**: Redis 7
- **Object Storage**: MinIO
- **Proxy**: Nginx
- **AI**: sentence-transformers (CPU) + optional small local LLM (deferred on 8 GB)

OpenSearch and full Ollama are **deferred** on this VPS size. Postgres full-text + pg_trgm is used instead.

## Quick Start (on Hostinger VPS)

```bash
# 1. Clone / upload this repo
cd claim-lagos/infra

# 2. Copy and edit secrets
cp ../backend/.env.example ../backend/.env
# Edit all passwords and SECRET_KEY

# 3. Start stack
docker compose up -d --build

# 4. Seed public geo data (after postgres is healthy)
docker compose exec api python /app/../scripts/seed_geo_public.py
# or copy script into container and run

# 5. Open
# Frontend: http://YOUR_VPS_IP
# API docs: http://YOUR_VPS_IP/api/docs
# Health:   http://YOUR_VPS_IP/health
```

## Phase Status

| Phase | Status | Notes |
|-------|--------|-------|
| 0 – Alignment | Done | Constraints locked |
| 1 – Product & Architecture | Done | PRD, schema, architecture delivered |
| 2 – Design System + UI | Done (scaffold) | Situation Room page live; full design system continues |
| 3 – Platform Foundation | **In Progress** | Docker Compose, schema, FastAPI skeleton, Next.js scaffold, geo seed |
| 4 – Situation Room + Ambassadors | Next | After foundation is stable on VPS |
| 5+ | Planned | Listen, Ads, CREATE, deep AI, etc. |

## Important Rules
- **No automated public publishing.** All AI-generated content and recommendations require human approval.
- All geo records from public sources are marked `is_placeholder = TRUE`.
- Credentials for X, Meta, YouTube, Google, TikTok are placeholders until provided.

## Resource Notes for 8 GB RAM
Approximate container limits set in `docker-compose.yml`:
- Postgres ~1.5 GB
- API ~768 MB
- Frontend ~512 MB
- Worker ~512 MB
- Redis ~288 MB
- MinIO ~256 MB
- Nginx ~128 MB

Total under ~4 GB leaving headroom for OS and spikes. Monitor with `docker stats`.

## Next Immediate Work
1. Deploy Compose to Hostinger and verify health.
2. Run geo seed.
3. Implement real JWT auth + RBAC middleware.
4. Connect frontend to live API.
5. Build Ambassador registration & task flows.
6. Add Leaflet map with PostGIS data.


## Documentation
- [Admin Guide](docs/ADMIN_GUIDE.md)
- [User Guide](docs/USER_GUIDE.md)
- [Ops Runbook](docs/OPS_RUNBOOK.md)
- [Security](docs/SECURITY.md)
- [Performance](docs/PERFORMANCE.md)
- [Production Cutover](docs/PRODUCTION_CUTOVER.md)
- [Hypercare](docs/HYPERCARE.md)
- [Training Outline](docs/TRAINING_OUTLINE.md)
- [Delivery Summary](docs/DELIVERY_SUMMARY.md)


## Production verify

```bash
BASE_URL=https://your-domain ./scripts/prod_verify.sh
```

See [Production Cutover](docs/PRODUCTION_CUTOVER.md) for the full go-live checklist.
