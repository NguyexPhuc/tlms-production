#!/bin/sh
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import sys
from app.core.config import get_settings

async def check():
    try:
        url = get_settings().DATABASE_URL
        if not url:
            print('DATABASE_URL is not set', file=sys.stderr)
            sys.exit(1)
        engine = create_async_engine(url)
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        await engine.dispose()
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(check())
"; do
    sleep 1
done
echo "Database is ready!"

# A production rollout can opt into one logical backup before applying a new
# migration. The flag is disabled by default and removed after the rollout.
if [ "${RESEARCH_PILOT_BACKUP_BEFORE_MIGRATION:-false}" = "true" ]; then
    echo "Creating pre-migration database backup..."
    python -m app.scripts.backup_production_db
fi

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Import the reviewed open-license bank only for the explicitly flagged pilot
# rollout. The importer is idempotent and aborts on an incomplete conflict.
if [ "${RESEARCH_PILOT_AUTO_SETUP:-false}" = "true" ]; then
    echo "Configuring the real research pilot..."
    if [ -n "${RENDER_GIT_COMMIT:-}" ]; then
        python -m app.scripts.setup_real_pilot \
            --workbook /app/app/data/TLMS_OpenLicense_QuestionBank_80_v1.xlsx \
            --git-commit "${RENDER_GIT_COMMIT}"
    else
        python -m app.scripts.setup_real_pilot \
            --workbook /app/app/data/TLMS_OpenLicense_QuestionBank_80_v1.xlsx
    fi
    if [ "${RESEARCH_PILOT_RUN_TEST_SMOKE:-false}" = "true" ]; then
        echo "Running TEST-origin research pilot smoke flow..."
        python -m app.scripts.run_real_pilot_dry_run
    fi
    python -m app.scripts.research_readiness_check \
        --study-code TLMS_ADAPTIVE_REAL_PILOT_2026
    python -m app.scripts.export_real_pilot_dataset \
        --study-code TLMS_ADAPTIVE_REAL_PILOT_2026 \
        --output /tmp/research_real_pilot_export
fi

# Start the application
echo "Starting application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-1}"
