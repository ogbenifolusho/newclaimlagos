#!/usr/bin/env bash
# Usage: ./restore.sh /var/backups/claim-lagos/claim_lagos_YYYYMMDD_HHMMSS.sql.gz
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi
FILE="$1"
COMPOSE_DIR="$(cd "$(dirname "$0")/../infra" && pwd)"

echo "WARNING: This will overwrite the claim_lagos database."
read -p "Type YES to continue: " confirm
[ "$confirm" = "YES" ] || exit 1

cd "$COMPOSE_DIR"
gunzip -c "$FILE" | docker compose exec -T postgres psql -U claim -d claim_lagos
echo "Restore complete."
