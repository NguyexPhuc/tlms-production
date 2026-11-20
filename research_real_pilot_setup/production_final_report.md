# TLMS Production Real Pilot Final Report

Production frontend: `https://quangphuc.id.vn` (existing deployment, HTTP 200)

Production backend: `https://tlms-api.onrender.com` (existing deployment, HTTP 200)

Production commit: `3b7301c03e2b9db4fb64051d1ab53c8d19901397` remains live. Research rollout commit `b7d7b9905722afd48d65c7eb462c08c9b0bf39d6` is not live.

Alembic revision: Not independently queryable on Render Free; research migrations were not run by the failed rollout.

Question Bank: 80 validated locally; not imported by this production rollout

PRE: 20 validated locally; production import not run

TRAIN: 40 validated locally; production import not run

POST: 20 validated locally; production import not run

Study: `TLMS_ADAPTIVE_REAL_PILOT_2026`

Status: BLOCKED BEFORE MIGRATION

Production users requested: 12

Found: PENDING

Not found: PENDING

Ready: PENDING

Dry-run: NOT RUN - production readiness gate failed

Applied enrollments: 0

REAL participants total: Not changed by this rollout

Consent NOT_REQUESTED: Not changed by this rollout

Consent GRANTED: Not changed by this rollout

Historical data converted to REAL: NO

Fake REAL data created: NO

Research UI available: NO on the current production deployment

Production readiness: NO

Production smoke test: NOT RUN - backup/deployment gate failed

Tests:

- Backend: PASS - 116 tests
- Frontend: PASS - lint has no errors; typecheck/build pass
- Health: PASS for the existing live frontend, backend health, and backend docs

FINAL:

`PRODUCTION REAL PILOT READY FOR PARTICIPANTS: NO`

Remaining blockers:

- Configure private Cloudflare R2 on Render with `S3_ENDPOINT_URL`,
  `S3_BUCKET`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY`.
- Re-run the guarded production deployment and verify backup, migrations,
  Question Bank import, study setup, readiness, and TEST-origin smoke logs.
- Deploy the matching Research UI only after the backend rollout succeeds.
- Run production readiness independently.
- Look up the 12 production accounts and review a masked dry-run report.
- Run a TEST-origin production smoke test before applying REAL enrollment.
