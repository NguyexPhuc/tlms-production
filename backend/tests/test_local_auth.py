from types import SimpleNamespace

import pytest

from app.core.exceptions import InvalidCredentialsException, RegistrationFailedException
from app.models.user import UserRole, UserStatus
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.local_auth import LocalAuthService


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, query_result=None):
        self.query_result = query_result
        self.added = None

    async def execute(self, _statement):
        return ScalarResult(self.query_result)

    def add(self, value):
        self.added = value

    async def flush(self):
        return None

    async def refresh(self, _value):
        return None


def test_password_hash_round_trip_and_unique_salts():
    first = LocalAuthService.hash_password("StrongPass123")
    second = LocalAuthService.hash_password("StrongPass123")

    assert first != second
    assert LocalAuthService.verify_password("StrongPass123", first)
    assert not LocalAuthService.verify_password("wrong-password", first)
    assert not LocalAuthService.verify_password("StrongPass123", "invalid-hash")


@pytest.mark.asyncio
async def test_register_creates_candidate_with_hashed_password():
    session = FakeSession()
    request = RegisterRequest(
        email="New.User@Example.com",
        password="StrongPass123",
        phone="0901234567",
        firstName="New",
        lastName="User",
    )

    user = await LocalAuthService().register(session, request)

    assert user is session.added
    assert user.email == "new.user@example.com"
    assert user.s4h_user_id.startswith("local:")
    assert user.roles == [UserRole.CANDIDATE.value]
    assert user.status == UserStatus.ACTIVE
    assert user.password_hash != request.password
    assert LocalAuthService.verify_password(request.password, user.password_hash)


@pytest.mark.asyncio
async def test_register_rejects_existing_email():
    session = FakeSession(query_result=SimpleNamespace(email="member@example.com"))
    request = RegisterRequest(
        email="MEMBER@example.com",
        password="StrongPass123",
        phone="0901234567",
        firstName="Existing",
        lastName="User",
    )

    with pytest.raises(RegistrationFailedException) as exc_info:
        await LocalAuthService().register(session, request)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_login_accepts_local_password_and_rejects_wrong_password():
    service = LocalAuthService()
    user = SimpleNamespace(
        email="member@example.com",
        status=UserStatus.ACTIVE,
        password_hash=service.hash_password("StrongPass123"),
    )
    session = FakeSession(query_result=user)

    authenticated = await service.login(
        session,
        LoginRequest(email="MEMBER@example.com", password="StrongPass123"),
    )
    assert authenticated is user

    with pytest.raises(InvalidCredentialsException):
        await service.login(
            session,
            LoginRequest(email="member@example.com", password="wrong-password"),
        )
