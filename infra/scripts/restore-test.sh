#!/usr/bin/env bash
# Restore a backup into a throw-away database and sanity-check it. Never touches the live database.
# Usage: AGE_IDENTITY=/path/to/age-key.txt infra/scripts/restore-test.sh /var/backups/hospital/hospital-XXXX.dump.age
set -euo pipefail
FILE=${1:?backup file}; : "${AGE_IDENTITY:?path to age private key}"
cd "$(dirname "$0")/.."
set -a; . ../.env.prod; set +a
COMPOSE="docker compose -f docker-compose.prod.yml --env-file ../.env.prod"
TMPDB="restore_test_$(date +%s)"
sha256sum -c "$FILE.sha256" >/dev/null 2>&1 && echo "checksum ok" || echo "warning: checksum missing/mismatch"
$COMPOSE exec -T db psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $TMPDB" >/dev/null
trap '$COMPOSE exec -T db psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $TMPDB" >/dev/null' EXIT
age -d -i "$AGE_IDENTITY" "$FILE" | $COMPOSE exec -T db pg_restore -U "$POSTGRES_USER" -d "$TMPDB" --no-owner --exit-on-error
Q() { $COMPOSE exec -T db psql -U "$POSTGRES_USER" -d "$TMPDB" -Atc "$1"; }
USERS=$(Q "select count(*) from users"); PATIENTS=$(Q "select count(*) from patients"); MIG=$(Q "select version_num from alembic_version")
[ "$USERS" -ge 1 ] || { echo "RESTORE CHECK FAILED: no users" >&2; exit 1; }
echo "restore ok: users=$USERS patients=$PATIENTS alembic=$MIG"
