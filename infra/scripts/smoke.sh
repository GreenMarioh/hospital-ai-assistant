#!/usr/bin/env bash
# End-to-end smoke test against a running deployment:
# register -> login -> book appointment -> AI triage -> admin dashboard.
# Usage: BASE_URL=https://host ADMIN_EMAIL=... ADMIN_PASSWORD=... infra/scripts/smoke.sh
set -euo pipefail
BASE_URL=${BASE_URL:?set BASE_URL}
ADMIN_EMAIL=${ADMIN_EMAIL:?}
ADMIN_PASSWORD=${ADMIN_PASSWORD:?}
J='Content-Type: application/json'
fail() { echo "SMOKE FAIL: $*" >&2; exit 1; }
jget() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)"; }

curl -fsS "$BASE_URL/healthz" >/dev/null || fail "healthz"
curl -fsS "$BASE_URL/readyz" >/dev/null || fail "readyz"

EMAIL="smoke.$(date +%s)@example.com"; PW="Smoke!Test-$(date +%s)"
REG=$(curl -fsS -X POST "$BASE_URL/api/auth/register" -H "$J" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\",\"first_name\":\"Smoke\",\"last_name\":\"Test\",\"date_of_birth\":\"1990-01-01\"}") || fail "register"
LOGIN=$(curl -fsS -X POST "$BASE_URL/api/auth/login" -H "$J" -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\"}") || fail "login"
TOKEN=$(echo "$LOGIN" | jget "d['access_token']")
AUTH="Authorization: Bearer $TOKEN"

DOCTOR=$(curl -fsS "$BASE_URL/api/doctors" -H "$AUTH" | jget "d[0]['id']") || fail "doctors"
FROM=$(date -u +%F); TO=$(date -u -d '+13 days' +%F)
SLOT=$(curl -fsS "$BASE_URL/api/doctors/$DOCTOR/slots?from=$FROM&to=$TO" -H "$AUTH" | jget "d[0]['starts_at']") || fail "slots (is a doctor seeded with availability?)"
APPT=$(curl -fsS -X POST "$BASE_URL/api/appointments" -H "$J" -H "$AUTH" -H "Idempotency-Key: smoke-$(date +%s)" \
  -d "{\"doctor_id\":\"$DOCTOR\",\"starts_at\":\"$SLOT\",\"reason\":\"smoke test\"}") || fail "book"
[ "$(echo "$APPT" | jget "d['status']")" = "booked" ] || fail "appointment not booked"

# AI triage: the emergency red-flag path is deterministic and works even when the LLM is down.
TRIAGE=$(curl -fsS -X POST "$BASE_URL/api/ai/triage/message" -H "$J" -H "$AUTH" -d '{"message":"I have severe chest pain"}') || fail "triage"
[ "$(echo "$TRIAGE" | jget "d['emergency']")" = "True" ] || fail "triage did not flag emergency"

ADMIN_TOKEN=$(curl -fsS -X POST "$BASE_URL/api/auth/login" -H "$J" -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" | jget "d['access_token']") || fail "admin login"
curl -fsS "$BASE_URL/api/admin/analytics/summary" -H "Authorization: Bearer $ADMIN_TOKEN" | jget "d['appointments']['totals']['total']" >/dev/null || fail "admin dashboard"
curl -fsS -o /dev/null "$BASE_URL/login" || fail "frontend"
echo "SMOKE OK ($BASE_URL)"
