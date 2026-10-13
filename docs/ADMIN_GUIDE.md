# CLAIM LAGOS – Administrator Guide

## First-time setup (Hostinger KVM 2)

1. Upload project to VPS, install Docker + Docker Compose.
2. `cd claim-lagos/infra`
3. `cp ../backend/.env.example ../backend/.env` — set strong `SECRET_KEY`, DB password, MinIO keys.
4. `docker compose up -d --build`
5. Seed data:
   ```bash
   docker compose exec api python /scripts/seed_geo_public.py
   docker compose exec api python /scripts/seed_admin.py
   ```
6. Login: `admin@claimlagos.local` / password from seed (change immediately).
7. Point domain DNS to VPS; enable HTTPS (Certbot or Hostinger SSL).

## Roles

| Role | Typical access |
|------|----------------|
| super_admin | Everything |
| campaign_director | Situation Room, reports |
| director_new_media | Full ops modules |
| situation_room_manager | Alerts, recommendations |
| digital_ads_manager | Ads |
| content_manager | CREATE, content approval |
| volunteer_coordinator | Ambassadors, tasks |
| digital_ambassador | My Tasks only |
| read_only_executive | View Situation Room / reports |

Assign roles in DB (`user_roles`) or extend admin UI later.

## Credentials vault

Platform API keys live in `.env` (never commit):

- `X_BEARER_TOKEN`, `META_ACCESS_TOKEN`, `YOUTUBE_API_KEY`, `TIKTOK_ACCESS_TOKEN`, Google Ads vars

Empty keys → synthetic Listen/Ads data for testing.

## Backups

```bash
sudo mkdir -p /var/backups/claim-lagos
# Daily cron
0 2 * * * BACKUP_DIR=/var/backups/claim-lagos /path/to/claim-lagos/scripts/backup.sh
```

Restore: `scripts/restore.sh <file.sql.gz>` (type YES to confirm).

## Monitoring

```bash
docker compose ps
docker stats
curl -s http://localhost/health
```

Grafana/Prometheus optional (commented in compose due to RAM).

## Security checklist

- [ ] Changed all default passwords and SECRET_KEY
- [ ] HTTPS enabled
- [ ] Firewall: only 80/443 (and SSH) open
- [ ] Rate limiting active (middleware)
- [ ] Admin MFA planned (field exists; enforce in next hardening pass)
- [ ] Backups verified weekly
- [ ] No automated public publishing enabled (by design)
