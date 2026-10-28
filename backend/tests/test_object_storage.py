from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.object_storage import ObjectStorageService


def test_render_database_url_is_normalized_for_asyncpg():
    settings = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://user:password@database.internal/tlms",
    )
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:password@database.internal/tlms"


def test_neon_database_url_is_normalized_for_asyncpg_ssl():
    settings = Settings(
        _env_file=None,
        DATABASE_URL=(
            "postgresql://user:password@database.neon.tech/tlms"
            "?sslmode=require&channel_binding=require"
        ),
    )
    assert settings.DATABASE_URL == (
        "postgresql+asyncpg://user:password@database.neon.tech/tlms?ssl=require"
    )


def test_local_storage_round_trip(tmp_path, monkeypatch):
    service = ObjectStorageService()
    upload_root = tmp_path / "uploads"
    private_root = tmp_path / "private"
    monkeypatch.setattr(service.settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(service.settings, "UPLOAD_DIR", str(upload_root))
    monkeypatch.setattr(service.settings, "CERTIFICATE_STORAGE_DIR", str(private_root))

    url = service.put_upload("quest_proofs/evidence.png", b"image", "image/png")
    locator = service.put_private("certificates/result.pdf", b"pdf", "application/pdf")

    assert url == "/uploads/quest_proofs/evidence.png"
    assert service.read_upload("quest_proofs/evidence.png").content == b"image"
    assert service.read_private(locator).content == b"pdf"
    assert Path(locator).is_file()


@pytest.mark.parametrize("key", ["../secret", "folder/../../secret", ""])
def test_storage_rejects_unsafe_keys(key):
    with pytest.raises(ValueError):
        ObjectStorageService._safe_relative_key(key)
