import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "BrandShield API"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./brandshield.db"

    # Security
    SECRET_KEY: str = "change-this-to-a-super-secret-random-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # File Uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "txt"]

    # AI Provider Configuration
    AI_PROVIDER: str = "gemini"  # "gemini" or "deepseek"
    AI_MODEL: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    AI_TEMPERATURE: float = 0.2
    AI_TIMEOUT: int = 45
    AI_MAX_RETRIES: int = 2

    @property
    def active_gemini_api_key(self) -> str:
        """
        Precedence: GEMINI_API_KEY is preferred for BrandShield.
        GOOGLE_API_KEY is supported as an optional alternative.
        """
        return (self.GEMINI_API_KEY or self.GOOGLE_API_KEY or "").strip()

    @property
    def active_gemini_model(self) -> str:
        """
        Precedence: GEMINI_MODEL is preferred.
        AI_MODEL is supported as fallback.
        Defaults to 'gemini-2.0-flash' if neither is set.
        """
        return (self.GEMINI_MODEL or self.AI_MODEL or "gemini-2.0-flash").strip()

    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        origins = list(self.CORS_ORIGINS)
        if self.FRONTEND_URL and self.FRONTEND_URL not in origins:
            origins.append(self.FRONTEND_URL)
        return origins


settings = Settings()
