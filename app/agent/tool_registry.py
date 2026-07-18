from __future__ import annotations

from app.agent.contracts import AgentToolCall, AgentToolDefinition


class InvalidAgentToolCallError(ValueError):
    pass


class ReadOnlyAgentToolRegistry:
    def __init__(self) -> None:
        self._tool_definitions_by_name = {
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
                    "contact and address state. Password is never returned."
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
