"""Read-only data-quality and pilot-readiness report for adaptive research."""
import argparse
import asyncio
from collections import Counter
from typing import Optional

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.certification import AssessmentPurpose, Exam, ExamQuestion, ExamResult
from app.models.development import (
    AdaptiveDecisionHistory,
    Question,
    QuestionAttemptHistory,
    QuestionVerificationStatus,
    ResearchConsentStatus,
    ResearchDataOrigin,
    ResearchExperimentGroup,
    ResearchFixedQuestionSequence,
    ResearchParticipation,
    ResearchQuestionPhase,
    ResearchStudy,
    ResearchStudyQuestion,
    ResearchStudyStatus,
    SkillMasteryHistory,
)


def _value(value):
    return value.value if hasattr(value, "value") else value


def _coverage(count: int, total: int) -> float:
    return round(count / total * 100, 2) if total else 0.0


async def readiness_report(study_code: Optional[str] = None) -> dict:
    async with AsyncSessionLocal() as db:
        participation_query = select(ResearchParticipation)
        if study_code:
            participation_query = participation_query.where(ResearchParticipation.study_code == study_code)
        participations = list((await db.execute(participation_query)).scalars().all())
        user_ids = [item.user_id for item in participations]
        questions = []
        study_question_links = []
        attempts = list((await db.execute(
            select(QuestionAttemptHistory).where(QuestionAttemptHistory.user_id.in_(user_ids))
        )).scalars().all())
        decisions = list((await db.execute(
            select(AdaptiveDecisionHistory).where(AdaptiveDecisionHistory.user_id.in_(user_ids))
        )).scalars().all())
        study = None
        pre_exam = None
        post_exam = None
        pre_exam_question_ids = set()
        post_exam_question_ids = set()
        sequence_items = []
        if study_code:
            study = (await db.execute(
                select(ResearchStudy).where(ResearchStudy.study_code == study_code)
            )).scalar_one_or_none()
            sequence_items = list((await db.execute(
                select(ResearchFixedQuestionSequence).where(
                    ResearchFixedQuestionSequence.study_code == study_code,
                    ResearchFixedQuestionSequence.active.is_(True),
                )
            )).scalars().all())
            study_question_links = list((await db.execute(
                select(ResearchStudyQuestion).where(
                    ResearchStudyQuestion.study_code == study_code,
                )
            )).scalars().all())
            question_ids = [item.question_id for item in study_question_links]
            questions = list((await db.execute(
                select(Question).where(Question.id.in_(question_ids))
            )).scalars().all()) if question_ids else []
            if study is not None and study.pre_exam_id is not None:
                pre_exam = await db.get(Exam, study.pre_exam_id)
                pre_exam_question_ids = set((await db.execute(
                    select(ExamQuestion.question_id).where(
                        ExamQuestion.exam_id == study.pre_exam_id
                    )
                )).scalars().all())
            if study is not None and study.post_exam_id is not None:
                post_exam = await db.get(Exam, study.post_exam_id)
                post_exam_question_ids = set((await db.execute(
                    select(ExamQuestion.question_id).where(
                        ExamQuestion.exam_id == study.post_exam_id
                    )
                )).scalars().all())
        else:
            questions = list((await db.execute(select(Question))).scalars().all())
        mastery_events = list((await db.execute(
            select(SkillMasteryHistory).where(SkillMasteryHistory.user_id.in_(user_ids))
        )).scalars().all())
        result_rows = list((await db.execute(
            select(ExamResult.user_id, ExamResult.exam_id).where(ExamResult.user_id.in_(user_ids))
        )).all())
        db.expunge_all()
        await db.rollback()

    groups = Counter(_value(item.experiment_group) for item in participations)
    origins = Counter(_value(item.data_origin) for item in participations)
    decisions_by_user = Counter(item.user_id for item in decisions)
    adaptive_participants = [
        item for item in participations
        if _value(item.experiment_group) == ResearchExperimentGroup.ADAPTIVE.value
    ]
    pre_users = {
        user_id for user_id, exam_id in result_rows
        if study is not None and exam_id == study.pre_exam_id
    }
    post_users = {
        user_id for user_id, exam_id in result_rows
        if study is not None and exam_id == study.post_exam_id
    }
    fixed_sequence_configured = bool(
        study and study.fixed_sequence_version
        and any(item.sequence_version == study.fixed_sequence_version for item in sequence_items)
    )
    source_count = sum(bool(item.source_name and item.source_url) for item in questions)
    license_count = sum(bool(item.source_license) for item in questions)
    verified_count = sum(
        item.verified_status == QuestionVerificationStatus.VERIFIED.value for item in questions
    )
    consent_count = sum(
        _value(item.consent_status) == ResearchConsentStatus.GRANTED.value for item in participations
    )
    real_count = sum(
        _value(item.data_origin) == ResearchDataOrigin.REAL.value for item in participations
    )
    test_participants = [
        item for item in participations
        if _value(item.data_origin) == ResearchDataOrigin.TEST.value
    ]
    test_user_ids = {item.user_id for item in test_participants}
    test_attempts = [item for item in attempts if item.user_id in test_user_ids and _value(item.data_origin) == "TEST"]
    test_decisions = [item for item in decisions if item.user_id in test_user_ids and _value(item.data_origin) == "TEST"]
    test_mastery = [item for item in mastery_events if item.user_id in test_user_ids and _value(item.data_origin) == "TEST"]
    phase_counts = Counter(item.phase for item in study_question_links)
    phase_question_ids = {
        phase: {item.question_id for item in study_question_links if item.phase == phase}
        for phase in ("PRE", "TRAIN", "POST")
    }
    phase_overlaps = {
        "PRE_TRAIN": len(phase_question_ids["PRE"] & phase_question_ids["TRAIN"]),
        "POST_TRAIN": len(phase_question_ids["POST"] & phase_question_ids["TRAIN"]),
        "PRE_POST": len(phase_question_ids["PRE"] & phase_question_ids["POST"]),
    }
    train_attempts_by_user = Counter(
        item.user_id for item in test_attempts
        if item.question_id in phase_question_ids["TRAIN"]
    )
    response_time_counts = Counter(item.response_time_status for item in test_attempts)
    metadata_ready = sum(
        bool(
            item.metadata_json
            and item.metadata_json.get("license_url")
            and item.metadata_json.get("provenance_status") == "SOURCE_VERIFIED"
            and item.metadata_json.get("content_review_status") == "AI_PRECHECKED"
        )
        for item in study_question_links
    )
    freeze_configured = bool(
        study and study.git_commit and study.question_bank_version
        and study.adaptive_algorithm_version and study.adaptive_selection_policy_version
        and study.fixed_selection_policy_version
    )

    setup_blockers = []
    if study is None:
        setup_blockers.append("STUDY MISSING")
    elif study.study_status not in {
        ResearchStudyStatus.PILOT.value,
        ResearchStudyStatus.ACTIVE.value,
    }:
        setup_blockers.append("STUDY IS NOT OPEN FOR PILOT")
    expected_phases = {"PRE": 20, "POST": 20, "TRAIN": 40}
    if any(phase_counts[phase] != count for phase, count in expected_phases.items()):
        setup_blockers.append(
            "QUESTION BANK MUST CONTAIN PRE=20, POST=20, TRAIN=40"
        )
    if any(phase_overlaps.values()):
        setup_blockers.append("PRE/TRAIN/POST QUESTION SETS OVERLAP")
    if verified_count != len(questions) or not questions:
        setup_blockers.append("QUESTION VERIFIED COVERAGE BELOW 100%")
    if source_count != len(questions) or license_count != len(questions) or not questions:
        setup_blockers.append("QUESTION SOURCE OR LICENSE COVERAGE BELOW 100%")
    if metadata_ready != len(study_question_links) or not study_question_links:
        setup_blockers.append(
            "QUESTION LICENSE URL / SOURCE_VERIFIED / AI_PRECHECKED COVERAGE BELOW 100%"
        )
    if groups[ResearchExperimentGroup.FIXED.value] and not fixed_sequence_configured:
        setup_blockers.append("FIXED SEQUENCE MISSING")
    if study is None or study.pre_exam_id is None or pre_exam is None:
        setup_blockers.append("PRE ASSESSMENT MISSING")
    elif (
        pre_exam.assessment_purpose != AssessmentPurpose.RESEARCH_PRE.value
        or pre_exam.max_attempts != 1
        or pre_exam_question_ids != phase_question_ids["PRE"]
    ):
        setup_blockers.append("PRE ASSESSMENT CONFIGURATION DOES NOT MATCH PRE BANK")
    if study is None or study.post_exam_id is None or post_exam is None:
        setup_blockers.append("POST ASSESSMENT MISSING")
    elif (
        post_exam.assessment_purpose != AssessmentPurpose.RESEARCH_POST.value
        or post_exam.max_attempts != 1
        or post_exam_question_ids != phase_question_ids["POST"]
    ):
        setup_blockers.append("POST ASSESSMENT CONFIGURATION DOES NOT MATCH POST BANK")
    if not freeze_configured:
        setup_blockers.append("RESEARCH FREEZE MISSING")

    dry_run_blockers = []
    if not test_participants:
        dry_run_blockers.append("NO TEST DRY-RUN PARTICIPANT")
    elif any(_value(item.consent_status) != ResearchConsentStatus.GRANTED.value for item in test_participants):
        dry_run_blockers.append("TEST CONSENT NOT GRANTED")
    if test_participants and any(item.user_id not in pre_users for item in test_participants):
        dry_run_blockers.append("TEST PRE ASSESSMENT INCOMPLETE")
    if test_participants and any(train_attempts_by_user[item.user_id] < 20 for item in test_participants):
        dry_run_blockers.append("TEST TRAIN ATTEMPTS BELOW 20")
    if test_participants and any(item.user_id not in post_users for item in test_participants):
        dry_run_blockers.append("TEST POST ASSESSMENT INCOMPLETE")
    if test_participants and any(item.completed_at is None for item in test_participants):
        dry_run_blockers.append("TEST PILOT LIFECYCLE INCOMPLETE")
    if not test_attempts:
        dry_run_blockers.append("TEST IMMUTABLE ATTEMPT LOG MISSING")
    if not test_mastery:
        dry_run_blockers.append("TEST MASTERY HISTORY MISSING")
    if not test_decisions:
        dry_run_blockers.append("TEST ADAPTIVE DECISION HISTORY MISSING")
    if test_attempts and not any(item.response_time_status == "VALID" for item in test_attempts):
        dry_run_blockers.append("TEST VALID RESPONSE TIME MISSING")
    blockers = setup_blockers + dry_run_blockers

    warnings = {
        "MISSING RESPONSE TIME": sum(item.response_time_seconds is None for item in attempts),
        "UNKNOWN DATA ORIGIN": sum(
            _value(item.data_origin) == ResearchDataOrigin.UNKNOWN.value for item in participations
        ),
        "CONSENT NOT GRANTED": len(participations) - consent_count,
        "MISSING PARTICIPANT CODE": sum(not item.participant_code for item in participations),
        "QUESTION LICENSE UNKNOWN": len(questions) - license_count,
        "MISSING ADAPTIVE DECISION": sum(
            decisions_by_user[item.user_id] == 0 for item in adaptive_participants
        ),
        "MISSING MASTERY SNAPSHOT": sum(
            item.mastery_before is None or item.mastery_after is None for item in attempts
        ),
        "MISSING DIFFICULTY SNAPSHOT": sum(
            item.difficulty_before is None or item.difficulty_after is None for item in attempts
        ),
        "PARTICIPANTS WITHOUT PRE": sum(item.user_id not in pre_users for item in participations),
        "PARTICIPANTS WITHOUT POST": sum(item.user_id not in post_users for item in participations),
    }
    return {
        "study_code": study_code,
        "study_status": study.study_status if study else None,
        "participants": len(participations),
        "consent_granted": consent_count,
        "groups": groups,
        "origins": origins,
        "fixed_participants": groups[ResearchExperimentGroup.FIXED.value],
        "adaptive_participants": groups[ResearchExperimentGroup.ADAPTIVE.value],
        "fixed_sequence_configured": fixed_sequence_configured,
        "fixed_sequence_version": study.fixed_sequence_version if study else None,
        "question_phase_counts": dict(phase_counts),
        "question_phase_overlaps": phase_overlaps,
        "pre_exam_configured": bool(study and study.pre_exam_id),
        "post_exam_configured": bool(study and study.post_exam_id),
        "pre_completed": len(pre_users),
        "post_completed": len(post_users),
        "questions": len(questions),
        "questions_with_source": source_count,
        "questions_with_license": license_count,
        "verified_questions": verified_count,
        "source_coverage": _coverage(source_count, len(questions)),
        "license_coverage": _coverage(license_count, len(questions)),
        "verified_coverage": _coverage(verified_count, len(questions)),
        "smoke_question_ids": [str(item.id) for item in questions if not item.skill_key or not item.topic],
        "attempts": len(attempts),
        "decisions": len(decisions),
        "mastery_history": len(mastery_events),
        "test_participants": len(test_participants),
        "test_attempts": len(test_attempts),
        "test_mastery_history": len(test_mastery),
        "test_adaptive_decisions": len(test_decisions),
        "test_train_attempts": sum(train_attempts_by_user.values()),
        "test_completed_participants": sum(
            item.completed_at is not None for item in test_participants
        ),
        "test_response_time": dict(response_time_counts),
        "test_excluded_from_real_export": all(
            _value(item.data_origin) != ResearchDataOrigin.REAL.value
            for item in test_participants
        ),
        "real_participants": real_count,
        "real_observations": sum(
            _value(item.data_origin) == ResearchDataOrigin.REAL.value for item in attempts
        ),
        "research_freeze_configured": freeze_configured,
        "warnings": warnings,
        "setup_blockers": setup_blockers,
        "dry_run_blockers": dry_run_blockers,
        "blockers": blockers,
        "pilot_ready": not blockers,
        "publishable_ready": (
            real_count >= 5
            and len([item for item in attempts if _value(item.data_origin) == "REAL"]) >= 100
            and bool([item for item in mastery_events if _value(item.data_origin) == "REAL"])
            and bool([item for item in decisions if _value(item.data_origin) == "REAL"])
        ),
        "fixed_selector_supported": True,
    }


def print_report(report: dict) -> None:
    print(f"Study code: {report['study_code'] or 'ALL'}")
    print(f"Study status: {report['study_status'] or 'NOT CONFIGURED'}")
    print(f"Participants enrolled: {report['participants']}")
    print(f"Consent granted: {report['consent_granted']}")
    print(f"Adaptive participants: {report['adaptive_participants']}")
    print(f"Fixed participants: {report['fixed_participants']}")
    print(f"REAL origin: {report['origins']['REAL']}")
    print(f"Fixed sequence configured: {report['fixed_sequence_configured']}")
    print(f"Fixed sequence version: {report['fixed_sequence_version'] or 'MISSING'}")
    print(f"Question phases: {report['question_phase_counts']}")
    print(f"Question phase overlaps: {report['question_phase_overlaps']}")
    print(f"PRE configured/completed: {report['pre_exam_configured']} / {report['pre_completed']}")
    print(f"POST configured/completed: {report['post_exam_configured']} / {report['post_completed']}")
    print(f"Question verified coverage: {report['verified_coverage']}%")
    print(f"Question source coverage: {report['source_coverage']}%")
    print(f"Question license coverage: {report['license_coverage']}%")
    print(f"Research freeze configured: {report['research_freeze_configured']}")
    print(
        "TEST logging attempts/mastery/decisions: "
        f"{report['test_attempts']}/{report['test_mastery_history']}/{report['test_adaptive_decisions']}"
    )
    print(f"TEST TRAIN attempts: {report['test_train_attempts']}")
    print(f"TEST completed participants: {report['test_completed_participants']}")
    print(f"TEST response time statuses: {report['test_response_time']}")
    print(f"TEST excluded from REAL export: {report['test_excluded_from_real_export']}")
    if report["smoke_question_ids"]:
        print("Questions missing skill/topic: " + ", ".join(report["smoke_question_ids"]))
    print("\nWarnings:")
    for label, count in report["warnings"].items():
        print(f"- {label}: {count}")
    print("\nPilot setup/dry-run blockers:")
    for blocker in report["blockers"]:
        print(f"- {blocker}")
    print(f"REAL PILOT READY FOR DATA COLLECTION: {'YES' if report['pilot_ready'] else 'NO'}")
    print(f"REAL PILOT DATASET READY FOR MANUSCRIPT ANALYSIS: {'YES' if report['publishable_ready'] else 'NO'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-code")
    args = parser.parse_args()
    print_report(asyncio.run(readiness_report(args.study_code)))


if __name__ == "__main__":
    main()
