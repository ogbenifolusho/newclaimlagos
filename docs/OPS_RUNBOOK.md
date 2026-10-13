# CLAIM LAGOS – Operational Runbook

## Service topology (Docker Compose)

| Container | Role | Mem limit |
|-----------|------|-----------|
| claim-nginx | Reverse proxy | 128m |
| claim-frontend | Next.js | 512m |
| claim-api | FastAPI | 768m |
| claim-worker | Background jobs | 512m |
| claim-postgres | PostGIS | 1536m |
| claim-redis | Cache/queue | 288m |
| claim-minio | Object storage | 256m |

## Common incidents

### High memory
```bash
docker stats
docker compose restart worker api
# If still tight: stop minio console ports, reduce ingest batch size
```

### API 502
```bash
docker compose logs api --tail 100
docker compose restart api nginx
```

### Database full / slow
```bash
docker compose exec postgres psql -U claim -d claim_lagos -c "VACUUM ANALYZE;"
# Archive old social_posts if needed
```

### WebSocket offline
- Check nginx Upgrade headers
- Confirm API process up
- Client falls back to 30s polling on Situation Room

### Rate limited (429)
- Auth: 20/min per IP
- General: 120/min per IP
- Legitimate burst: wait 60s or whitelist at nginx

## Deploy update
```bash
cd claim-lagos
git pull   # or upload files
cd infra
docker compose up -d --build
```

## Health probes
- `GET /health` → `{"status":"ok"}`
- `GET /api/docs` → OpenAPI UI

## Disaster recovery
1. Provision new VPS / same Hostinger rebuild
2. Install Docker, restore project files + `.env`
3. `docker compose up -d`
4. `scripts/restore.sh <latest.sql.gz>`
5. Verify login + Situation Room
6. RPO target: last daily backup (≤24h); RTO: ~1–2 hours with prepared image

## Escalation
1. Technical Support Team (compose/logs)
2. Director of New Media (ops decisions)
3. Super Admin (credentials / restore authority)
