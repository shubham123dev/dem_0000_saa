from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.agent.action_contracts import AgentApprovalPolicy
from app.domain.enums import Permission

RiskLevel = Literal["low", "medium", "high"]


@dataclass(frozen=True)
class WorkplaceRiskDecision:
    risk_level: RiskLevel
    approval_policy: AgentApprovalPolicy
    reasons: tuple[str, ...]
    affected_count: int

    def public_dict(self) -> dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "approval_policy": self.approval_policy.model_dump(mode="json"),
            "reasons": list(self.reasons),
            "affected_count": self.affected_count,
        }


class WorkplaceRiskEvaluator:
    """Backend-owned dynamic risk policy for governed workflow actions."""

    @staticmethod
    def evaluate(
        *,
        action_name: str,
        required_permission: str,
        affected_count: int,
        destructive: bool = False,
        privileged: bool = False,
        access_change_count: int = 0,
    ) -> WorkplaceRiskDecision:
        if affected_count < 1 or affected_count > 500:
            raise ValueError("Affected resource count is invalid")
        reasons: list[str] = []
        high = False
        if destructive:
            reasons.append("destructive_or_revoking_operation")
            high = True
        if privileged:
            reasons.append("privileged_role_or_permission_change")
            high = True
        if affected_count > 5:
            reasons.append("more_than_five_resources")
            high = True
        if access_change_count > 3:
            reasons.append("more_than_three_access_changes")
            high = True
        if action_name in {
            "offboard_organization_user",
            "restore_workplace_resource_snapshots",
        }:
            reasons.append("workflow_policy_requires_independent_review")
            high = True
        if action_name == "apply_organization_access_package" and access_change_count:
            reasons.append("organization_access_package")
        if not reasons:
            reasons.append("bounded_governed_change")
        risk_level: RiskLevel = "high" if high else "medium"
        policy = AgentApprovalPolicy(
            self_approval_allowed=not high,
            required_approver_permission=required_permission,
            minimum_approvals=2 if high else 1,
        )
        return WorkplaceRiskDecision(
            risk_level=risk_level,
            approval_policy=policy,
            reasons=tuple(reasons),
            affected_count=affected_count,
        )

    @staticmethod
    def workflow_permission() -> str:
        return Permission.WORKPLACE_WORKFLOWS_MANAGE.value
