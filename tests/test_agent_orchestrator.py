from __future__ import annotations

import pytest

from app.agent.contracts import AgentPlan, AgentToolCall
from app.agent.orchestrator import ReadOnlyAgentOrchestrator
from app.agent.tool_registry import InvalidAgentToolCallError, ReadOnlyAgentToolRegistry
from app.core.errors import OrganizationAccessDeniedError
from app.domain.enums import OrganizationStatus, UserStatus
from app.domain.models import OrganizationProfile, User

EXPECTED_ACTION_NAMES = {
    "update_organization_contact_email",
    "invite_organization_user",
    "assign_organization_seat",
    "grant_organization_report_access",
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

    async def read_profile(self, *, user: User, organization_id: str):
        self._record_call("get_organization_profile", user, organization_id, None)
        return (
            OrganizationProfile(
                id=organization_id,
                display_name="Test Organization",
                legal_name=None,
                contact_email=None,
                environment="sandbox",
                status=OrganizationStatus.ACTIVE,
                version=1,
            ),
            None,
        )

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


async def test_agent_executes_allowlisted_tool_with_backend_context() -> None:
    organization_service = FakeOrganizationService()
    gateway, orchestrator = build_orchestrator(
        AgentPlan(tool_calls=(AgentToolCall(tool_name="get_organization_profile"),)),
        organization_service,
    )
    execution_result = await orchestrator.execute(
        user=build_user(),
        organization_id="org_request_001",
        user_request="Show the organization profile",
    )

    assert gateway.received_user_request == "Show the organization profile"
    assert "get_organization_profile" in gateway.received_tool_names
    assert set(gateway.received_action_names) == EXPECTED_ACTION_NAMES
    assert organization_service.calls == [
        ("get_organization_profile", "usr_request_001", "org_request_001", None)
    ]
    assert execution_result.results[0].data.id == "org_request_001"


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
                    tool_name="get_organization_profile",
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
        AgentPlan(tool_calls=(AgentToolCall(tool_name="list_organization_users"),)),
        FakeOrganizationService(deny_access=True),
    )
    with pytest.raises(OrganizationAccessDeniedError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="List users",
        )


async def test_agent_executes_multiple_validated_calls_in_order() -> None:
    service = FakeOrganizationService()
    _, orchestrator = build_orchestrator(
        AgentPlan(
            tool_calls=(
                AgentToolCall(tool_name="get_organization_profile"),
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
        "get_organization_profile",
        "list_organization_reports",
        "get_organization_audit_log",
    ]
    assert [result.tool_name for result in execution_result.results] == [
        "get_organization_profile",
        "list_organization_reports",
        "get_organization_audit_log",
    ]


async def test_read_executor_rejects_action_plan() -> None:
    _, orchestrator = build_orchestrator(
        AgentPlan(
            intent="action_proposal",
            action_proposal={
                "action_name": "assign_organization_seat",
                "arguments": {"user_id": "usr_member_003", "seat_type": "standard"},
            },
        )
    )
    with pytest.raises(InvalidAgentToolCallError):
        await orchestrator.execute(
            user=build_user(),
            organization_id="org_request_001",
            user_request="Assign a seat",
        )
