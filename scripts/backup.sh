#!/usr/bin/env bash
# CLAIM LAGOS – Postgres backup for Hostinger VPS
# Cron example (daily 02:00): 0 2 * * * /path/to/claim-lagos/scripts/backup.sh

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/claim-lagos}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
COMPOSE_DIR="$(cd "$(dirname "$0")/../infra" && pwd)"
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="${BACKUP_DIR}/claim_lagos_${STAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Starting backup → $FILE"
cd "$COMPOSE_DIR"
docker compose exec -T postgres pg_dump -U claim -d claim_lagos | gzip > "$FILE"
echo "[$(date -Iseconds)] Backup size: $(du -h "$FILE" | cut -f1)"

# Retention
find "$BACKUP_DIR" -name "claim_lagos_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete
echo "[$(date -Iseconds)] Done. Retention ${RETENTION_DAYS} days."
