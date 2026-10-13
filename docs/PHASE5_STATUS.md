# Phase 5 – Listen + Alerts + Basic Intelligence — COMPLETE

**Completed**: 2026-10-13

## Delivered

### Ingestion (placeholders)
- Connectors for X, Meta (FB+IG), YouTube, TikTok
- Uses env credentials when present; otherwise **synthetic posts** so the pipeline is fully testable
- Process pipeline: language heuristic, sentiment, topics, keyword match, bot heuristic

### Intelligence (CPU-friendly, no GPU)
- Rule-based sentiment (positive / neutral / negative / mixed)
- Topic classification: economy, roads, housing, education, healthcare, security, governance, transportation
- Keyword matching against active rules
- Simple bot suspicion signals

### Keyword monitoring
- CRUD-style create + list keyword rules
- Demo seed: Transport, Governance, Economy
- Platforms filterable per rule

### Alerts
- Auto-created when keyword match + negative/mixed sentiment
- Stored in DB, listed, acknowledge endpoint
- Pushed to Situation Room via WebSocket `publish_alert`
- Situation Room live alerts now read from Listen DB

### APIs
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/v1/listen/keywords | Create rule |
| GET | /api/v1/listen/keywords | List rules |
| POST | /api/v1/listen/keywords/seed-demo | Seed demo rules |
| POST | /api/v1/listen/ingest | Run ingest (all or one platform) |
| GET | /api/v1/listen/posts | Recent posts + filters |
| GET | /api/v1/listen/alerts | Open alerts |
| POST | /api/v1/listen/alerts/{id}/ack | Acknowledge |
| GET | /api/v1/listen/stats | Counts + credential status |

### Frontend
- `/listen` page: stats, posts feed, keyword rules, alerts, Seed + Run ingest buttons

## How to exercise

```bash
# Login, then:
POST /api/v1/listen/keywords/seed-demo
POST /api/v1/listen/ingest?limit=10
GET  /api/v1/listen/posts
GET  /api/v1/listen/alerts
# Situation Room will show new alerts; WebSocket pushes on ingest
```

## Next: Phase 6
Digital Ads + CREATE + Amplify/Influence workflows
- Ads lifecycle placeholders (Meta, Google, X, TikTok)
- CREATE calendar + AI draft (approval only)
- Amplify/Influence rapid-response queues
