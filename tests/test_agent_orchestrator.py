from __future__ import annotations

from datetime import date

import pytest

from app.agent.contracts import AgentPlan, AgentToolCall
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.tool_registry import InvalidAgentToolCallError, ReadOnlyAgentToolRegistry
from app.core.errors import OrganizationAccessDeniedError
from app.domain.enums import (
    Environment,
    OrganizationStatus,
    UserStatus,
    WorkspaceHealthStatus,
)
from app.domain.models import (
    OrganizationOverview,
    OrganizationOverviewMetrics,
    OrganizationProfile,
    User,
)

EXPECTED_ACTION_NAMES = {
    "update_organization_contact_email",
    "update_nucleus_organization_account_field",
    "clear_nucleus_organization_account_field",
    "grant_nucleus_category_access",
    "revoke_nucleus_category_access",
    "grant_nucleus_report_access",
    "revoke_nucleus_report_access",
    "update_nucleus_organization_permissions",
    "update_nucleus_organization_username",
    "update_nucleus_organization_license",
    "approve_nucleus_organization_account",
    "reject_nucleus_organization_account",
    "activate_nucleus_organization_account",
    "deactivate_nucleus_organization_account",
    "grant_nucleus_company_profile_access",
    "revoke_nucleus_company_profile_access",
    "grant_nucleus_drug_access",
    "revoke_nucleus_drug_access",
    "grant_nucleus_indication_access",
    "revoke_nucleus_indication_access",
    "grant_nucleus_market_access",
    "revoke_nucleus_market_access",
    "invite_organization_user",
    "activate_organization_membership",
    "update_organization_member_role",
    "remove_organization_user",
    "assign_organization_seat",
    "revoke_organization_seat",
    "grant_organization_report_access",
    "revoke_organization_report_access",
    "create_workplace_resource",
    "update_workplace_resource",
    "clear_workplace_resource_fields",
    "activate_workplace_resource",
    "deactivate_workplace_resource",
    "delete_workplace_resource",
    "restore_workplace_resource",
    "bulk_update_workplace_resources",
}

EXPECTED_TOOL_NAMES = {
    "get_organization_overview",
    "get_nucleus_organization_account",
    "get_nucleus_organization_license",
    "get_nucleus_organization_approval_status",
    "get_nucleus_organization_entitlements",
    "get_organization_profile",
    "list_organization_users",
    "get_organization_seat_summary",
    "list_organization_reports",
    "check_organization_report_access",
    "get_organization_audit_log",
    "list_workplace_resource_types",
    "describe_workplace_resource",
    "search_workplace_resources",
    "get_workplace_resource",
    "count_workplace_resources",
}


class FakeAgentModelGateway:
    def __init__(self, agent_plan: AgentPlan) -> None:
        self.agent_plan = agent_plan
        self.received_user_request: str | None = None
        self.received_tool_names: tuple[str, ...] = ()
        self.received_action_names: tuple[str, ...] = ()

    async def create_plan(self, *, user_request: str, available_tools, available_actions):
        self.received_user_request = user_request
        self.received_tool_names = tuple(tool.name for tool in available_tools)
        self.received_action_names = tuple(action.name for action in available_actions)
        return self.agent_plan


class FakeOrganizationService:
    def __init__(self, *, deny_access: bool = False) -> None:
        self.deny_access = deny_access
        self.calls: list[tuple[str, str, str, str | None]] = []

    async def read_overview(self, *, user: User, organization_id: str):
        self._record_call("get_organization_overview", user, organization_id, None)
        profile = self._profile(organization_id)
        return (
            OrganizationOverview(
                organization=profile,
                organization_type="organization",
                renewal_date=date(2026, 11, 26),
                workspace_status=WorkspaceHealthStatus.HEALTHY,
                metrics=OrganizationOverviewMetrics(
                    licensed_modules=2,
                    available_areas=9,
                    organization_logins=1,
                    workspace_health_percent=98,
                ),
                version=1,
            ),
            None,
        )

    async def read_profile(self, *, user: User, organization_id: str):
        self._record_call("get_organization_profile", user, organization_id, None)
        return (self._profile(organization_id), None)

    async def list_users(self, *, user: User, organization_id: str):
        self._record_call("list_organization_users", user, organization_id, None)
        return ([], None)

    async def get_seat_summary(self, *, user: User, organization_id: str):
        self._record_call("get_organization_seat_summary", user, organization_id, None)
        return (None, None)

    async def list_reports(self, *, user: User, organization_id: str):
        self._record_call("list_organization_reports", user, organization_id, None)
        return ([], None)

    async def check_report_access(
        self,
        *,
        user: User,
        organization_id: str,
        report_id: str,
    ):
        self._record_call(
            "check_organization_report_access",
            user,
            organization_id,
            report_id,
        )
        return ({"report_id": report_id}, None)

    async def list_audit_events(self, *, user: User, organization_id: str):
        self._record_call("get_organization_audit_log", user, organization_id, None)
        return ([], None)

    @staticmethod
    def _profile(organization_id: str) -> OrganizationProfile:
        return OrganizationProfile(
            id=organization_id,
            display_name="Test Organization",
            legal_name=None,
            contact_email=None,
            environment=Environment.SANDBOX,
            status=OrganizationStatus.ACTIVE,
            version=1,
        )

    def _record_call(
        self,
        tool_name: str,
        user: User,
        organization_id: str,
        report_id: str | None,
    ) -> None:
        if self.deny_access:
            raise OrganizationAccessDeniedError()
        self.calls.append((tool_name, user.id, organization_id, report_id))


def build_user() -> User:
    return User(
        id="usr_request_001",
        display_name="Request User",
        email="request.user@example.test",
        status=UserStatus.ACTIVE,
    )


def build_orchestrator(plan: AgentPlan, service: FakeOrganizationService | None = None):
    gateway = FakeAgentModelGateway(plan)
    orchestrator = ReadOnlyAgentOrchestrator(
        model_gateway=gateway,
        tool_registry=ReadOnlyAgentToolRegistry(),
        organization_service=service or FakeOrganizationService(),
    )
    return gateway, orchestrator


async def test_agent_executes_overview_with_backend_context() -> None:
    organization_service = FakeOrganizationService()
    gateway, orchestrator = build_orchestrator(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_overview"),)),
        organization_service,
    )
    execution_result = await orchestrator.execute(
        user=build_user(),
        organization_id="org_request_001",
        user_request="Show the organization overview",
    )

    assert gateway.received_user_request == "Show the organization overview"
    assert set(gateway.received_tool_names) == EXPECTED_TOOL_NAMES
    assert set(gateway.received_action_names) == EXPECTED_ACTION_NAMES
    assert organization_service.calls == [
        ("get_organization_overview", "usr_request_001", "org_request_001", None)
    ]
    assert execution_result.results[0].data.metrics.workspace_health_percent == 98


async def test_agent_rejects_unknown_tool_before_service_execution() -> None:
    service = FakeOrganizationService()
    _, orchestrator = build_orchestrator(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="delete_organization"),)),
        service,
    )
    with pytest.raises(InvalidAgentToolCallError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="Delete the organization",
        )
    assert service.calls == []


async def test_agent_rejects_model_supplied_organization_identity() -> None:
    service = FakeOrganizationService()
    _, orchestrator = build_orchestrator(
        AgentPlan(
            tool_calls=(
                AgentToolCall(
                    tool_name="get_organization_overview",
                    arguments={"organization_id": "org_other_001"},
                ),
            )
        ),
        service,
    )
    with pytest.raises(InvalidAgentToolCallError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="Show another organization",
        )
    assert service.calls == []


async def test_agent_requires_exact_report_access_arguments() -> None:
    service = FakeOrganizationService()
    _, orchestrator = build_orchestrator(
        AgentPlan(
            tool_calls=(
                AgentToolCall(
                    tool_name="check_organization_report_access",
                    arguments={"report_id": "rpt_market_001"},
                ),
            )
        ),
        service,
    )
    await orchestrator.execute(
        user=build_user(),
        organization_id="org_request_001",
        user_request="Can I access this report?",
    )
    assert service.calls[-1][-1] == "rpt_market_001"


async def test_agent_propagates_backend_authorization_failure() -> None:
    _, orchestrator = build_orchestrator(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_overview"),)),
        FakeOrganizationService(deny_access=True),
    )
    with pytest.raises(OrganizationAccessDeniedError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="Show overview",
        )


async def test_agent_executes_multiple_validated_calls_in_order() -> None:
    service = FakeOrganizationService()
    _, orchestrator = build_orchestrator(
        AgentPlan(
            tool_calls=(
                AgentToolCall(tool_name="get_organization_overview"),
                AgentToolCall(tool_name="list_organization_reports"),
                AgentToolCall(tool_name="get_organization_audit_log"),
            )
        ),
        service,
    )
    execution_result = await orchestrator.execute(
        user=build_user(),
        organization_id="org_request_001",
        user_request="Give me an organization overview",
    )
    assert [call[0] for call in service.calls] == [
        "get_organization_overview",
        "list_organization_reports",
        "get_organization_audit_log",
    ]
    assert [result.tool_name for result in execution_result.results] == [
        "get_organization_overview",
        "list_organization_reports",
        "get_organization_audit_log",
    ]


async def test_read_executor_rejects_action_plan() -> None:
    _, orchestrator = build_orchestrator(
        AgentPlan(
            intent="action_proposal",
            action_proposal={
                "action_name": "assign_organization_seat",
                "arguments": {
                    "user_id": "usr_member_003",
                    "seat_type": "standard",
                },
            },
        )
    )
    with pytest.raises(InvalidAgentToolCallError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="Assign a seat",
        )
