"""
Schemas package
"""
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
    RefreshedTokenResponse,
    S4HUserInfo,
    UserResponse,
    AuthenticatedUserResponse,
    MessageResponse,
    ErrorResponse
)

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
    "TokenResponse",
    "RefreshedTokenResponse",
    "S4HUserInfo",
    "UserResponse",
    "AuthenticatedUserResponse",
    "MessageResponse",
    "ErrorResponse"
]
