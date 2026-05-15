"""
Phase 1: Foundation - Configuration Management

All environment variables and settings in one place.
Follows Pydantic V2 BaseSettings pattern for validation and auto-reloading.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from typing import List
import os
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Priority: .env file > environment variables > defaults
    """

    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sanmitra_db",
        description="PostgreSQL async connection string",
    )
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string",
    )
    MONGODB_DB_NAME: str = Field(
        default="sanmitra",
        description="MongoDB database name",
    )

    # JWT Configuration
    JWT_SECRET: str = Field(
        default="your-super-secret-key-change-in-production",
        description="Secret key for JWT signing",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_HOURS: int = Field(default=24, description="JWT token expiration in hours")

    # Feature Flags
    MANDIR_USE_MODULAR_ROUTER: bool = Field(
        default=False,
        description="Feature flag: use new modular router (true) or old monolithic (false)",
    )

    # Environment Configuration
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=True, description="Enable debug mode")

    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1", description="API v1 prefix")
    API_TITLE: str = Field(default="SanMitra Backend", description="API title")
    API_VERSION: str = Field(default="1.0.0", description="API version")

    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="Allowed CORS origins",
    )

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL")

    # Pagination
    DEFAULT_LIMIT: int = Field(default=50, description="Default pagination limit")
    MAX_LIMIT: int = Field(default=200, description="Maximum pagination limit")

    # Multi-tenancy
    DEFAULT_TENANT_ID: str = Field(
        default="mandir_default",
        description="Default tenant ID for backward compatibility",
    )
    DEFAULT_APP_KEY: str = Field(
        default="mandirmitra",
        description="Default app key (mandirmitra, gruhamitra, etc.)",
    )

    # Pagination defaults
    PAGINATION_DEFAULT_PAGE: int = 1
    PAGINATION_DEFAULT_PAGE_SIZE: int = 50
    PAGINATION_MAX_PAGE_SIZE: int = 200

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string if needed"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Using @lru_cache ensures settings are loaded once and reused.
    """
    return Settings()


# Convenience function for import
settings = get_settings()
