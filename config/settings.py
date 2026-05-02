"""Configuration management for Paperless-AI."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    paperless_url: str = Field(..., description="URL of the Paperless-ngx instance")
    paperless_api_token: str = Field(..., description="API token for Paperless-ngx")

    @field_validator("paperless_url")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load settings on first use. Lets `--help` work without env vars set."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    return Settings()
