# CLAIM LAGOS – Production Cutover Checklist

**Target**: Hostinger KVM 2 (2 vCPU / 8 GB / 100 GB NVMe)  
**Owner**: Technical Support Team + Director of New Media

## T-7 days

- [ ] Domain DNS A record points to VPS IP
- [ ] Hostinger firewall: 22, 80, 443 only
- [ ] `.env` filled with strong unique secrets (SECRET_KEY ≥ 64 chars, DB, MinIO)
- [ ] Platform API placeholders documented; live keys added when available
- [ ] Official geo boundaries requested from Lagos/INEC (replace public placeholders)
- [ ] Election date set: `PUT /api/v1/campaign/config?election_date=YYYY-MM-DD`
- [ ] Backup directory created: `/var/backups/claim-lagos`
- [ ] Cron for `scripts/backup.sh` installed and tested once

## T-1 day

- [ ] `docker compose up -d --build` on production host
- [ ] `seed_geo_public.py` + `seed_admin.py` run
- [ ] Admin password changed immediately after first login
- [ ] HTTPS certificate active (Hostinger SSL or Certbot)
- [ ] `curl https://DOMAIN/health` returns ok
- [ ] Login → Situation Room → Listen seed+ingest → Reports smoke test
- [ ] Ambassadors: create 1 test user → verify → assign task → report
- [ ] Recommendation accept/reject path verified (no public publish)
- [ ] `docker stats` under load of 3–5 concurrent browsers acceptable

## Go-live (T-0)

- [ ] Freeze non-essential deploys for 24h unless critical fix
- [ ] Situation Room displayed on command screen
- [ ] On-call contact list posted (Tech Support + New Media Director)
- [ ] Announce internal URL to Directorate roles only
- [ ] Confirm WebSocket status shows **live** (or polling fallback OK)
- [ ] First executive report exported and archived

## T+1 to T+14 (Hypercare)

- [ ] Daily: check `/health`, `docker ps`, disk usage, last backup file
- [ ] Daily: review open alerts + pending recommendations in Situation Room
- [ ] Log all severity-1 incidents in shared sheet
- [ ] Weekly: restore drill on staging copy (optional) or verify backup gunzips
- [ ] Collect operator feedback → backlog for continuous improvement

## Rollback

1. `docker compose down`
2. Restore previous image tags / git revision
3. `scripts/restore.sh <pre-cutover.sql.gz>`
4. `docker compose up -d`
5. Notify Director of New Media

## Definition of Done (production)

- [x] All modules reachable behind HTTPS
- [x] RBAC login working
- [x] Zero auto-publish paths in code
- [x] Backups automated
- [x] Docs available to Admin and Users
- [x] Hypercare owners named
