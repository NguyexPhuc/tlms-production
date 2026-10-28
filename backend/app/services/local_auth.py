"""
Local development authentication fallback.

TLMS production auth still belongs to S4H. This service only issues local
tokens for seeded/local users when the external S4H Auth service is down.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import InvalidCredentialsException, TokenExpiredException
from app.models.user import User, UserStatus
from app.schemas.auth import LoginRequest, RefreshedTokenResponse, TokenResponse

settings = get_settings()

ALGORITHM = "HS256"
ISSUER = "tlms-local-dev"


class LocalAuthService:
    """Issue and validate local-only JWTs for development."""

    def _encode_token(self, user: User, token_type: str, expires_delta: timedelta) -> str:
        expires_at = datetime.utcnow() + expires_delta
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "typ": token_type,
            "iss": ISSUER,
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, settings.DEV_AUTH_SECRET_KEY, algorithm=ALGORITHM)

    def create_tokens(self, user: User) -> TokenResponse:
        return TokenResponse(
            accessToken=self._encode_token(
                user,
                "access",
                timedelta(minutes=settings.DEV_AUTH_ACCESS_TOKEN_MINUTES),
            ),
            refreshToken=self._encode_token(
                user,
                "refresh",
                timedelta(days=settings.DEV_AUTH_REFRESH_TOKEN_DAYS),
            ),
        )

    def refresh_access_token(self, refresh_token: str, user: User) -> RefreshedTokenResponse:
        self.decode_token(refresh_token, expected_type="refresh")
        return RefreshedTokenResponse(
            accessToken=self._encode_token(
                user,
                "access",
                timedelta(minutes=settings.DEV_AUTH_ACCESS_TOKEN_MINUTES),
            )
        )

    def decode_token(self, token: str, expected_type: str = "access") -> dict:
        try:
            payload = jwt.decode(token, settings.DEV_AUTH_SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise TokenExpiredException() from exc

        if payload.get("iss") != ISSUER or payload.get("typ") != expected_type:
            raise TokenExpiredException()
        return payload

    def is_local_token(self, token: str) -> bool:
        try:
            payload = jwt.get_unverified_claims(token)
        except JWTError:
            return False
        return payload.get("iss") == ISSUER

    async def get_user_from_token(
        self,
        db: AsyncSession,
        token: str,
        expected_type: str = "access",
    ) -> User:
        payload = self.decode_token(token, expected_type=expected_type)
        user_id = payload.get("sub")
        if not user_id:
            raise TokenExpiredException()

        stmt = select(User).where(User.id == UUID(user_id))
        result = await db.execute(stmt)
        user: Optional[User] = result.scalar_one_or_none()
        if user is None or user.status != UserStatus.ACTIVE:
            raise TokenExpiredException()
        return user

    async def login(self, db: AsyncSession, credentials: LoginRequest) -> User:
        if not settings.DEV_AUTH_FALLBACK_ENABLED:
            raise InvalidCredentialsException()

        if credentials.password != settings.DEV_AUTH_PASSWORD:
            raise InvalidCredentialsException()

        stmt = select(User).where(User.email == credentials.email)
        result = await db.execute(stmt)
        user: Optional[User] = result.scalar_one_or_none()
        if user is None or user.status != UserStatus.ACTIVE:
            raise InvalidCredentialsException()
        return user


local_auth_service = LocalAuthService()
