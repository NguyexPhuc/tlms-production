import pytest

from app.services import background_tasks


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
