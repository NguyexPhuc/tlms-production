from types import SimpleNamespace

import pytest

from app.api.routes import auth
from app.core.exceptions import (
    AccountNotRegisteredException,
    InvalidCredentialsException,
    S4HServiceUnavailableException,
)
from app.schemas.auth import LoginRequest


@pytest.mark.asyncio
async def test_unknown_account_is_not_mislabeled_as_maintenance(monkeypatch):
    async def no_local_user(_db, _email):
        return None

    async def local_login_fails(_db, _credentials):
        raise InvalidCredentialsException()

    async def s4h_is_down(_credentials):
        raise S4HServiceUnavailableException()

    monkeypatch.setattr(auth.local_auth_service, "get_user_by_email", no_local_user)
    monkeypatch.setattr(auth.local_auth_service, "login", local_login_fails)
    monkeypatch.setattr(auth.s4h_auth_service, "login", s4h_is_down)

    with pytest.raises(AccountNotRegisteredException) as exc_info:
        await auth.login(
            LoginRequest(email="missing@example.com", password="secret"),
            db=SimpleNamespace(),
        )

    assert exc_info.value.status_code == 404
    assert "chưa được đăng ký" in exc_info.value.detail


@pytest.mark.asyncio
async def test_wrong_local_password_stays_invalid_credentials(monkeypatch):
    local_user = SimpleNamespace(password_hash="scrypt-hash")

    async def get_local_user(_db, _email):
        return local_user

    async def local_login_fails(_db, _credentials):
        raise InvalidCredentialsException()

    async def s4h_must_not_run(_credentials):
        raise AssertionError("S4H must not run for an account with a local password")

    monkeypatch.setattr(auth.local_auth_service, "get_user_by_email", get_local_user)
    monkeypatch.setattr(auth.local_auth_service, "login", local_login_fails)
    monkeypatch.setattr(auth.s4h_auth_service, "login", s4h_must_not_run)

    with pytest.raises(InvalidCredentialsException):
        await auth.login(
            LoginRequest(email="member@example.com", password="wrong"),
            db=SimpleNamespace(),
        )
