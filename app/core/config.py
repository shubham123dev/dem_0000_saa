"""Application configuration.

Settings are loaded from environment variables (and an optional local `.env`
file). No secrets or personal information are stored here. Step 0 is
sandbox-only; production access remains explicitly out of scope.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the sandbox Workplace Agent backend."""

    model_config = SettingsConfigDict(
        env_prefix="WORKPLACE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "DBMR Workplace Agent (Sandbox)"
    database_url: str = "sqlite+aiosqlite:///./workplace_sandbox.db"
    environment: str = "sandbox"
    enable_raw_mock_api: bool = False

    @property
    def is_sandbox(self) -> bool:
        return self.environment == "sandbox"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""

    return Settings()
