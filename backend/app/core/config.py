import os
from typing import List
from pydantic import field_validator
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
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
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

    @classmethod
    def _normalize_pg_scheme(cls, raw_url: str) -> str:
        """
        Safely normalize PostgreSQL connection schemes for SQLAlchemy 2.
        - Converts legacy postgres:// to postgresql://
        - If bare postgresql:// is provided without an explicit driver (+psycopg2, etc.)
          and psycopg (v3) is not installed in the environment, routes to +psycopg2
          to ensure compatibility with psycopg2-binary.
        - Preserves postgresql+psycopg2://, postgresql+psycopg://, sqlite:///, etc.
        """
        url = (raw_url or "").strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            try:
                import psycopg  # noqa: F401
            except ImportError:
                url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url_input(cls, v: str) -> str:
        """
        Safely normalize database URL inputs on model instantiation.
        """
        if isinstance(v, str):
            return cls._normalize_pg_scheme(v)
        return v

    @property
    def normalized_database_url(self) -> str:
        """
        Ensures a normalized database URL compatible with SQLAlchemy 2 and Alembic.
        """
        return self._normalize_pg_scheme(self.DATABASE_URL)

    @property
    def safe_database_info(self) -> str:
        """
        Returns dialect and host information with credentials masked.
        Never prints or logs database passwords or sensitive credentials.
        """
        url = self.normalized_database_url
        if url.startswith("sqlite"):
            return "sqlite"
        try:
            from sqlalchemy.engine import make_url
            u = make_url(url)
            host_str = u.host or "localhost"
            port_str = f":{u.port}" if u.port else ""
            db_name = f"/{u.database}" if u.database else ""
            return f"{u.drivername}://***:***@{host_str}{port_str}{db_name}"
        except Exception:
            scheme = url.split("://", 1)[0] if "://" in url else "unknown"
            return f"{scheme}://***"

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
