from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ActionCapabilityOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    label: str
    description: str
    resource_label: str
    risk_level: Literal["low", "medium", "high"]
    requires_approval: bool
    supports_dry_run: bool
    available: bool


class ActionCapabilityCatalogueOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    action_capabilities: tuple