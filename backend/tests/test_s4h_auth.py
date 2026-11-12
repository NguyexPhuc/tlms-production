from types import SimpleNamespace

import pytest

from app.core.exceptions import S4HServiceUnavailableException
from app.services.s4h_auth import S4HAuthService


class FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def request(self, **kwargs):
        return SimpleNamespace(
            status_code=520,
            json=lambda: {"message": "upstream unavailable"},
            text="upstream unavailable",
        )


@pytest.mark.asyncio
async def test_upstream_5xx_is_reported_as_service_unavailable(monkeypatch):
    monkeypatch.setattr("app.services.s4h_auth.httpx.AsyncClient", FakeClient)

    with pytest.raises(S4HServiceUnavailableException) as exc_info:
        await S4HAuthService()._make_request("POST", "/auth/login", {})

    assert exc_info.value.status_code == 503
