#!/usr/bin/env bash
# Production smoke verification – run after deploy
# Usage: BASE_URL=https://claim.example.com ./scripts/prod_verify.sh

set -euo pipefail
BASE="${BASE_URL:-http://localhost}"

echo "=== CLAIM LAGOS production verify against $BASE ==="

echo -n "Health... "
code=$(curl -s -o /tmp/claim_health.json -w "%{http_code}" "$BASE/health" || true)
if [ "$code" = "200" ]; then echo "OK ($code)"; else echo "FAIL ($code)"; exit 1; fi

echo -n "OpenAPI... "
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/docs" || true)
if [ "$code" = "200" ]; then echo "OK"; else echo "WARN ($code)"; fi

echo -n "Situation Room overview... "
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/situation-room/overview" || true)
if [ "$code" = "200" ]; then echo "OK"; else echo "FAIL ($code)"; exit 1; fi

echo -n "Geo hierarchy... "
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/geo/hierarchy?level=lga" || true)
if [ "$code" = "200" ]; then echo "OK"; else echo "FAIL ($code)"; exit 1; fi

echo -n "Campaign config... "
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/api/v1/campaign/config" || true)
if [ "$code" = "200" ]; then echo "OK"; else echo "WARN ($code)"; fi

echo "=== Smoke checks passed ==="
echo "Next: manual login, Listen ingest, recommendation review, backup dry-run"
