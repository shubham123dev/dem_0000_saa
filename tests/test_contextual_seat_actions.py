from __future__ import annotations

from sqlalchemy import select

from app.agent.answer_contracts import AgentQueryCompletion
from app.agent.contextual_action_resolver import resolve_member_action_plan
from app.db.orm_models import OrganizationMembershipORM, SeatAssignmentORM, UserORM
from app.domain.enums import MembershipStatus, UserStatus
from app.domain.models import OrganizationMember
from app.repositories.agent_action_repository import AgentActionRepository
from app.repositories.agent_run_repository import AgentRunRepository
from app.services.agent_run_worker import AgentRunExecutor


def _member(
    *,
    user_id: str,
    display_name: str,
    membership_status: MembershipStatus = MembershipStatus.ACTIVE,
    has_active_seat: bool = False,
) -> OrganizationMember:
    return OrganizationMember(
        user_id=user_id,
        display_name=display_name,
        email=f"{user_id}@example.test",
        user_status=UserStatus.ACTIVE,
        role="sandbox_reader",
        membership_status=membership_status,
        has_active_seat=has_active_seat,
    )


def test_contextual_resolver_requires_unique_member_name() -> None:
    plan = resolve_member_action_plan(
        user_request=(
            "Conversation context:\n\n"
            "Assistant: Alex needs a seat.\n\n"
            "User: assign an active seat pls\n\n"
            "Respond to the latest user message using the earlier messages only as context."
        ),
        action_name="assign_organization_seat",
        members=[
            _member(user_id="usr_alex_1", display_name="Alex"),
            _member(user_id="usr_alex_2", display_name="Alex"),
        ],
    )

    assert plan is not None
    assert plan.intent == "clarification_required"
    assert plan.missing_fields == ("user_id",)


def test_contextual_resolver_uses_onboarding_for_invited_member() -> None:
    plan = resolve_member_action_plan(
        user_request=(
            "Conversation context:\n\n"
            "Assistant: Demo Analyst has been invited and needs an active seat.\n\n"
            "User: assign an active seat pls\n\n"
            "Respond to the latest user message using the earlier messages only as context."
        ),
        action_name="assign_organization_seat",
        members=[
            _member(
                user_id="usr_demo",
                display_name="Demo Analyst",
                membership_status=MembershipStatus.INVITED,
            )
        ],
    )

    assert plan is not None
    assert plan.intent == "action_proposal"
    assert plan.action_proposal is not None
    assert plan.action_proposal.action_name == "onboard_organization_user"
    assert plan.action_proposal.arguments["seat_type"] == "standard"


async def test_three_turn_demo_analyst_flow_creates_proposal_without_mutation(
    sessionmaker_,
    seeded,
    monkeypatch,
) -> None:
    user_id = "usr_invited_e32175a743ac6dcbdc35"
    async with sessionmaker_() as session:
        session.add(
            UserORM(
                id=user_id,
                display_name="Demo Analyst",
                email="demo.analyst@example.test",
                status=UserStatus.ACTIVE.value,
            )
        )
        session.add(
            OrganizationMembershipORM(
                organization_id="org_sandbox_001",
                user_id=user_id,
                role="sandbox_reader",
                membership_status=MembershipStatus.INVITED.value,
                version=1,
            )
        )
        await session.commit()

        repository = AgentRunRepository(session)
        first = await repository.create_run(
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            query="tell me about all user in this",
            client_request_id="context-seat-1",
            conversation_id=None,
            request_id=None,
        )
        await repository.claim_next(worker_id="test-worker")
        await repository.complete_run(
            run_id=first.run.id,
            completion=AgentQueryCompletion(
                mode="read",
                answer="Demo Analyst is an invited organization user.",
                answer_source="deterministic",
            ),
        )
        second = await repository.create_run(
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            query="for demo analyst what is pending from my side",
            client_request_id="context-seat-2",
            conversation_id=first.conversation.id,
            request_id=None,
        )
        await repository.claim_next(worker_id="test-worker")
        await repository.complete_run(
            run_id=second.run.id,
            completion=AgentQueryCompletion(
                mode="read",
                answer="Demo Analyst has been invited and needs activation and a standard seat.",
                answer_source="deterministic",
            ),
        )
        third = await repository.create_run(
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            query="assign an active seat pls",
            client_request_id="context-seat-3",
            conversation_id=first.conversation.id,
            request_id=None,
        )
        await repository.claim_next(worker_id="context-seat-worker")

    class ModelMustNotRun:
        async def create_plan(self, **_kwargs):
            raise AssertionError("Contextual seat resolution must not call the model")

        async def create_answer(self, **_kwargs):
            raise AssertionError("Contextual seat resolution must not synthesize an answer")

    monkeypatch.setattr(
        "app.agent.run_runtime.get_agent_model_gateway",
        lambda: ModelMustNotRun(),
    )
    monkeypatch.setattr(
        "app.agent.run_runtime.get_agent_answer_gateway",
        lambda: ModelMustNotRun(),
    )

    await AgentRunExecutor(sessionmaker_).execute(
        third.run.id,
        "context-seat-worker",
    )

    async with sessionmaker_() as session:
        proposal = await AgentActionRepository(
            session
        ).get_proposal_by_source_agent_run_id(third.run.id)
        assert proposal is not None
        assert proposal.action_name == "onboard_organization_user"
        assert proposal.arguments == {
            "email": "demo.analyst@example.test",
            "display_name": "Demo Analyst",
            "role": "sandbox_reader",
            "seat_type": "standard",
        }
        assignment = await session.scalar(
            select(SeatAssignmentORM).where(
                SeatAssignmentORM.organization_id == "org_sandbox_001",
                SeatAssignmentORM.user_id == user_id,
                SeatAssignmentORM.status == "active",
            )
        )
        assert assignment is None
