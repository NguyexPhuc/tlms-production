"""
Authentication Routes
Implements the auth endpoints using S4H Auth Service (Proxy Pattern)

Endpoints:
- POST /auth/login - Login through S4H Auth
- POST /auth/register - Register through S4H Auth  
- POST /auth/refresh - Refresh token through S4H Auth
- POST /auth/logout - Logout (client-side token removal)
- GET /auth/me - Get current user info
"""
import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import (
    AccountNotRegisteredException,
    InvalidCredentialsException,
    S4HServiceUnavailableException,
)
from app.api.deps import get_current_user
from app.services.local_auth import local_auth_service
from app.services.s4h_auth import s4h_auth_service
from app.services.user import user_service
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
    RefreshedTokenResponse,
    UserResponse,
    AuthenticatedUserResponse,
    MessageResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def build_user_response(user: User) -> UserResponse:
    """Map a local user model to the public auth response shape."""
    display_level = user.calculate_level()
    return UserResponse(
        id=str(user.id),
        s4h_user_id=user.s4h_user_id,
        email=user.email,
        phone=user.phone,
        student_id=user.student_id,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        full_name=user.full_name,
        roles=user.roles or ['candidate'],
        primary_role=user.primary_role,
        status=user.status.value if hasattr(user.status, 'value') else user.status,
        current_xp=user.current_xp,
        discipline_score=user.discipline_score,
        level=display_level,
        reliability_score=user.reliability_score,
        member_score=user.member_score,
        promotion_progress=user.promotion_progress,
        member_level=user.member_level,
        core_task_progress=user.core_task_progress,
        is_ready_to_promote=user.is_ready_to_promote,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at
    )


def build_authenticated_response(tokens: TokenResponse, user: User) -> AuthenticatedUserResponse:
    return AuthenticatedUserResponse(
        tokens=tokens,
        user=build_user_response(user)
    )


@router.post(
    "/login",
    response_model=AuthenticatedUserResponse,
    summary="Đăng nhập",
    description="""
    Đăng nhập vào hệ thống TLMS.
    
    **Quy trình (Proxy Authentication):**
    1. Nhận email/password từ client
    2. Forward đến S4H Auth Service để xác thực
    3. Nếu thành công: Trả về JWT tokens và thông tin user local
    4. Nếu thất bại: Trả về lỗi "Sai tài khoản hoặc mật khẩu"
    
    **Lưu ý:** Password không được lưu trữ trong hệ thống này.
    """
)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login Flow (oauth.md section 4.1):
    1. Client sends email/password to Python Backend
    2. Python Backend forwards to S4H /auth/login
    3. If 200: Return JWT Token
    4. If 400/401: Return error
    
    S4H passwords are never stored. Standalone TLMS passwords are stored only
    as salted scrypt hashes when the identity provider is unavailable.
    """
    local_user = await local_auth_service.get_user_by_email(db, credentials.email)

    # Accounts with a local password must fail with 401 on a wrong password;
    # they must not be mislabeled as an S4H outage.
    if local_user is not None and local_user.password_hash:
        user = await local_auth_service.login(db, credentials)
        tokens = local_auth_service.create_tokens(user)
        await user_service.update_user_login(db, user)
        logger.info("Local login successful: %s", user.email)
        return build_authenticated_response(tokens, user)

    # Optional shared development fallback for legacy seeded users.
    try:
        user = await local_auth_service.login(db, credentials)
        tokens = local_auth_service.create_tokens(user)
        await user_service.update_user_login(db, user)
        logger.info(f"Local dev login successful: {user.email}")
        return build_authenticated_response(tokens, user)
    except InvalidCredentialsException:
        pass

    try:
        # Forward login to S4H Auth
        tokens = await s4h_auth_service.login(credentials)

        # Get user info from S4H with the new token
        s4h_user_info = await s4h_auth_service.get_user_info(tokens.accessToken)

        # Lazy Sync: Get or create local user
        user = await user_service.get_or_create_user(db, s4h_user_info)
    except S4HServiceUnavailableException:
        if local_user is None:
            raise AccountNotRegisteredException()
        # A known S4H-only account cannot be verified while the provider is
        # unavailable, so preserve the accurate service outage response.
        raise
    
    # Update last login
    await user_service.update_user_login(db, user)
    
    logger.info(f"User logged in: {user.email}")
    return build_authenticated_response(tokens, user)


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản mới",
    description="""
    Đăng ký tài khoản mới trong hệ thống.
    
    **Quy trình:**
    1. Nhận thông tin đăng ký từ client
    2. Forward đến S4H Auth Service
    3. Nếu thành công: Trả về thông báo thành công
    4. Nếu thất bại: Trả về lỗi (email đã tồn tại, etc.)
    
    **Lưu ý:** 
    - Password không được lưu trong hệ thống TLMS
    - User local sẽ được tạo tự động khi đăng nhập lần đầu
    """
)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register through S4H Auth, with a standalone TLMS fallback during outages.

    Existing emails are never claimed by the fallback registration flow.
    """
    try:
        await s4h_auth_service.register(user_data)
    except S4HServiceUnavailableException:
        await local_auth_service.register(db, user_data)
    
    logger.info(f"New user registered: {user_data.email}")
    
    return MessageResponse(
        message="Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.",
        success=True
    )


@router.post(
    "/refresh",
    response_model=RefreshedTokenResponse,
    summary="Làm mới Access Token",
    description="""
    Làm mới access token bằng refresh token.
    
    **Sử dụng khi:**
    - Access token hết hạn (401 Unauthorized)
    - Client cần token mới mà không cần đăng nhập lại
    """
)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    Forward to S4H /auth/refresh
    """
    if local_auth_service.is_local_token(refresh_request.refreshToken):
        user = await local_auth_service.get_user_from_token(
            db,
            refresh_request.refreshToken,
            expected_type="refresh",
        )
        result = local_auth_service.refresh_access_token(refresh_request.refreshToken, user)
        logger.info("Local dev token refreshed successfully")
        return result

    result = await s4h_auth_service.refresh_token(refresh_request)
    
    logger.info("Token refreshed successfully")
    
    return result


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất",
    description="""
    Đăng xuất khỏi hệ thống.
    
    **Lưu ý:** 
    - JWT tokens là stateless, server không lưu session
    - Client cần tự xóa tokens khỏi storage
    - Endpoint này chỉ để confirm và có thể dùng cho logging
    """
)
async def logout(current_user: User = Depends(get_current_user)):
    """
    Logout user
    
    Since JWT is stateless, actual logout happens client-side
    by removing the tokens from storage.
    
    This endpoint:
    1. Confirms valid token
    2. Logs the logout event
    3. Returns success message
    
    For better security, consider implementing token blacklist
    using Redis (mentioned in oauth.md section 6).
    """
    logger.info(f"User logged out: {current_user.email}")
    
    return MessageResponse(
        message="Đăng xuất thành công",
        success=True
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin user hiện tại",
    description="""
    Lấy thông tin chi tiết của user đang đăng nhập.
    
    **Yêu cầu:** Bearer token trong header Authorization
    """
)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user info
    This also validates the token is still valid
    """
    return build_user_response(current_user)
