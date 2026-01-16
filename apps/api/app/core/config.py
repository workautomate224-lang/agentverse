"""
Application configuration settings
"""

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # Application
    PROJECT_NAME: str = "AgentVerse API"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentverse"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        if isinstance(v, list):
            return v
        return []

    # OpenRouter
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL: str = "openai/gpt-5.2"  # GPT-5.2 as default for PIL jobs

    # PIL (Project Intelligence Layer) Settings
    # Controls whether LLM fallbacks are allowed when OpenRouter calls fail
    # Set to "false" in staging/prod to ensure real LLM calls are made
    PIL_ALLOW_FALLBACK: bool = False  # Default: fail fast, no silent fallbacks

    # Sentry
    SENTRY_DSN: str | None = None

    # Census Data Integration
    CENSUS_API_KEY: str | None = None  # Optional - increases rate limits
    CENSUS_DEFAULT_YEAR: int = 2022
    USE_REAL_CENSUS_DATA: bool = True  # Enable real census data for personas

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # Simulation
    MAX_AGENTS_FREE: int = 1000
    MAX_AGENTS_PRO: int = 10000
    MAX_AGENTS_ENTERPRISE: int = 100000
    DEFAULT_BATCH_SIZE: int = 50
    SIMULATION_TIMEOUT_SECONDS: int = 300

    # Object Storage (S3-compatible) - project.md §5.4
    # Supports AWS S3, MinIO, DigitalOcean Spaces, etc.
    STORAGE_BACKEND: str = "s3"  # Options: "s3", "local", "gcs"
    STORAGE_BUCKET: str = "agentverse-artifacts"
    STORAGE_REGION: str = "us-east-1"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_ENDPOINT_URL: str | None = None  # For MinIO or other S3-compatible
    STORAGE_USE_SSL: bool = True
    STORAGE_LOCAL_PATH: str = "/tmp/agentverse-storage"  # For local backend

    # Storage path prefixes (tenant isolation - project.md §8.1)
    STORAGE_TELEMETRY_PREFIX: str = "telemetry"
    STORAGE_SNAPSHOTS_PREFIX: str = "snapshots"
    STORAGE_ARTIFACTS_PREFIX: str = "artifacts"

    # Signed URL expiration (project.md §8.4)
    STORAGE_URL_EXPIRATION_SECONDS: int = 3600  # 1 hour

    # Versioning - Platform versions (project.md §6.5)
    ENGINE_VERSION: str = "1.0.0"
    RULESET_VERSION: str = "1.0.0"
    SCHEMA_VERSION: str = "1.0.0"

    # Staging Operations (for chaos testing and Step 3.1 validation)
    # Set via Railway env var - only used in staging environment
    STAGING_OPS_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
