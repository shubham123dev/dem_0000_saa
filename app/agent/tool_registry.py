from __future__ import annotations

from app.agent.contracts import AgentToolCall, AgentToolDefinition
from app.workplace_resources.operation_router import WorkplaceOperationRouter
from app.workplace_resources.relationships import WorkplaceRelationRegistry


_QUERY_CONTRACT = {
    "shape": {
        "all": [{"field": "field_name", "operator": "equals", "value": "value"}],
        "any": [],
    },
    "operators": [
        "equals",
        "not_equals",
        "contains",
        "starts_with",
        "in",
        "greater_than",
        "less_than",
        "between",
        "is_null",
        "is_not_null",
    ],
    "maximum_conditions": 20,
}


class InvalidAgentToolCallError(ValueError):
    pass


class ReadOnlyAgentToolRegistry:
    def __init__(self) -> None:
        resource_catalog = WorkplaceOperationRouter().public_catalog()
        relationship_catalog = tuple(
            item.public_dict()
            for item in WorkplaceRelationRegistry().list_definitions()
        )
        self._tool_definitions_by_name = {
            "get_current_user_profile": AgentToolDefinition(
                name="get_current_user_profile",
                description=(
                    "Read the currently authenticated user identity, display name, email, and user ID."
                ),
            ),
            "get_organization_overview": AgentToolDefinition(
                name="get_organization_overview",
                description=(
                    "Read the current organization overview, renewal, workspace "
                    "health and dashboard metrics."
                ),
            ),
            "get_nucleus_organization_account": AgentToolDefinition(
                name="get_nucleus_organization_account",
                description=(
                    "Read the exact-schema Nucleus OrganizationAccount profile, "
                    "contact and address state. Credentials are never returned."
                ),
            ),
            "get_nucleus_organization_license": AgentToolDefinition(
                name="get_nucleus_organization_license",
                description=(
                    "Read MaxUserLimit, LicenseStartDate, LicenseEndDate and "
                    "the current account status."
                ),
            ),
            "get_nucleus_organization_approval_status": AgentToolDefinition(
                name="get_nucleus_organization_approval_status",
                description=(
                    "Read approved/rejected state, reviewer identifiers, dates "
                    "and rejection reason for the current organization account."
                ),
            ),
            "get_nucleus_organization_entitlements": AgentToolDefinition(
                name="get_nucleus_organization_entitlements",
                description=(
                    "Read category, company profile, drug, indication, market, "
                    "report and special-permission access rows."
                ),
            ),
            "get_organization_profile": AgentToolDefinition(
                name="get_organization_profile",
                description="Read the current organization profile.",
            ),
            "list_organization_users": AgentToolDefinition(
                name="list_organization_users",
                description="List users in the current organization.",
            ),
            "get_organization_seat_summary": AgentToolDefinition(
                name="get_organization_seat_summary",
                description="Read the current organization seat summary.",
            ),
            "list_organization_reports": AgentToolDefinition(
                name="list_organization_reports",
                description="List reports and current organization access.",
            ),
            "check_organization_report_access": AgentToolDefinition(
                name="check_organization_report_access",
                description="Check current organization access to one report.",
                required_argument_names=("report_id",),
            ),
            "get_organization_audit_log": AgentToolDefinition(
                name="get_organization_audit_log",
                description="Read the current organization audit log.",
            ),
            "list_workplace_resource_types": AgentToolDefinition(
                name="list_workplace_resource_types",
                description=(
                    "List backend-registered workplace resources, safe fields, "
                    "available operations and canonical tool/action routes."
                ),
                metadata={"resource_catalog": resource_catalog},
            ),
            "describe_workplace_resource": AgentToolDefinition(
                name="describe_workplace_resource",
                description=(
                    "Describe one registered resource, its safe fields, allowed "
                    "operations and canonical routes."
                ),
                required_argument_names=("resource_type",),
            ),
            "search_workplace_resources": AgentToolDefinition(
                name="search_workplace_resources",
                description=(
                    "Search one generic organization-scoped resource using an "
                    "allowlisted equality-filter JSON object."
                ),
                required_argument_names=("resource_type", "filters_json"),
            ),
            "get_workplace_resource": AgentToolDefinition(
                name="get_workplace_resource",
                description=(
                    "Read one generic organization-scoped resource by its "
                    "backend-visible resource identifier."
                ),
                required_argument_names=("resource_type", "resource_id"),
            ),
            "count_workplace_resources": AgentToolDefinition(
                name="count_workplace_resources",
                description=(
                    "Count generic organization-scoped resources using an "
                    "allowlisted equality-filter JSON object."
                ),
                required_argument_names=("resource_type", "filters_json"),
            ),
            "list_related_workplace_resources": AgentToolDefinition(
                name="list_related_workplace_resources",
                description=(
                    "Traverse one backend-registered relationship from an "
                    "organization-scoped source resource."
                ),
                required_argument_names=(
                    "source_resource_type",
                    "source_resource_id",
                    "relationship",
                ),
                metadata={"relationships": relationship_catalog},
            ),
            "summarize_workplace_resources": AgentToolDefinition(
                name="summarize_workplace_resources",
                description=(
                    "Summarize a registered resource using the governed query "
                    "language and return counts plus a bounded sample."
                ),
                required_argument_names=("resource_type", "query_json"),
                metadata={"query_contract": _QUERY_CONTRACT},
            ),
            "compare_workplace_resources": AgentToolDefinition(
                name="compare_workplace_resources",
                description=(
                    "Compare two to ten resources of the same registered type "
                    "and return only backend-readable field differences."
                ),
                required_argument_names=(
                    "resource_type",
                    "resource_ids_json",
                ),
                metadata={
                    "resource_ids_json": "JSON array of two to ten resource IDs"
                },
            ),
            "explain_workplace_resource_capabilities": AgentToolDefinition(
                name="explain_workplace_resource_capabilities",
                description=(
                    "Explain safe fields, canonical routes, relationships and "
                    "query operators for one registered resource."
                ),
                required_argument_names=("resource_type",),
            ),
        }

    def list_tool_definitions(self) -> tuple[AgentToolDefinition, ...]:
        return tuple(self._tool_definitions_by_name.values())

    def validate_tool_call(self, tool_call: AgentToolCall) -> AgentToolCall:
        tool_definition = self._tool_definitions_by_name.get(tool_call.tool_name)
        if tool_definition is None:
            raise InvalidAgentToolCallError("Unknown agent tool")

        supplied_argument_names = set(tool_call.arguments)
        required_argument_names = set(tool_definition.required_argument_names)
        if supplied_argument_names != required_argument_names:
            raise InvalidAgentToolCallError("Agent tool arguments are invalid")

        forbidden_argument_names = {
            "organization_id",
            "user_id",
            "actor_user_id",
            "permission",
            "role",
        }
        if supplied_argument_names & forbidden_argument_names:
            raise InvalidAgentToolCallError(
                "Identity and authorization arguments are forbidden"
            )

        return tool_call
