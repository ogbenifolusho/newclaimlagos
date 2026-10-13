# CLAIM LAGOS – Performance (Hostinger KVM 2: 2 vCPU / 8 GB)

## Design choices
- Single API worker (uvicorn)
- Postgres shared_buffers 256MB, max_connections 50
- Redis maxmemory 256mb LRU
- OpenSearch & Ollama deferred
- Listen ingest default limit 10–15 posts/platform per run
- Frontend 30s poll + optional WebSocket

## Expected capacity (order-of-magnitude)
- Concurrent dashboard users: tens, not thousands
- Social rows: hundreds of thousands manageable with indexes; partition `social_posts` if multi-million
- Ingest: batch/on-demand, not continuous firehose without more RAM/CPU

## If you outgrow 8 GB
1. Second VPS for Postgres + Redis
2. Add OpenSearch on dedicated node
3. Horizontal API replicas behind nginx
4. Redis-backed rate limiting and Celery workers

## Quick checks
```bash
docker stats --no-stream
docker compose exec postgres psql -U claim -d claim_lagos -c "SELECT relname, n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10;"
```
