import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional


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

    # NASA handover dataset (processed terrain / CTX / REMS / RAD).
    # Leave unset to use the resolver in app/data_pipeline/dataset_paths.py.
    DHRUVION_DATA_DIR: Optional[str] = None
    DATASET_STATIC_MOUNT: str = "/static/dhruvion"

    # Planning assumptions (not rover-verified telemetry)
    DEFAULT_TRAVEL_SPEED_M_PER_MIN: float = 60.0

    # AI assistant (Groq preferred, Ollama optional local fallback).
    LLM_ENABLED: bool = True
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_TIMEOUT_S: float = 20.0
    LLM_ANSWER_TIMEOUT_S: float = 30.0
    LLM_HEALTH_TIMEOUT_S: float = 2.0
    LLM_MAX_TOOL_ROUNDS: int = 3
    LLM_MAX_TOKENS: int = 100

    # Local fallback provider.
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "qwen2.5-coder:3b"

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