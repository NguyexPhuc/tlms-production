"""Dedicated scheduler process for production deployments."""
from __future__ import annotations

import asyncio
import logging
import signal
import time
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.services.background_tasks import start_scheduler, stop_scheduler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


def _migration_heads() -> set[str]:
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    return set(ScriptDirectory.from_config(config).get_heads())


async def wait_for_database_schema() -> None:
    """Do not run startup jobs against a database while the web service migrates it."""
    expected = _migration_heads()
    deadline = time.monotonic() + max(settings.WORKER_DB_WAIT_SECONDS, 1)
    last_error = "database is not ready"

    while time.monotonic() < deadline:
        try:
            async with engine.connect() as connection:
                result = await connection.execute(text("SELECT version_num FROM alembic_version"))
                current = set(result.scalars().all())
            if current == expected:
                logger.info("Database schema is ready at Alembic head %s", ", ".join(sorted(expected)))
                return
            last_error = f"database revisions {sorted(current)} do not match heads {sorted(expected)}"
        except Exception as exc:
            last_error = str(exc)
        logger.info("Waiting for database migrations: %s", last_error)
        await asyncio.sleep(3)

    raise RuntimeError(f"Timed out waiting for database migrations: {last_error}")


async def run() -> None:
    await wait_for_database_schema()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop_event.set))

    start_scheduler()
    logger.info("TLMS scheduler worker is running")
    try:
        await stop_event.wait()
    finally:
        stop_scheduler()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
