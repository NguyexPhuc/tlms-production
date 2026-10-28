from datetime import datetime, timedelta

import pytest

from app.models.zalo import ZaloLinkStatus, ZaloProvider
from app.services.zalo_adapter import (
    MockZaloAdapter,
    ZaloAdapterError,
    ZaloOaAdapter,
    verify_webhook_signature,
    webhook_signature,
)
from app.services.zalo_quiz import (
    normalize_choice,
    objective_score,
    session_has_expired,
    webhook_event_key,
    ZaloQuizService,
)


def test_normalize_choice_accepts_supported_formats():
    assert normalize_choice("A") == "A"
    assert normalize_choice(" b. ") == "B"
    assert normalize_choice("C) dap an") == "C"
    assert normalize_choice("D - answer") == "D"
    assert normalize_choice("answer A") is None
    assert normalize_choice("E") is None


def test_objective_score_is_deterministic():
    assert objective_score("a", "A") == (True, 100.0)
    assert objective_score("B", "A") == (False, 0.0)


def test_expiry_uses_deadline_boundary():
    now = datetime.utcnow()
    assert session_has_expired(now - timedelta(seconds=1), now)
    assert session_has_expired(now, now)
    assert not session_has_expired(now + timedelta(seconds=1), now)


def test_webhook_signature_and_duplicate_key():
    raw = b'{"app_id":"app","timestamp":"1000","message":{"msg_id":"m1"}}'
    signature = webhook_signature(raw, "app", "1000", "secret")
    assert verify_webhook_signature(raw, f"mac={signature}", "app", "1000", "secret")
    assert not verify_webhook_signature(raw + b" ", signature, "app", "1000", "secret")
    payload = {"event_name": "user_send_text", "message": {"msg_id": "m1"}}
    assert webhook_event_key(payload, raw) == "user_send_text:m1"
    assert webhook_event_key(payload, raw) == webhook_event_key(payload, raw)


def test_send_policy_checks_consent_and_interaction_window():
    now = datetime.utcnow()
    link = type(
        "Link",
        (),
        {
            "status": ZaloLinkStatus.LINKED,
            "consent_granted": True,
            "notifications_enabled": True,
            "zalo_user_id": "uid",
            "last_interaction_at": now - timedelta(days=2),
        },
    )()
    config = type("Config", (), {"provider": ZaloProvider.ZALO_OA, "send_window_days": 7})()
    assert ZaloQuizService.can_send(link, config, now)
    link.last_interaction_at = now - timedelta(days=8)
    assert not ZaloQuizService.can_send(link, config, now)
    link.last_interaction_at = now
    link.consent_granted = False
    assert not ZaloQuizService.can_send(link, config, now)


@pytest.mark.asyncio
async def test_mock_adapter_returns_stable_success_and_never_calls_zalo():
    adapter = MockZaloAdapter()
    first = await adapter.send_text("mock-user", "Question A/B/C/D")
    second = await adapter.send_text("mock-user", "Question A/B/C/D")
    assert first.external_message_id == second.external_message_id
    assert first.response["error"] == 0


@pytest.mark.asyncio
async def test_oa_adapter_refreshes_expired_token_once(monkeypatch):
    adapter = ZaloOaAdapter()
    adapter._access_token = "expired-token"
    calls = []

    monkeypatch.setattr("app.services.zalo_adapter.settings.ZALO_APP_ID", "app")
    monkeypatch.setattr("app.services.zalo_adapter.settings.ZALO_APP_SECRET", "secret")

    async def fake_send_once(user_id, text):
        calls.append((user_id, text))
        if len(calls) == 1:
            return 401, {"error": -201, "message": "access token expired"}
        return 200, {"error": 0, "message": "Success", "data": {"message_id": "m2"}}

    async def fake_refresh():
        adapter._access_token = "new-token"
        return True

    monkeypatch.setattr(adapter, "_send_once", fake_send_once)
    monkeypatch.setattr(adapter, "_refresh_access_token", fake_refresh)

    result = await adapter.send_text("zalo-user", "Question")
    assert len(calls) == 2
    assert result.external_message_id == "m2"


@pytest.mark.asyncio
async def test_oa_adapter_raises_for_delivery_error(monkeypatch):
    adapter = ZaloOaAdapter()
    adapter._access_token = "token"

    monkeypatch.setattr("app.services.zalo_adapter.settings.ZALO_APP_ID", "app")
    monkeypatch.setattr("app.services.zalo_adapter.settings.ZALO_APP_SECRET", "secret")

    async def fake_send_once(user_id, text):
        return 429, {"error": -32, "message": "quota exceeded"}

    monkeypatch.setattr(adapter, "_send_once", fake_send_once)
    with pytest.raises(ZaloAdapterError, match="quota exceeded"):
        await adapter.send_text("zalo-user", "Question")
