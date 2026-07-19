from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from app.db.action_models import AgentActionProposalORM
from app.repositories.action_control_repository import ActionControlRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def test_action_execution_events_are_deduplicated_and_replayable(db_session, seeded):
    proposal_id = uuid.uuid4().hex
    db_session.add(
        AgentActionProposalORM(
            id=proposal_id,
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            source_agent_run_id=None,
            action_name="update_organization_contact_email",
            arguments_json={"contact_email": "control@example.test"},
            changes_json=[{"field": "contact_email", "before": None, "after": "control@example.test"}],
            action_fingerprint="phase6-control-test",
            risk_level="low",
            resource_type="organization",
            resource_id="org_sandbox_001",
            status="pending_approval",
            observed_resource_version=1,
            resource_preconditions_json=[{"resource_type": "organization", "resource_id": "org_sandbox_001", "observed_version": 1}],
            fingerprint_version=4,
            approval_policy_json={"self_approval_allowed": True, "required_approver_permission": "organization.profile.update", "minimum_approvals": 1},
            expires_at=_utcnow() + timedelta(minutes=15),
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
    )
    await db_session.commit()
    repository = ActionControlRepository(db_session)
    first = await repository.append_event(
        proposal_id=proposal_id,
        event_type="execution.accepted",
        stage="acceptance",
        message="Execution request accepted",
        payload=None,
        terminal=False,
        dedupe_key="request-1-accepted",
    )
    duplicate = await repository.append_event(
        proposal_id=proposal_id,
        event_type="execution.accepted",
        stage="acceptance",
        message="Execution request accepted",
        payload=None,
        terminal=False,
        dedupe_key="request-1-accepted",
    )
    second = await repository.append_event(
        proposal_id=proposal_id,
        event_type="execution.succeeded",
        stage="completion",
        message="Execution completed and verified",
        payload={"outcome": "succeeded"},
        terminal=True,
        dedupe_key="request-1-succeeded",
    )
    assert duplicate.id == first.id
    assert second.sequence == first.sequence + 1
    replay = await repository.list_events(proposal_id=proposal_id, after_sequence=first.sequence)
    assert [event.event_type for event in replay] == ["execution.succeeded"]
