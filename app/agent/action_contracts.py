from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import OrganizationProfile


class AgentApprovalPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    self_approval_allowed: bool = True
    required_approver_permission: str
    minimum_approvals: int = Field(default=1, ge=1, le=10)


