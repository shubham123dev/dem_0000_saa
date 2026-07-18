from __future__ import annotations

from datetime import datetime, timezone

from app.agent.action_contracts import (
    AgentActionChange,
    AgentActionResourcePrecondition,
    AgentApprovalPolicy,
)
from app.agent.action_registry import AgentActionRegistry, build_action_fingerprint
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.relationships import WorkplaceRelationRegistry
from app.workplace_resources.risk import WorkplaceRiskEvaluator


def test_final_surface_and_internal_rollback_boundary() -> None:
    action_registry = AgentActionRegistry()
    registered = {item.name for item in action_registry.list_definitions()}
    model_actions = {item.name for item in action_registry.list_model_definitions()}
    tools = {
        item.name
        for item in ReadOnlyAgentToolRegistry().list_tool_definitions()
    }
    assert len(registered) == 43
    assert len(model_actions) == 42
    assert len(tools) == 20
    assert "restore_workplace_resource_snapshots" in registered
    assert "restore_workplace_resource_snapshots" not in model_actions
    assert {
        "list_related_workplace_resources",
        "summarize_workplace_resources",
        "compare_workplace_resources",
        "explain_workplace_resource_capabilities",
    }.issubset(tools)


def test_relationships_and_routes_are_backend_owned() -> None:
    relations = WorkplaceRelationRegistry().list_definitions()
    assert len(relations) == 17
    assert len(
        {(item.source_resource_type, item.name) for item in relations}
    ) == 17
    router = WorkplaceOperationRouter()
    routed_actions = {
        item.target_name
        for item in router.list_routes()
        if item.route_kind == "action"
    }
    assert {
        "onboard_organization_user",
        "offboard_organization_user",
        "apply_organization_access_package",
        "bulk_update_workplace_resources_by_query",
    }.issubset(routed_actions)
    relation_sources = {item.source_resource_type for item in relations}
    for route in router.list_routes():
        if route.operation == "list_related":
            assert route.resource_type in relation_sources
    assert not any(
        route.resource_type == "organization" and route.operation == "compare"
        for route in router.list_routes()
    )


def test_dynamic_risk_requires_independent_review_when_needed() -> None:
    normal = WorkplaceRiskEvaluator.evaluate(
        action_name="onboard_organization_user",
        required_permission="workplace.workflows.manage",
        affected_count=1,
    )
    assert normal.risk_level == "medium"
    assert normal.approval_policy.minimum_approvals == 1
    assert normal.approval_policy.self_approval_allowed is True

    high = WorkplaceRiskEvaluator.evaluate(
        action_name="apply_organization_access_package",
        required_permission="workplace.workflows.manage",
        affected_count=6,
        access_change_count=6,
    )
    assert high.risk_level == "high"
    assert high.approval_policy.minimum_approvals == 2
    assert high.approval_policy.self_approval_allowed is False


def test_fingerprint_v4_binds_dynamic_risk_and_keeps_v3_available() -> None:
    common = {
        "organization_id": "org_sandbox_001",
        "requested_by_user_id": "usr_admin_001",
        "action_name": "onboard_organization_user",
        "arguments": {"email": "risk@example.test"},
        "changes": (
            AgentActionChange(field="workflow", before=None, after={"active": True}),
        ),
        "observed_resource_version": 0,
        "approval_policy": AgentApprovalPolicy(
            self_approval_allowed=True,
            required_approver_permission="workplace.workflows.manage",
            minimum_approvals=1,
        ),
        "resource_type": "organization_user_onboarding",
        "resource_id": "risk@example.test",
        "resource_preconditions": (
            AgentActionResourcePrecondition(
                resource_type="organization_membership",
                resource_id="risk@example.test",
                observed_version=0,
            ),
        ),
        "expires_at": datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc),
    }
    medium = build_action_fingerprint(
        **common, fingerprint_version=4, risk_level="medium"
    )
    high = build_action_fingerprint(
        **common, fingerprint_version=4, risk_level="high"
    )
    historical = build_action_fingerprint(**common, fingerprint_version=3)
    assert medium != high
    assert historical not in {medium, high}
