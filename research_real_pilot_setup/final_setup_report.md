# TLMS Adaptive Real Pilot - Final Setup Report

Generated: 2026-11-19 (Asia/Saigon)

## Final Status

**REAL PILOT READY FOR DATA COLLECTION: YES**

The technical readiness check has no setup or dry-run blockers. There are no
REAL participants or REAL observations yet; that is expected before recruitment
and is not a technical failure.

## Required Summary

```text
Study code: TLMS_ADAPTIVE_REAL_PILOT_2026

Study status: PILOT

Alembic head: 036_real_pilot_question_bank (head)

Question Bank:
Total: 80
PRE: 20
TRAIN: 40
POST: 20

PRE exam ID: cf7c84eb-269f-4d0b-8bfa-542923bfc5f3
POST exam ID: 4683fd20-876b-4fae-a091-b133e304b7dd

Adaptive algorithm version: adaptive-v1
Selection policy version: question-selection-v1

Dry-run TEST participant: P000001
PRE completed: YES
TRAIN attempts: 20
POST completed: YES

question_attempt_history rows: 20
skill_mastery_history rows: 20
adaptive_decision_history rows: 23

response_time:
VALID: 18
MISSING_START: 0
INVALID_CLOCK: 0
OUTLIER: 2

Exporter: PASS

TEST excluded from REAL publishable: PASS

Backend tests: PASS - 116 passed
Health: PASS - backend /health 200, Swagger /docs 200, frontend 200
Git diff check: PASS - no whitespace errors; Windows line-ending warnings only

REAL participants enrolled: 0
REAL observations: 0

FINAL:
REAL PILOT READY FOR DATA COLLECTION: YES

Remaining blockers: None for technical data collection readiness.
```

## Workbook Validation

- Workbook: `TLMS_OpenLicense_QuestionBank_80_v1.xlsx`
- Canonical sheet: `Question_Bank_80`
- Unique question IDs: 80/80
- PRE / TRAIN / POST overlap: 0 / 0 / 0
- PRE/POST matched pairs: 20 complete pairs
- Provenance: 80/80 `SOURCE_VERIFIED`
- Content review: 80/80 `AI_PRECHECKED`
- License: 80/80 `CC BY-NC-SA 4.0`
- Source and license URLs: 100% present
- `human_spotcheck=PENDING` and `pilot_eligible=NO` were not treated as blockers,
  in accordance with the current research protocol.

Question items were adapted from openly licensed academic teaching materials and passed internal QA checks.

No SME or expert validation is claimed.

TRAIN distribution:

| Skill | Questions |
| --- | ---: |
| Git | 8 |
| Backend | 8 |
| Database | 8 |
| Frontend | 8 |
| Problem Solving | 8 |

## Import And Assessments

The first successful import inserted 80 questions and 80 study mappings. A
subsequent normalization updated the imported question-type labels to the
existing TLMS convention (`multiple_choice` / `short_answer`). The final repeat
run reported: inserted 0, updated 0, reused 80 questions and 80 mappings,
skipped 80. No duplicate study, exam, question or mapping was created.

| Assessment | Purpose | Questions | Max score | Max attempts |
| --- | --- | ---: | ---: | ---: |
| `TLMS_REAL_PILOT_PRE_2026` | `RESEARCH_PRE` | 20 | 20.0 | 1 |
| `TLMS_REAL_PILOT_POST_2026` | `RESEARCH_POST` | 20 | 20.0 | 1 |

Research freeze:

- Git revision: `3b7301c03e2b9db4fb64051d1ab53c8d19901397`
- Question bank version: `TLMS_OpenLicense_QuestionBank_80_v1`
- Study created at: `2026-11-17T22:42:36.733931`

## Adaptive Selector Audit

The existing selection algorithm was not changed.

- Baseline average `<50` maps ability difficulty to `3.0`.
- Baseline average `50..<80` maps to `5.0`.
- Baseline average `>=80` maps to `7.5`.
- Skills are prioritized from weakest mastery upward. Without profiles, the
  fallback priority is Database, Backend, Frontend, Problem Solving.
- With a skill profile, target difficulty is:

```text
target_difficulty = 0.6 * ability_difficulty + 0.4 * current_skill_difficulty
```

- Unanswered adaptive questions are filtered first, then ranked by skill
  priority, absolute distance to target difficulty, and creation time.
- Up to 5 questions are served per selection call.
- Each new serve creates one serve session and one immutable adaptive decision;
  refresh/repeated listing reuses active sessions instead of duplicating logs.

## Research Gates And Dry-Run

Confirmed gates:

1. TRAIN requires `consent=GRANTED` and a completed PRE result.
2. POST requires completed PRE and at least 20 study TRAIN attempts.
3. Pilot completion requires consent, PRE, at least 20 TRAIN attempts and POST.

Dry-run used the production local-auth, research, certification and question
services. No attempt, mastery or decision rows were inserted directly. The TEST
participant completed PRE, 20 TRAIN attempts and POST. All 20 immutable attempts
have mastery-before/after, difficulty-before/after and algorithm snapshots.

Two response times are `OUTLIER` because their serve sessions survived a long
machine/container interruption between dry-run resumes. Timestamps were not
edited. The remaining 18/20 response times are `VALID`.

The local container had no AI API key during the run. Short-answer scoring used
the production local fallback and was correctly labeled `LOCAL_FALLBACK`; the
adaptive selector, gates and research instrumentation were still exercised.

## Export Validation

All required files exist in `research_real_pilot_export/`:

```text
00_manifest.md
00_codebook.md
01_participants.csv
02_question_bank.csv
03_question_attempts.csv
04_skill_mastery_history.csv
05_adaptive_decisions.csv
06_pre_post_results.csv
07_participant_outcomes.csv
08_participant_skill_outcomes.csv
09_survey.csv
10_data_quality.csv
11_system_method_snapshot.md
12_pilot_summary.md
13_pilot_readiness_report.md
```

The export contains 80 question-bank metadata rows and zero REAL participant,
attempt, mastery, decision, PRE/POST, outcome or survey rows. A scan found no
`P000001` or `TEST` records in publishable CSV files.

## Commands Used

```powershell
docker cp C:\Users\Chest\Downloads\TLMS_OpenLicense_QuestionBank_80_v1.xlsx tlms-backend:/tmp/TLMS_OpenLicense_QuestionBank_80_v1.xlsx
$commit = git rev-parse HEAD
docker compose exec -T backend python -m app.scripts.setup_real_pilot --workbook /tmp/TLMS_OpenLicense_QuestionBank_80_v1.xlsx --git-commit $commit
docker compose exec -T backend python -m app.scripts.run_real_pilot_dry_run
docker compose exec -T backend python -m app.scripts.research_readiness_check --study-code TLMS_ADAPTIVE_REAL_PILOT_2026
docker compose exec -T backend python -m app.scripts.export_real_pilot_dataset --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 --output /tmp/research_real_pilot_export
docker compose exec -T backend python -m pytest -q
docker compose exec -T backend alembic current
git diff --check
```

## Researcher Runbook

1. Select 10 real users.
2. Enroll users manually in `TLMS_ADAPTIVE_REAL_PILOT_2026`.
3. Participant grants consent.
4. Participant completes PRE.
5. Participant completes 20-40 TRAIN questions.
6. Participant completes POST.
7. Participant completes survey.
8. Export dataset.

Do not auto-enroll production users, auto-grant consent, convert TEST/legacy
records to REAL, or manufacture REAL attempts/results.

Prepare the explicit allowlist in `real_participants_to_enroll.csv`, then run:

```powershell
docker cp .\research_real_pilot_setup\real_participants_to_enroll.csv tlms-backend:/tmp/real_participants_to_enroll.csv

docker compose exec -T backend python -m app.scripts.enroll_real_pilot_participants `
  --input /tmp/real_participants_to_enroll.csv `
  --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 `
  --output /tmp/enrollment_report.csv `
  --dry-run

docker cp tlms-backend:/tmp/enrollment_report.csv .\research_real_pilot_setup\enrollment_report.csv
```

Review the masked report and replace `--dry-run` with `--apply` only after the
allowlist is approved. Enrollment leaves consent as `NOT_REQUESTED`, creates no
research observation, and never relabels historical activity.

After real participants finish, export with:

```powershell
docker compose exec -T backend python -m app.scripts.export_real_pilot_dataset `
  --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 `
  --output /tmp/research_real_pilot_export

docker cp tlms-backend:/tmp/research_real_pilot_export .\research_real_pilot_export
```

## Non-Blocking Warnings

- Pydantic v2 reports class-based `Config` deprecation warnings in legacy
  schemas; they do not fail tests or runtime health.
- Pytest cannot write its cache under `/app` as the non-root container user;
  test execution itself completes successfully.
- The workspace contains pre-existing uncommitted TLMS changes. The study stores
  the requested Git revision and the report separately records that the final
  working-tree diff check passed.
