"""First-party authentication used when S4H is unavailable."""
import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidCredentialsException,
    RegistrationFailedException,
    TokenExpiredException,
)
from app.models.user import MemberLevel, User, UserRole, UserStatus
from app.schemas.auth import LoginRequest, RefreshedTokenResponse, RegisterRequest, TokenResponse

settings = get_settings()

ALGORITHM = "HS256"
ISSUER = "tlms-local-dev"
PASSWORD_SCHEME = "scrypt"
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 64


class LocalAuthService:
    """Manage standalone TLMS credentials and local JWTs."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Return a versioned, salted scrypt password hash."""
        salt = os.urandom(16)
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R,
            p=SCRYPT_P, dklen=SCRYPT_DKLEN,
        )
        encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")
        encoded_digest = base64.urlsafe_b64encode(digest).decode("ascii")
        return f"{PASSWORD_SCHEME}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encoded_salt}${encoded_digest}"

    @staticmethod
    def verify_password(password: str, encoded_hash: str) -> bool:
        """Verify a password without leaking timing information."""
        try:
            scheme, n, r, p, encoded_salt, encoded_digest = encoded_hash.split("$", 5)
            if scheme != PASSWORD_SCHEME:
                return False
            salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
            expected = base64.urlsafe_b64decode(encoded_digest.encode("ascii"))
            actual = hashlib.scrypt(
                password.encode("utf-8"), salt=salt, n=int(n), r=int(r),
                p=int(p), dklen=len(expected),
            )
            return hmac.compare_digest(actual, expected)
        except (ValueError, TypeError, UnicodeError):
            return False

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
        stmt = select(User).where(func.lower(User.email) == credentials.email.strip().lower())
        result = await db.execute(stmt)
        user: Optional[User] = result.scalar_one_or_none()
        if user is None or user.status != UserStatus.ACTIVE:
            raise InvalidCredentialsException()

        local_password_valid = bool(
            settings.LOCAL_AUTH_ENABLED
            and user.password_hash
            and self.verify_password(credentials.password, user.password_hash)
        )
        shared_dev_password_valid = bool(
            settings.DEV_AUTH_FALLBACK_ENABLED
            and settings.DEV_AUTH_PASSWORD
            and hmac.compare_digest(credentials.password, settings.DEV_AUTH_PASSWORD)
        )
        if not local_password_valid and not shared_dev_password_valid:
            raise InvalidCredentialsException()
        return user

    async def register(self, db: AsyncSession, user_data: RegisterRequest) -> User:
        """Create a standalone candidate account without claiming an existing email."""
        if not settings.LOCAL_AUTH_ENABLED:
            raise RegistrationFailedException("Đăng ký TLMS cục bộ đang tắt")

        email = str(user_data.email).strip().lower()
        existing = await db.execute(select(User).where(func.lower(User.email) == email))
        if existing.scalar_one_or_none() is not None:
            raise RegistrationFailedException("Email đã được đăng ký")

        user = User(
            s4h_user_id=f"local:{uuid4()}", email=email,
            phone=user_data.phone.strip(), first_name=user_data.firstName.strip(),
            last_name=user_data.lastName.strip(),
            password_hash=self.hash_password(user_data.password),
            roles=[UserRole.CANDIDATE.value], status=UserStatus.ACTIVE,
            current_xp=0, discipline_score=100.0, reliability_score=100.0,
            member_score=0.0, promotion_progress=0.0,
            member_level=MemberLevel.NEW, level=1,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


local_auth_service = LocalAuthService()
