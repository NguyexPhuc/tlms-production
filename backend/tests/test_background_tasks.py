import pytest

from app.services import background_tasks


@pytest.mark.parametrize(
    ("student_id", "expected"),
    [
        (None, False),
        ("", False),
        (" TLMS0004 ", False),
        ("demo123", False),
        ("TEST99", False),
        ("123000529", True),
        ("20ABC123", True),
    ],
)
def test_schedule_sync_rejects_local_demo_student_ids(student_id, expected):
    assert background_tasks._is_syncable_student_id(student_id) is expected


@pytest.mark.asyncio
async def test_background_job_retries_transient_failure(monkeypatch):
    attempts = 0

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(background_tasks.asyncio, "sleep", no_wait)

    result = await background_tasks._run_with_retry("test", operation)

    assert result == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_background_job_raises_after_retry_limit(monkeypatch):
    async def operation():
        raise RuntimeError("permanent failure")

    async def no_wait(_seconds):
        return None

    monkeypatch.setattr(background_tasks.asyncio, "sleep", no_wait)

    with pytest.raises(RuntimeError, match="permanent failure"):
        await background_tasks._run_with_retry("test", operation, attempts=2)
