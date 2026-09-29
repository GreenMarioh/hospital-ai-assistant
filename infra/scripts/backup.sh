#!/usr/bin/env bash
# Daily encrypted Postgres backup. Requires `age` (https://age-encryption.org) and BACKUP_AGE_RECIPIENT.
# Cron example (server): 17 2 * * * /opt/hospital/infra/scripts/backup.sh >> /var/log/hospital-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ../.env.prod; set +a
: "${BACKUP_AGE_RECIPIENT:?set BACKUP_AGE_RECIPIENT (age public key)}"
DIR=${BACKUP_DIR:-/var/backups/hospital}; KEEP=${BACKUP_KEEP_DAYS:-14}
mkdir -p "$DIR"; umask 077
OUT="$DIR/hospital-$(date -u +%Y%m%dT%H%M%SZ).dump.age"
COMPOSE="docker compose -f docker-compose.prod.yml ${COMPOSE_EXTRA:-} --env-file ../.env.prod"
# custom-format dump, encrypted on the fly: plaintext never touches disk
$COMPOSE exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc | age -r "$BACKUP_AGE_RECIPIENT" -o "$OUT"
[ -s "$OUT" ] || { echo "backup empty" >&2; rm -f "$OUT"; exit 1; }
sha256sum "$OUT" > "$OUT.sha256"
if [ -n "${BACKUP_S3_URI:-}" ]; then aws s3 cp "$OUT" "$BACKUP_S3_URI/" && aws s3 cp "$OUT.sha256" "$BACKUP_S3_URI/"; fi
find "$DIR" -name 'hospital-*.dump.age*' -mtime "+$KEEP" -delete
echo "backup ok: $OUT ($(du -h "$OUT" | cut -f1))"
