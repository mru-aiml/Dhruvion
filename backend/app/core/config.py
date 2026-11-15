import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./dhruvion.db"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    COOKIE_NAME: str = "dhruvion_access_token"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # API
    API_PREFIX: str = "/api"
    API_TITLE: str = "DHRUVION API"
    API_VERSION: str = "0.1.0"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Data paths
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = Path(__file__).resolve().parents[3] / "data"
    PROCESSED_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "processed"
    REPORTS_DIR: Path = Path(__file__).resolve().parents[3] / "data" / "processed" / "reports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()

# Backward compatibility exports for existing code
DATABASE_URL = settings.DATABASE_URL
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
COOKIE_NAME = settings.COOKIE_NAME
FRONTEND_ORIGIN = settings.FRONTEND_ORIGIN