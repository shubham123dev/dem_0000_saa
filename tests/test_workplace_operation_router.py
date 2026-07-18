from __future__ import annotations

import json

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.action_registry import AgentActionRegistry
from app.agent.tool_registry import ReadOnlyAgentToolRegistry
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.registry import WorkplaceResourceRegistry


def test_operation_routes_are_unique_known_and_canonical() -> None:
    registry = WorkplaceResourceRegistry()
    router = WorkplaceOperationRouter(registry)
    known_actions = {
        item.name for item in AgentActionRegistry().list_definitions()
    }
    known_tools = {
        item.name for item in ReadOnlyAgentToolRegistry().list_tool_definitions()
    }
    seen = set()
    for route in router.list_routes():
        key = (route.resource_type, route.operation, route.fields)
        assert key not in seen
        seen.add(key)
        if route.route_kind == "action":
            assert route.target_name in known_actions
        else:
            assert route.target_name in known_tools

    organization = registry.get("organization")
    assert organization.field_map["display_name"].editable is False
    assert organization.field_map["contact_email"].editable is False
    catalog = {item["resource_type"]: item for item in router.public_catalog()}
    organization_routes = catalog["organization"]["routes"]
    assert any(
        item["target_name"] == "update_organization_contact_email"
        and item.get("fields") == ["contact_email"]
        for item in organization_routes
    )
    assert any(
        item["target_name"] == "update_nucleus_organization_account_field"
        and item.get("fields") == ["display_name"]
        for item in organization_routes
    )


def test_router_normalizes_synchronized_generic_proposals() -> None:
    router = WorkplaceOperationRouter()
    email = router.normalize_action_proposal(
        AgentActionProposalInput(
            action_name="update_workplace_resource",
            arguments={
                "resource_type": "organization",
                "resource_id": "org_sandbox_001",
                "changes_json": json.dumps(
                    {"contact_email": "new@example.test"}
                ),
            },
        )
    )
    assert email.action_name == "update_organization_contact_email"
    assert email.arguments == {"contact_email": "new@example.test"}

    name = router.normalize_action_proposal(
        AgentActionProposalInput(
            action_name="update_workplace_resource",
            arguments={
                "resource_type": "organization",
                "resource_id": "org_sandbox_001",
                "changes_json": json.dumps({"display_name": "New Name"}),
            },
        )
    )
    assert name.action_name == "update_nucleus_organization_account_field"
    assert name.arguments == {
        "field_name": "OrganizationName",
        "value": "New Name",
    }
