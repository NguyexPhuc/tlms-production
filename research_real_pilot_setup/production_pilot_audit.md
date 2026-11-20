# TLMS Production Pilot Audit

Audit timestamp: 2026-11-20 (Asia/Ho_Chi_Minh)

## Deployment inventory

| Component | Verified value | Evidence |
| --- | --- | --- |
| Frontend | `https://quangphuc.id.vn` | Vercel production alias and HTTP 200 |
| Frontend fallback | `https://tlms-production.vercel.app` | Vercel production alias and HTTP 200 |
| Backend | `https://tlms-api.onrender.com` | Render service `srv-dbgv22bbc2fs73bmgjj0` and HTTP 200 |
| Backend custom domain | `https://api.quangphuc.id.vn` | DNS does not currently resolve; not usable |
| Backend provider | Render Free Web Service, Singapore | Render CLI service inventory |
| Database provider | Neon PostgreSQL | Repository production deployment configuration |
| Database host | Not printed or stored in this report | Render secret; CLI does not expose it |
| Backend production commit | `3b7301c03e2b9db4fb64051d1ab53c8d19901397` | Live Render deploy `dep-dbtu9dgn74is73esqf50` |
| Frontend deployment | `dpl_EG24redjUguQWHLgFcJwPzuFQVyf` | Vercel CLI inspect |
| Environment | `APP_ENV=production`, Docker runtime | Render Blueprint |

Frontend is deployed by Vercel from the `frontend` root. Backend is deployed by
Render from `backend/Dockerfile`. Both originate from the `main` branch of
`NguyexPhuc/tlms-production`.

## Database safety

No local database will be copied or restored to production. The production
rollout uses the existing `DATABASE_URL`, additive Alembic migrations and the
idempotent reviewed Question Bank importer.

Render Free does not permit SSH or one-off jobs for this service. The current
production Alembic revision could therefore not be queried independently before
the rollout. The deployed Git commit contains migrations through `033`, but this
is not used as proof of the database revision. The deployment must stop if the
entrypoint migration log is not successful.

Migration chain to deploy, in order:

1. `034_adaptive_pilot_readiness`
2. `035_research_pilot_operations`
3. `036_real_pilot_question_bank`
4. `037_research_participant_survey`

No downgrade or skipped revision is allowed.

## Backup strategy

The rollout image contains PostgreSQL 17 `pg_dump`. Before Alembic runs, the
one-time rollout flag executes a custom-format logical backup and uploads it to
the configured private Cloudflare R2 bucket. Migration proceeds only if backup
creation and upload succeed.

Backup created: **NO**

Backup method: `pg_dump --format=custom` to private R2 object storage

Timestamp: Not applicable; no backup object was created

Two guarded deploys were attempted and stopped before Alembic:

- `dep-dbvfuvijnfac73di09bg` stopped because `STORAGE_BACKEND` was not `s3`.
- `dep-dc01j0m7bikc7395avhg` stopped because the Render service has none of
  `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, or
  `S3_SECRET_ACCESS_KEY` configured.

The deployment guard behaved correctly: no new migration, Question Bank
import, study setup, smoke data, or REAL enrollment was executed. The existing
live backend remains on commit `3b7301c03e2b9db4fb64051d1ab53c8d19901397`.

To resume, configure the four R2 values above as secret environment variables
on Render service `srv-dbgv22bbc2fs73bmgjj0`. Keep `STORAGE_BACKEND=s3`.
Do not put any credential in Git, this report, or terminal output. Then deploy
commit `b7d7b9905722afd48d65c7eb462c08c9b0bf39d6`; the entrypoint will retry the
backup before it is allowed to run Alembic.

## Pre-deployment status

- Local Question Bank validation: PASS (`PRE=20`, `TRAIN=40`, `POST=20`).
- Local Alembic head: `037_research_participant_survey`.
- Backend tests: PASS (`116 passed`).
- Frontend lint: PASS with pre-existing warnings and no errors.
- Frontend build/typecheck: PASS.
- Known dependency warning: Next.js 16.4.3 is flagged by the installed build
  tooling as affected by a security advisory. Upgrade is tracked separately and
  is not mixed into this research rollout.

## Enrollment gate

REAL enrollment remains blocked until all of these production checks pass:

- private backup created;
- migrations reach `037_research_participant_survey`;
- Question Bank import is idempotent and complete;
- production readiness reports `YES`;
- participant Research UI is deployed and healthy;
- production user lookup/dry-run is reviewed.

Current gate result: **BLOCKED BEFORE MIGRATION** because private backup
storage is not configured. No production user lookup or enrollment was run.

## Live service check after failed rollout

- `https://tlms-api.onrender.com/health`: HTTP 200
- `https://tlms-api.onrender.com/docs`: HTTP 200
- `https://quangphuc.id.vn`: HTTP 200
- `https://tlms-production.vercel.app`: HTTP 200
