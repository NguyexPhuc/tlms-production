"""Local and S3-compatible object storage used by uploads and certificates."""
from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    content: bytes
    content_type: str


class ObjectStorageService:
    """Keep private data durable without exposing bucket credentials or object keys."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = None

    @property
    def is_s3(self) -> bool:
        return self.settings.STORAGE_BACKEND.strip().lower() == "s3"

    def put_upload(self, relative_key: str, content: bytes, content_type: str) -> str:
        relative_key = self._safe_relative_key(relative_key)
        if self.is_s3:
            self._put_s3(f"uploads/{relative_key}", content, content_type)
        else:
            self._write_local(Path(self.settings.UPLOAD_DIR), relative_key, content)
        return f"/uploads/{relative_key}"

    def read_upload(self, relative_key: str) -> StoredObject:
        relative_key = self._safe_relative_key(relative_key)
        if self.is_s3:
            return self._read_s3(f"uploads/{relative_key}")
        path = self._local_path(Path(self.settings.UPLOAD_DIR), relative_key)
        return StoredObject(path.read_bytes(), self._content_type(path.name))

    def put_private(self, relative_key: str, content: bytes, content_type: str) -> str:
        relative_key = self._safe_relative_key(relative_key)
        if self.is_s3:
            object_key = f"private/{relative_key}"
            self._put_s3(object_key, content, content_type)
            return f"s3://{object_key}"
        path = self._write_local(Path(self.settings.CERTIFICATE_STORAGE_DIR), relative_key, content)
        return str(path)

    def read_private(self, storage_key: str) -> StoredObject:
        if storage_key.startswith("s3://"):
            return self._read_s3(storage_key[5:])
        path = Path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return StoredObject(path.read_bytes(), self._content_type(path.name))

    def private_exists(self, storage_key: Optional[str]) -> bool:
        if not storage_key:
            return False
        if storage_key.startswith("s3://"):
            try:
                self._s3_client().head_object(Bucket=self._bucket(), Key=storage_key[5:])
                return True
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {"404", "NoSuchKey", "NotFound"}:
                    return False
                raise
        return Path(storage_key).is_file()

    def _put_s3(self, object_key: str, content: bytes, content_type: str) -> None:
        self._s3_client().put_object(
            Bucket=self._bucket(),
            Key=object_key,
            Body=content,
            ContentType=content_type or "application/octet-stream",
        )

    def _read_s3(self, object_key: str) -> StoredObject:
        try:
            response = self._s3_client().get_object(Bucket=self._bucket(), Key=object_key)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in {"404", "NoSuchKey", "NotFound"}:
                raise FileNotFoundError(object_key) from exc
            raise
        return StoredObject(
            response["Body"].read(),
            response.get("ContentType") or self._content_type(object_key),
        )

    def _s3_client(self):
        if self._client is not None:
            return self._client
        required = {
            "S3_ENDPOINT_URL": self.settings.S3_ENDPOINT_URL,
            "S3_BUCKET": self.settings.S3_BUCKET,
            "S3_ACCESS_KEY_ID": self.settings.S3_ACCESS_KEY_ID,
            "S3_SECRET_ACCESS_KEY": self.settings.S3_SECRET_ACCESS_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing S3 storage settings: {', '.join(missing)}")
        self._client = boto3.client(
            "s3",
            endpoint_url=self.settings.S3_ENDPOINT_URL,
            region_name=self.settings.S3_REGION,
            aws_access_key_id=self.settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=self.settings.S3_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        return self._client

    def _bucket(self) -> str:
        if not self.settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        return self.settings.S3_BUCKET

    @staticmethod
    def _safe_relative_key(value: str) -> str:
        normalized = value.replace("\\", "/").lstrip("/")
        path = PurePosixPath(normalized)
        if not normalized or ".." in path.parts or "." in path.parts:
            raise ValueError("Invalid storage key")
        return path.as_posix()

    @classmethod
    def _local_path(cls, root: Path, relative_key: str) -> Path:
        root = root.resolve()
        path = (root / cls._safe_relative_key(relative_key)).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Storage key escapes configured directory")
        return path

    @classmethod
    def _write_local(cls, root: Path, relative_key: str, content: bytes) -> Path:
        path = cls._local_path(root, relative_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    @staticmethod
    def _content_type(filename: str) -> str:
        return mimetypes.guess_type(filename)[0] or "application/octet-stream"


object_storage = ObjectStorageService()
