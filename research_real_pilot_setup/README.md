# TLMS Real Pilot Runbook

## 1. Prepare the approved bank

Place `TLMS_OpenLicense_QuestionBank_80_v1.xlsx` on the machine. It must contain
20 PRE, 20 POST and 40 TRAIN rows and pass the importer validation documented in
`backend/app/scripts/setup_real_pilot.py`.

```powershell
docker cp .\TLMS_OpenLicense_QuestionBank_80_v1.xlsx tlms-backend:/tmp/TLMS_OpenLicense_QuestionBank_80_v1.xlsx
$commit = git rev-parse HEAD
docker compose exec -T backend python -m app.scripts.setup_real_pilot --workbook /tmp/TLMS_OpenLicense_QuestionBank_80_v1.xlsx --git-commit $commit
```

The command is idempotent. It reuses a complete imported bank and refuses to
overwrite an incomplete or conflicting bank.

## 2. Verify setup

```powershell
docker compose exec -T backend python -m app.scripts.research_readiness_check --study-code TLMS_ADAPTIVE_REAL_PILOT_2026
```

Confirm PRE and POST IDs are present, TRAIN count is 40 and source/license/QA
coverage is 100%.

## 3. Enroll selected real users

Fill `research_real_pilot_setup/real_participants_to_enroll.csv`. Lookup supports
exact email, student ID or internal user UUID. Display names are intentionally
unsupported because they are not unique.

```csv
identifier_type,identifier,allow_mentor
email,user1@example.com,false
student_id,123456789,false
```

Candidate and member accounts are eligible by default. A mentor row requires
`allow_mentor=true`. Admin, inactive and explicit TEST/DEMO/SEED accounts are
skipped. The tool never discovers or enrolls every user automatically.

Copy the allowlist into the container and run dry-run first:

```powershell
docker cp .\research_real_pilot_setup\real_participants_to_enroll.csv tlms-backend:/tmp/real_participants_to_enroll.csv

docker compose exec -T backend python -m app.scripts.enroll_real_pilot_participants `
  --input /tmp/real_participants_to_enroll.csv `
  --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 `
  --output /tmp/enrollment_report.csv `
  --dry-run

docker cp tlms-backend:/tmp/enrollment_report.csv .\research_real_pilot_setup\enrollment_report.csv
```

Review the masked report. Only after approval, run apply explicitly:

```powershell
docker compose exec -T backend python -m app.scripts.enroll_real_pilot_participants `
  --input /tmp/real_participants_to_enroll.csv `
  --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 `
  --output /tmp/enrollment_report.csv `
  --apply

docker cp tlms-backend:/tmp/enrollment_report.csv .\research_real_pilot_setup\enrollment_report.csv
```

Apply creates only a `ResearchParticipation` with group `ADAPTIVE`, origin
`REAL`, and consent `NOT_REQUESTED`. Repeated enrollment is skipped without
changing participant code, consent, progress or study assignment. It does not
create or relabel attempts, mastery events, decisions, exams, surveys, tasks,
quests, XP or roadmap history.

## 4. Record participant consent

The participant signs in and calls:

`PATCH /api/v1/research/my-consent`

```json
{"consent_status": "GRANTED"}
```

Use `DECLINED` when consent is refused and `WITHDRAWN` when previously granted
consent is withdrawn. Those participants are excluded from the default REAL export.

Research flow:

```text
Admin enroll
  -> Participant login
  -> Participant grants consent
  -> PRE 20
  -> Adaptive TRAIN >=20
  -> POST 20
  -> Survey
  -> Export research dataset
```

## 5. Participant flow

1. Open the PRE exam using the ID returned by the setup command.
2. Complete all 20 PRE questions.
3. Use `/candidate/questions` for TRAIN. Every answer must go through the official
   Question API; do not insert attempts directly.
4. Complete at least 20 TRAIN attempts; 30-40 are preferred.
5. Open the POST exam. The backend rejects POST before 20 TRAIN attempts.
6. Mentor/admin calls `POST /api/v1/research/participants/{participant_code}/complete`.

The completion endpoint rejects incomplete participants.

## 6. TEST dry-run

Use the idempotent service-flow dry-run. It creates or reuses one dedicated TEST
account, records explicit consent, completes PRE, at least 20 TRAIN submissions,
POST and the participant lifecycle. It never inserts attempt rows directly.

```powershell
docker compose exec -T backend python -m app.scripts.run_real_pilot_dry_run
```

Do not change TEST records to REAL.

## 7. Export after the pilot

```powershell
docker compose exec -T backend python -m app.scripts.export_real_pilot_dataset --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 --output /tmp/research_real_pilot_export
docker cp tlms-backend:/tmp/research_real_pilot_export .\research_real_pilot_export
```

The default exporter includes only consented REAL participants and post-consent
events. It does not export names, email, phone, MSSV, raw user IDs or answer text.
