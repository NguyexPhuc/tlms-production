"""
TLMS Application Configuration
Loads settings from environment variables
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "TLMS"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RUN_SCHEDULER: bool = True
    AUTO_CREATE_SCHEMA: bool = True
    WORKER_DB_WAIT_SECONDS: int = 300
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tlms"
    
    # S4H Auth Service - Identity Provider
    S4H_AUTH_BASE_URL: str = "http://api-auth.aisteamx.edu.vn"

    # First-party local accounts keep TLMS usable when the external identity
    # provider is unavailable. Passwords are stored only as salted hashes.
    LOCAL_AUTH_ENABLED: bool = True

    # Local development auth fallback.
    # This is used only for local seeded TLMS users when S4H Auth is unavailable.
    DEV_AUTH_FALLBACK_ENABLED: bool = False
    DEV_AUTH_PASSWORD: str = ""
    DEV_AUTH_SECRET_KEY: str = ""
    DEV_AUTH_ACCESS_TOKEN_MINUTES: int = 1440
    DEV_AUTH_REFRESH_TOKEN_DAYS: int = 7

    # LHU External API
    LHU_API_BASE_URL: str = "https://tapi.lhu.edu.vn"

    # LHU MySQL Database (for Student ID Sync)
    LHU_MYSQL_HOST: str = ""
    LHU_MYSQL_PORT: int = 3306
    LHU_MYSQL_USER: str = ""
    LHU_MYSQL_PASSWORD: str = ""
    LHU_MYSQL_DATABASE: str = ""

    # Webhook Security - API Key for S4H check-in webhook
    WEBHOOK_API_KEY: str = ""

    # Dedicated secret for free-tier scheduled job callbacks from GitHub Actions.
    SCHEDULER_API_KEY: str = ""

    # MongoDB (for User Import from S4H)
    MONGODB_CONNECTION_STRING: str = ""
    MONGODB_DATABASE: str = "checkin_service"
    MONGODB_USERS_COLLECTION: str = "users"

    # User Import Security - Secret Token for admin operations
    USER_IMPORT_SECRET_TOKEN: str = ""

    # Member development thresholds
    DAILY_TASK_COMPLETE_THRESHOLD: float = 1.0
    DAILY_TASK_PARTIAL_THRESHOLD: float = 0.01
    DAILY_DISCIPLINE_COMPLETE_BONUS: float = 1.0
    DAILY_DISCIPLINE_PARTIAL_PENALTY: float = -1.0
    DAILY_DISCIPLINE_MISSED_PENALTY: float = -3.0
    DAILY_RELIABILITY_COMPLETE_BONUS: float = 1.0
    DAILY_RELIABILITY_PARTIAL_PENALTY: float = -2.0
    DAILY_RELIABILITY_MISSED_PENALTY: float = -5.0
    PROMOTION_ATTENDANCE_THRESHOLD: float = 80.0
    PROMOTION_TASK_COMPLETION_THRESHOLD: float = 80.0
    PROMOTION_SCORE_THRESHOLD: float = 70.0
    MEMBER_EVALUATION_TASK_WEIGHT: float = 0.40
    MEMBER_EVALUATION_QUALITY_WEIGHT: float = 0.25
    MEMBER_EVALUATION_ATTENDANCE_WEIGHT: float = 0.20
    MEMBER_EVALUATION_DISCIPLINE_WEIGHT: float = 0.15

    # Daily Quest generation
    AI_PROVIDER: str = "openai"
    AI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    AI_MODEL: str = ""
    DAILY_QUEST_LIMIT: int = 5
    DAILY_QUEST_RESET_HOUR: int = 0
    AI_AUTO_PASS_SCORE: int = 70
    UPLOAD_DIR: str = "uploads"
    QUEST_PROOF_UPLOAD_DIR: str = "quest_proofs"
    MAX_UPLOAD_BYTES: int = 5000000

    # Digital certification
    PUBLIC_WEB_URL: str = "http://localhost:3000"
    CERTIFICATE_STORAGE_DIR: str = "private/certificates"
    CERTIFICATE_ISSUER_NAME: str = "T&A Lab"
    CERTIFICATE_VERIFY_RATE_LIMIT: int = 30
    CERTIFICATION_READ_ONLY: bool = True

    # File storage. Production uses an S3-compatible private bucket (for example R2).
    STORAGE_BACKEND: str = "local"
    S3_ENDPOINT_URL: str = ""
    S3_REGION: str = "auto"
    S3_BUCKET: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""

    # Weekly cup competition
    WEEKLY_CUP_MIN_DISCIPLINE: float = 80.0
    WEEKLY_CUP_OPEN_WEEKDAY: int = 4  # Monday=0, Friday=4
    WEEKLY_CUP_OPEN_HOUR: int = 0
    WEEKLY_CUP_DURATION_HOURS: int = 24

    # Optional Zalo OA Daily Task Quiz integration. Secrets stay in environment variables.
    ZALO_INTEGRATION_ENABLED: bool = False
    ZALO_PROVIDER: str = "mock"
    ZALO_APP_ID: str = ""
    ZALO_APP_SECRET: str = ""
    ZALO_OA_ID: str = ""
    ZALO_OA_SECRET_KEY: str = ""
    ZALO_OA_ACCESS_TOKEN: str = ""
    ZALO_OA_REFRESH_TOKEN: str = ""
    ZALO_OA_SEND_URL: str = "https://openapi.zalo.me/v3.0/oa/message/cs"
    ZALO_OA_TOKEN_URL: str = "https://oauth.zaloapp.com/v4/oa/access_token"
    ZALO_WEB_APP_URL: str = "http://localhost:3000"
    ZALO_LINK_TOKEN_MINUTES: int = 15
    ZALO_WEBHOOK_MAX_SKEW_SECONDS: int = 300

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Normalize managed PostgreSQL URLs for SQLAlchemy's asyncpg dialect."""
        url = make_url(value)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+asyncpg")

        if url.drivername == "postgresql+asyncpg":
            query = dict(url.query)
            ssl_mode = query.pop("sslmode", None)
            query.pop("channel_binding", None)
            if ssl_mode and "ssl" not in query:
                query["ssl"] = "disable" if ssl_mode == "disable" else "require"
            url = url.set(query=query)

        return url.render_as_string(hide_password=False)
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

settings = get_settings()

