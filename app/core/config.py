from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
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
    agent_model_provider: str | None = None
    agent_model_api_key: str | None = None
    agent_model_name: str = "gpt-5-mini"
    agent_model_endpoint: str = "https://api.openai.com/v1/responses"
    agent_model_timeout_seconds: float = Field(default=20.0, gt=0, le=120)
    agent_model_maximum_attempts: int = Field(default=2, ge=1, le=3)
    agent_model_retry_delay_seconds: float = Field(default=0.25, ge=0, le=5)
    agent_model_maximum_output_tokens: int = Field(default=1000, ge=100, le=4000)

    @property
    def is_sandbox(self) -> bool:
        return self.environment == "sandbox"


@lru_cache
def get_settings() -> Settings:
    return Settings()
