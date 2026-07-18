from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
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

    agent_run_poll_seconds: float = Field(default=0.75, ge=0.1, le=10)
    agent_run_lease_seconds: int = Field(default=45, ge=15, le=300)
    agent_run_lease_renew_seconds: int = Field(default=15, ge=5, le=120)
    agent_run_stream_poll_seconds: float = Field(default=0.5, ge=0.1, le=5)
    agent_run_heartbeat_seconds: float = Field(default=15.0, ge=5, le=60)

    action_maximum_pending_per_organization: int = Field(default=100, ge=1, le=1000)
    action_maximum_pending_per_user: int = Field(default=20, ge=1, le=200)
    action_maximum_proposals_per_user_per_minute: int = Field(default=10, ge=1, le=100)
    action_default_page_size: int = Field(default=25, ge=1, le=100)
    action_maximum_page_size: int = Field(default=100, ge=1, le=200)
    action_maximum_reconciliation_attempts: int = Field(default=5, ge=1, le=20)
    action_maximum_audit_replay_attempts: int = Field(default=5, ge=1, le=20)

    @model_validator(mode="after")
    def validate_agent_run_lease(self) -> "Settings":
        if self.agent_run_lease_renew_seconds >= self.agent_run_lease_seconds:
            raise ValueError(
                "agent_run_lease_renew_seconds must be shorter than agent_run_lease_seconds"
            )
        return self

    @property
    def is_sandbox(self) -> bool:
        return self.environment == "sandbox"


@lru_cache
def get_settings() -> Settings:
    return Settings()
