"""Delivery adapters and security helpers for Zalo OA."""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.models.zalo import ZaloProvider

logger = logging.getLogger(__name__)


class ZaloAdapterError(RuntimeError):
    pass


@dataclass
class ZaloSendResult:
    external_message_id: Optional[str]
    response: Dict[str, Any]


def webhook_signature(raw_body: bytes, app_id: str, timestamp: str, secret: str) -> str:
    data = raw_body.decode("utf-8")
    return hashlib.sha256(f"{app_id}{data}{timestamp}{secret}".encode("utf-8")).hexdigest()


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    app_id: str,
    timestamp: str,
    secret: str,
) -> bool:
    if not all([raw_body, signature_header, app_id, timestamp, secret]):
        return False
    received = signature_header.strip()
    if received.lower().startswith("mac="):
        received = received[4:].strip()
    expected = webhook_signature(raw_body, app_id, timestamp, secret)
    return hmac.compare_digest(received.lower(), expected.lower())


class BaseZaloAdapter:
    async def send_text(self, zalo_user_id: str, text: str) -> ZaloSendResult:
        raise NotImplementedError


class MockZaloAdapter(BaseZaloAdapter):
    async def send_text(self, zalo_user_id: str, text: str) -> ZaloSendResult:
        digest = hashlib.sha256(f"{zalo_user_id}:{text}".encode("utf-8")).hexdigest()[:20]
        return ZaloSendResult(
            external_message_id=f"mock-{digest}",
            response={"error": 0, "message": "Mock delivery", "provider": "mock"},
        )


class ZaloOaAdapter(BaseZaloAdapter):
    def __init__(self) -> None:
        self._access_token = settings.ZALO_OA_ACCESS_TOKEN
        self._refresh_token = settings.ZALO_OA_REFRESH_TOKEN

    def _validate_configuration(self) -> None:
        missing = [
            name
            for name, value in {
                "ZALO_APP_ID": settings.ZALO_APP_ID,
                "ZALO_APP_SECRET": settings.ZALO_APP_SECRET,
                "ZALO_OA_ACCESS_TOKEN": self._access_token,
            }.items()
            if not value
        ]
        if missing:
            raise ZaloAdapterError(f"Missing Zalo OA configuration: {', '.join(missing)}")

    async def _refresh_access_token(self) -> bool:
        if not self._refresh_token or not settings.ZALO_APP_ID or not settings.ZALO_APP_SECRET:
            return False
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                settings.ZALO_OA_TOKEN_URL,
                headers={
                    "secret_key": settings.ZALO_APP_SECRET,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "app_id": settings.ZALO_APP_ID,
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
            )
            response.raise_for_status()
            data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            logger.warning("Zalo OA token refresh returned no access token")
            return False
        self._access_token = str(access_token)
        if data.get("refresh_token"):
            self._refresh_token = str(data["refresh_token"])
        logger.info("Zalo OA access token refreshed in memory")
        return True

    @staticmethod
    def _looks_like_token_error(status_code: int, data: Dict[str, Any]) -> bool:
        if status_code in {401, 403}:
            return True
        message = str(data.get("message") or "").lower()
        return "token" in message and any(word in message for word in ("expire", "invalid", "oauth"))

    async def _send_once(self, zalo_user_id: str, text: str) -> tuple[int, Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                settings.ZALO_OA_SEND_URL,
                headers={"access_token": self._access_token, "Content-Type": "application/json"},
                json={"recipient": {"user_id": zalo_user_id}, "message": {"text": text[:2000]}},
            )
            try:
                data = response.json()
            except ValueError as exc:
                raise ZaloAdapterError("Zalo OA returned a non-JSON response") from exc
            return response.status_code, data

    async def send_text(self, zalo_user_id: str, text: str) -> ZaloSendResult:
        self._validate_configuration()
        status_code, data = await self._send_once(zalo_user_id, text)
        if self._looks_like_token_error(status_code, data) and await self._refresh_access_token():
            status_code, data = await self._send_once(zalo_user_id, text)
        if status_code >= 400 or data.get("error") not in (None, 0, "0"):
            raise ZaloAdapterError(
                f"Zalo OA send failed (HTTP {status_code}, code {data.get('error')}): {data.get('message', 'unknown error')}"
            )
        response_data = data.get("data") if isinstance(data.get("data"), dict) else {}
        return ZaloSendResult(
            external_message_id=response_data.get("message_id"),
            response={
                "error": data.get("error", 0),
                "message": data.get("message", "Success"),
                "quota_type": (response_data.get("quota") or {}).get("quota_type"),
            },
        )


mock_zalo_adapter = MockZaloAdapter()
zalo_oa_adapter = ZaloOaAdapter()


def get_zalo_adapter(provider: ZaloProvider) -> BaseZaloAdapter:
    if provider == ZaloProvider.ZALO_OA:
        return zalo_oa_adapter
    return mock_zalo_adapter
