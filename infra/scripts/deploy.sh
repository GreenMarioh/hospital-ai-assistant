#!/usr/bin/env bash
# Deploy an image tag on the server, run migrations, smoke test, roll back automatically on failure.
# Usage (from the infra directory on the server): ./scripts/deploy.sh <image-tag>
# Migrations must be backward compatible (expand/contract) because rollback only re-deploys the previous images.
set -euo pipefail
TAG=${1:?usage: deploy.sh <image-tag>}
cd "$(dirname "$0")/.."
ENV_FILE=../.env.prod
set -a; . "$ENV_FILE"; set +a
COMPOSE="docker compose -f docker-compose.prod.yml ${COMPOSE_EXTRA:-} --env-file $ENV_FILE"
PREV=$(cat .deployed_tag 2>/dev/null || true)

export IMAGE_TAG=$TAG
echo "==> deploying $TAG (previous: ${PREV:-none})"
[ -n "${SKIP_PULL:-}" ] || $COMPOSE pull   # SKIP_PULL=1 for local rehearsals with locally built images
$COMPOSE up -d db redis
$COMPOSE --profile tools run --rm migrate
$COMPOSE up -d --remove-orphans

echo "==> waiting for backend health"
for i in $(seq 1 40); do
  [ "$($COMPOSE ps --format '{{.Health}}' backend)" = "healthy" ] && break
  sleep 3
done

if BASE_URL="${SMOKE_BASE_URL:-https://$DOMAIN}" ADMIN_EMAIL="${ADMIN_EMAIL}" ADMIN_PASSWORD="${SMOKE_ADMIN_PASSWORD:-${ADMIN_PASSWORD}}" ./scripts/smoke.sh; then
  echo "$TAG" > .deployed_tag
  echo "==> deploy OK"
else
  echo "==> smoke test FAILED"
  if [ -n "$PREV" ]; then
    echo "==> rolling back to $PREV"
    export IMAGE_TAG=$PREV
    $COMPOSE up -d --remove-orphans
  fi
  exit 1
fi
