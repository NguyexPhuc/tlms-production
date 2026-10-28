"""
Custom exceptions for TLMS
"""
from fastapi import HTTPException, status


class S4HAuthException(HTTPException):
    """Exception for S4H Auth Service errors"""
    
    def __init__(self, detail: str = "Lỗi xác thực với hệ thống S4H"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


class S4HServiceUnavailableException(HTTPException):
    """Exception when S4H Auth Service is down"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hệ thống đăng nhập đang bảo trì. Vui lòng thử lại sau."
        )


class InvalidCredentialsException(HTTPException):
    """Exception for invalid login credentials"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tài khoản hoặc mật khẩu"
        )


class NotFoundException(HTTPException):
    """Generic Not Found Exception"""
    def __init__(self, detail: str = "Not Found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(HTTPException):
    """Generic Bad Request Exception"""
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class ForbiddenException(HTTPException):
    """Generic Forbidden Exception"""
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class TokenExpiredException(HTTPException):
    """Exception for expired or invalid token"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"}
        )


class UserNotFoundException(NotFoundException):
    """Exception when user is not found"""
    
    def __init__(self):
        super().__init__(
            detail="Không tìm thấy người dùng"
        )


class RegistrationFailedException(HTTPException):
    """Exception when registration fails"""
    
    def __init__(self, detail: str = "Đăng ký thất bại"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail
        )
