"""Create a private logical PostgreSQL backup before a production migration."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.services.object_storage import object_storage


def main() -> None:
    settings = get_settings()
    if settings.APP_ENV.strip().lower() != "production":
        raise RuntimeError("Production database backup can only run with APP_ENV=production")
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")
    if not object_storage.is_s3:
        raise RuntimeError("Production backup requires private S3-compatible storage")

    url = make_url(settings.DATABASE_URL)
    if not all((url.host, url.username, url.database)):
        raise RuntimeError("DATABASE_URL is incomplete")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"tlms-before-research-pilot-{timestamp}.dump"
    environment = os.environ.copy()
    if url.password:
        environment["PGPASSWORD"] = url.password
    environment.setdefault("PGSSLMODE", str(url.query.get("sslmode", "require")))

    with tempfile.TemporaryDirectory(prefix="tlms-backup-") as temporary_directory:
        output_path = Path(temporary_directory) / filename
        command = [
            "pg_dump",
            "--host", str(url.host),
            "--port", str(url.port or 5432),
            "--username", str(url.username),
            "--dbname", str(url.database),
            "--format", "custom",
            "--no-owner",
            "--no-acl",
            "--file", str(output_path),
        ]
        subprocess.run(command, env=environment, check=True)
        content = output_path.read_bytes()
        if not content:
            raise RuntimeError("pg_dump produced an empty backup")
        digest = hashlib.sha256(content).hexdigest()
        storage_key = object_storage.put_private(
            f"backups/{filename}",
            content,
            "application/octet-stream",
        )

    print(f"Backup created: {storage_key}")
    print(f"Backup timestamp: {timestamp}")
    print(f"Backup size: {len(content)} bytes")
    print(f"Backup SHA256: {digest}")


if __name__ == "__main__":
    main()
