# CLAIM LAGOS – Hypercare (first 14 days)

## On-call rhythm

| Window | Check | Action if fail |
|--------|-------|----------------|
| Every 4h (day) | `curl /health` | Restart api/nginx; escalate if 2 fails |
| Daily 08:00 | `docker ps`, disk %, latest backup | Free disk / re-run backup |
| Daily 18:00 | Open alerts + pending recs count | Brief Situation Room Manager |
| Weekly | Review rate-limit 429 logs | Adjust limits or whitelist HQ IPs |

## Severity levels

| Sev | Example | Response |
|-----|---------|----------|
| S1 | Situation Room down during live event | Immediate restart + rollback if needed; call Super Admin |
| S2 | Ingest broken / no alerts flowing | Fix Listen worker; use manual alert entry |
| S3 | Single module UI glitch | Ticket; fix in next deploy window |
| S4 | Cosmetic / feature request | Backlog |

## Continuous improvement backlog (post-hypercare)

1. Enforce MFA on privileged roles (fields already in schema)
2. Redis-backed rate limiting
3. Official LGA/LCDA/Ward polygons → real heat maps
4. Live social/Ads API connectors when credentials issued
5. PDF/PPT report generation (reportlab / python-pptx)
6. Second VPS split (DB/search) if RAM pressure sustained
7. Partition `social_posts` by month when volume grows

## Training sessions (suggested)

1. **Executives (30 min)**: Situation Room only – KPIs, alerts, accept/reject meaning
2. **New Media ops (90 min)**: Listen, Content, CREATE, Ads, Influence, Reports
3. **Ambassador coordinators (60 min)**: Register, verify, task, leaderboard
4. **Ambassadors (30 min)**: Login, My Tasks, submit report

Use `docs/USER_GUIDE.md` as the handout.
