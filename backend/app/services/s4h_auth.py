"""
S4H Auth Service Integration
Implements Proxy Authentication Pattern as described in oauth.md

This service handles all communication with S4H Auth Service:
- POST /auth/login - Login and get tokens
- POST /auth/register - Register new user
- POST /auth/refresh - Refresh access token
- GET /users/me - Validate token and get user info
"""
import httpx
import logging
from typing import Optional, Tuple
from app.core.config import get_settings
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    TokenResponse,
    RefreshedTokenResponse,
    S4HUserInfo
)
from app.core.exceptions import (
    S4HAuthException,
    S4HServiceUnavailableException,
    InvalidCredentialsException,
    TokenExpiredException,
    RegistrationFailedException
)

logger = logging.getLogger(__name__)
settings = get_settings()


class S4HAuthService:
    """
    Service for integrating with S4H Auth Identity Provider
    
    Important Security Notes (from oauth.md):
    - NEVER log or store passwords (Zero Trust Password policy)
    - Password only passes through RAM, never written to disk
    """
    
    def __init__(self):
        self.base_url = settings.S4H_AUTH_BASE_URL
        self.timeout = 30.0  # seconds
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        headers: Optional[dict] = None
    ) -> Tuple[int, dict]:
        """
        Make HTTP request to S4H Auth Service
        
        Returns:
            Tuple of (status_code, response_data)
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=headers
                )
                
                # Try to parse JSON response
                try:
                    data = response.json()
                except Exception:
                    data = {"message": response.text}
                
                return response.status_code, data
                
        except httpx.TimeoutException:
            logger.error(f"Timeout connecting to S4H Auth: {endpoint}")
            raise S4HServiceUnavailableException()
        except httpx.ConnectError:
            logger.error(f"Cannot connect to S4H Auth: {endpoint}")
            raise S4HServiceUnavailableException()
        except Exception as e:
            logger.error(f"Error communicating with S4H Auth: {str(e)}")
            raise S4HServiceUnavailableException()
    
    async def login(self, credentials: LoginRequest) -> TokenResponse:
        """
        Forward login request to S4H Auth Service
        
        Flow (from oauth.md section 4.1):
        1. Receive email and password from client
        2. Forward to S4H /auth/login
        3. If 200: Return JWT tokens
        4. If 400/401: Return "Sai tài khoản hoặc mật khẩu"
        
        IMPORTANT: Password is NEVER logged or stored
        """
        # DO NOT log password - Zero Trust Password policy
        logger.info(f"Login attempt for email: {credentials.email}")
        
        status_code, data = await self._make_request(
            method="POST",
            endpoint="/auth/login",
            json_data={
                "email": credentials.email,
                "password": credentials.password  # Forward as-is, not stored
            }
        )
        
        if status_code == 200:
            logger.info(f"Login successful for: {credentials.email}")
            return TokenResponse(
                accessToken=data.get("accessToken", ""),
                refreshToken=data.get("refreshToken", "")
            )
        elif status_code in [400, 401]:
            logger.warning(f"Login failed for: {credentials.email}")
            raise InvalidCredentialsException()
        else:
            logger.error(f"Unexpected response from S4H Auth: {status_code}")
            raise S4HAuthException(detail="Lỗi không xác định từ hệ thống xác thực")
    
    async def register(self, user_data: RegisterRequest) -> bool:
        """
        Forward registration request to S4H Auth Service
        
        Endpoint: POST /auth/register
        Input: { email, password, phone, firstName, lastName }
        Output: 200 OK on success
        
        IMPORTANT: Password is NEVER logged or stored
        """
        # DO NOT log password
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        status_code, data = await self._make_request(
            method="POST",
            endpoint="/auth/register",
            json_data={
                "email": user_data.email,
                "password": user_data.password,  # Forward as-is, not stored
                "phone": user_data.phone,
                "firstName": user_data.firstName,
                "lastName": user_data.lastName
            }
        )
        
        if status_code == 200:
            logger.info(f"Registration successful for: {user_data.email}")
            return True
        elif status_code == 400:
            detail = data.get("message", "Email đã tồn tại hoặc dữ liệu không hợp lệ")
            logger.warning(f"Registration failed for {user_data.email}: {detail}")
            raise RegistrationFailedException(detail=detail)
        elif status_code == 409:
            logger.warning(f"Registration failed - email exists: {user_data.email}")
            raise RegistrationFailedException(detail="Email đã được đăng ký")
        else:
            logger.error(f"Unexpected registration response: {status_code}")
            raise S4HAuthException(detail="Lỗi không xác định khi đăng ký")
    
    async def refresh_token(self, refresh_request: RefreshTokenRequest) -> RefreshedTokenResponse:
        """
        Refresh access token using refresh token
        
        Endpoint: POST /auth/refresh
        Input: { refreshToken }
        Output: { accessToken }
        """
        logger.info("Token refresh attempt")
        
        status_code, data = await self._make_request(
            method="POST",
            endpoint="/auth/refresh",
            json_data={
                "refreshToken": refresh_request.refreshToken
            }
        )
        
        if status_code == 200:
            logger.info("Token refresh successful")
            return RefreshedTokenResponse(
                accessToken=data.get("accessToken", "")
            )
        elif status_code == 401:
            logger.warning("Token refresh failed - invalid refresh token")
            raise TokenExpiredException()
        else:
            logger.error(f"Unexpected refresh response: {status_code}")
            raise S4HAuthException(detail="Lỗi làm mới token")
    
    async def get_user_info(self, access_token: str) -> S4HUserInfo:
        """
        Validate token and get user info from S4H Auth
        
        Used for Token Introspection (oauth.md section 4.2):
        1. Call GET /users/me with Bearer token
        2. If 200: Token valid, return user info
        3. If 401: Token expired/invalid
        
        This is called by middleware on every protected request
        """
        status_code, data = await self._make_request(
            method="GET",
            endpoint="/users/me",
            headers={
                "Authorization": f"Bearer {access_token}"
            }
        )
        
        if status_code == 200:
            return S4HUserInfo(
                id=data.get("id", ""),
                email=data.get("email", ""),
                phone=data.get("phone"),  # Get phone from S4H if available
                firstName=data.get("firstName"),
                lastName=data.get("lastName"),
                role=data.get("role"),
                studentCode=data.get("studentCode")  # Get student code if available
            )
        elif status_code == 401:
            raise TokenExpiredException()
        else:
            logger.error(f"Unexpected user info response: {status_code}")
            raise S4HAuthException(detail="Lỗi lấy thông tin người dùng")


# Singleton instance
s4h_auth_service = S4HAuthService()
