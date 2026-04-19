"""Application configuration loaded from environment variables."""

from typing import List, Set

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Central configuration — reads from .env or environment."""

    # App metadata
    APP_TITLE: str = "Data Validation & Cleaning API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "A FastAPI service that cleans, validates, and standardizes "
        "raw datasets into structured, production-ready data."
    )

    # Upload limits
    MAX_UPLOAD_MB: int = 15
    ALLOWED_EXTENSIONS: Set[str] = {".csv", ".xlsx", ".xls"}

    # Preview
    DEFAULT_PREVIEW_ROWS: int = 10

    # Groq AI
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def groq_available(self) -> bool:
        return bool(self.GROQ_API_KEY)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
