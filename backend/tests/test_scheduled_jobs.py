from fastapi import HTTPException
import pytest

from app.api.routes import scheduled_jobs


def test_scheduler_key_accepts_matching_secret(monkeypatch):
    monkeypatch.setattr(scheduled_jobs.settings, "SCHEDULER_API_KEY", "scheduler-secret")
    scheduled_jobs.verify_scheduler_key("scheduler-secret")


def test_scheduler_key_rejects_invalid_secret(monkeypatch):
    monkeypatch.setattr(scheduled_jobs.settings, "SCHEDULER_API_KEY", "scheduler-secret")
    with pytest.raises(HTTPException) as exc_info:
        scheduled_jobs.verify_scheduler_key("wrong-secret")
    assert exc_info.value.status_code == 401


def test_scheduler_key_requires_server_configuration(monkeypatch):
    monkeypatch.setattr(scheduled_jobs.settings, "SCHEDULER_API_KEY", "")
    with pytest.raises(HTTPException) as exc_info:
        scheduled_jobs.verify_scheduler_key("anything")
    assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_scheduler_endpoint_dispatches_existing_job(monkeypatch):
    called = False

    async def fake_daily_quest_job():
        nonlocal called
        called = True

    monkeypatch.setattr(scheduled_jobs.settings, "SCHEDULER_API_KEY", "scheduler-secret")
    monkeypatch.setattr(scheduled_jobs, "reset_daily_quests", fake_daily_quest_job)

    response = await scheduled_jobs.run_scheduled_job(
        scheduled_jobs.ScheduledJobName.DAILY_QUESTS,
        "scheduler-secret",
    )

    assert called is True
    assert response == {"success": True, "job": "daily-quests"}
