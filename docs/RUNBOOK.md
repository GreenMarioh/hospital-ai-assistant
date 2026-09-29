# Runbook

Audience: the person operating the deployed system. Commands run on the server in `/opt/hospital/infra` unless stated.

## 0. Architecture in one paragraph
Caddy (80/443, automatic Let's Encrypt certificates) routes `/api/*`, `/healthz`, `/readyz` to the FastAPI backend and everything else to the Next.js frontend. The backend talks to Postgres 16 (and Redis for shared rate-limit counters). A separate `worker` container runs APScheduler (appointment reminders). Only Caddy publishes ports.

## 1. First-time setup (new server)
1. Create a VM (Ubuntu 22.04/24.04, 2 vCPU / 4 GB is enough for a small clinic) and point DNS `A`/`AAAA` for your domain at it.
2. As root: `curl -fsSL https://raw.githubusercontent.com/<you>/<repo>/main/infra/scripts/provision.sh | bash` (or copy and run it). It installs Docker, enables the firewall (only 22/80/443), fail2ban, unattended upgrades, key-only SSH, log rotation, and the 02:17 UTC backup cron. **Keep a second SSH session open while it changes sshd.**
3. Add the CI deploy public key to `/home/deploy/.ssh/authorized_keys`. Clone the repo to `/opt/hospital` (owned by `deploy`).
4. `cp .env.prod.example .env.prod && chmod 600 .env.prod` and fill it in: `DOMAIN`, `ACME_EMAIL`, `GHCR_OWNER`, strong random `SECRET_KEY`, `FIELD_ENCRYPTION_KEY` (`python3 -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"`), DB passwords (and the two DB URLs), `ANTHROPIC_API_KEY`, SMTP settings (`EMAIL_BACKEND=smtp`), `ADMIN_EMAIL`/`ADMIN_PASSWORD`, `BACKUP_AGE_RECIPIENT`.
   - **Back up `FIELD_ENCRYPTION_KEY` and the age private key somewhere safe and separate from the server.** Losing either means unrecoverable data / backups.
5. GitHub repo settings → Secrets (environment `production`): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY`, `GHCR_READ_TOKEN` (PAT with `read:packages`).
6. Seed the first admin and reference data (no demo data in prod because `ENVIRONMENT=prod`):
   `IMAGE_TAG=<tag> docker compose -f docker-compose.prod.yml --env-file ../.env.prod run --rm backend python -m app.seed`
   then log in and **change the admin password immediately**. Create doctors (Admin → Users, role Doctor) and have them set their weekly availability (Doctor → Availability & leave).
7. Deploy (section 2). The smoke test needs at least one doctor with availability.

## 2. Deploy
Automatic: pushing a `v*` tag (or running the *Deploy* workflow) builds and pushes images to GHCR, SSHes to the server and runs `scripts/deploy.sh <tag>`.

Manually: `./scripts/deploy.sh v1.2.3`. The script: pulls images → starts db/redis → **runs Alembic migrations** (`migrate` service, schema-owner DB role) → restarts backend/worker/frontend → waits for health → runs `scripts/smoke.sh` (register → login → book → cancel → AI triage → admin dashboard) → records the tag in `.deployed_tag`.
Caddy retries upstreams for up to 15 s, so a rolling restart is normally invisible to users (low downtime, not zero).

**Migration rule**: migrations must be backward compatible with the previous release (expand → deploy → contract in a later release), because rollback re-deploys the previous *images* and does not reverse the schema.

## 3. Rollback
- Automatic: if health or the smoke test fails, `deploy.sh` redeploys the previously recorded tag and exits non-zero (the workflow fails).
- Manual: `./scripts/deploy.sh <previous-tag>`.
- Schema rollback (rare): restore the pre-deploy backup (section 4) into a new database and repoint; do not downgrade Alembic on live data.
- Rehearsed locally (see section 8): a deliberately broken release failed the smoke test and the previous release was restored automatically.

## 4. Backups and restore
- Daily 02:17 UTC: `scripts/backup.sh` → `pg_dump -Fc | age -r $BACKUP_AGE_RECIPIENT` → `/var/backups/hospital/hospital-<UTC>.dump.age` (+ `.sha256`), keeps `BACKUP_KEEP_DAYS` (14). Plaintext never touches disk. Set `BACKUP_S3_URI` (needs `aws` CLI) to copy off-host. **Off-host copies are essential: a backup on the same disk is not a backup.**
- Uploaded documents live in the `uploads` Docker volume (or your S3 bucket if `STORAGE_BACKEND=s3`) and are **not** in the DB dump: back that volume up too (`docker run --rm -v hospital-ai_uploads:/d -v /var/backups/hospital:/b alpine tar czf /b/uploads-$(date +%F).tgz -C /d .`) or use bucket versioning.
- Test the restore at least monthly (it never touches the live DB):
  `AGE_IDENTITY=/secure/age-key.txt ./scripts/restore-test.sh /var/backups/hospital/hospital-XXXX.dump.age` → prints `restore ok: users=.. patients=.. alembic=..`.
- Real restore (disaster): provision a server, deploy, stop the app (`docker compose ... stop backend worker`), `age -d -i key.txt file.dump.age | docker compose ... exec -T db pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --no-owner`, restore the uploads volume, start the app, run the smoke test.

## 5. Monitoring and logs
- Uptime: point an external monitor (UptimeRobot, Better Stack, Uptime Kuma) at `https://<domain>/readyz` (checks DB) with alerts to on-call.
- Errors: set `SENTRY_DSN` (backend). Never enable request-body capture: payloads contain PHI.
- Logs: `docker compose -f docker-compose.prod.yml logs -f backend` (JSON lines with `request_id`; rotated at 10 MB × 5). Caddy access log: `caddy` container `/data/access.log` (rolled).
- AI health: Admin → Dashboard shows AI usage, degraded (AI-down) responses and latency.
- Certificates renew automatically (Caddy). If issuance fails, check DNS and that ports 80/443 are reachable: `docker compose logs caddy`.

## 6. Incident checklists
**Site down / 502**: `docker compose ps` → look for unhealthy containers → `logs backend` → `readyz` says DB down? check `db` health and disk space (`df -h`). Roll back if the last deploy is the trigger.
**Database disk full**: prune old backups/logs, `docker system prune` (never `--volumes`), resize disk, then investigate the growth (`audit_logs` is the usual suspect: archive rows older than your retention period).
**AI provider outage**: no action required. Triage falls back to rule-based red flags plus a "book directly" message, FAQ returns document excerpts, briefings return a structured overview, the booking assistant returns 503 and points users to manual booking. The circuit breaker re-tests after 60 s.
**Suspected credential compromise**: rotate `SECRET_KEY` (logs everyone out), disable the user (Admin → Users), review `Audit logs` filtered by that user/IP, rotate DB passwords, and follow your breach-notification policy (HIPAA/GDPR timelines start at discovery).
**Suspected PHI exposure**: preserve logs, restrict access, export the relevant audit log range, involve your privacy officer.
**Locked-out admin**: `docker compose run --rm backend python -c "..."` to reset the hash, or run the seed with a new `ADMIN_PASSWORD` for a *new* admin email and disable the old one.
**Reminders not sending**: `docker compose logs worker`; the job is idempotent (dedupe keys in `notifications`), so restarting the worker never double-sends.

## 7. Routine maintenance
Weekly: check backups exist off-host and the disk has space. Monthly: restore test, `pip-audit`/`npm audit` (CI does it on every push), rotate admin passwords, review users. Quarterly: rotate `SECRET_KEY`/DB passwords, review audit logs for unusual access, update base images (rebuild + deploy).

## 8. Rehearse locally (what was verified)
`infra/docker-compose.rehearsal.yml` runs the *production* compose file on unprivileged ports with Caddy's internal CA:
```bash
docker build -t ghcr.io/local/hospital-ai-backend:test backend
docker build --build-arg NEXT_PUBLIC_API_URL= -t ghcr.io/local/hospital-ai-frontend:test frontend
cp .env.prod.example .env.prod   # DOMAIN=localhost, GHCR_OWNER=local, EMAIL_BACKEND=console, generated secrets
export COMPOSE_PROJECT_NAME=hospital-prod GHCR_OWNER=local COMPOSE_EXTRA="-f docker-compose.rehearsal.yml" \
       SKIP_PULL=1 SMOKE_BASE_URL=https://localhost:8443 CURL_OPTS=-k
cd infra && ./scripts/deploy.sh test          # add a demo seed first: run backend `python -m app.seed` with ENVIRONMENT=dev
```
Results recorded when this was written: migrations applied, HTTPS via Caddy, same-origin routing, smoke test passed; a broken image tag was rolled back automatically; an age-encrypted backup restored into a scratch database (12 users, 4 patients, alembic `0001`) and a wrong key was rejected.
