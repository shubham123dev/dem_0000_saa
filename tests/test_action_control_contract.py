from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.action_models import AgentActionProposalORM
from app.db.agent_run_models import AgentConversationORM, AgentMessageORM, AgentRunORM


async def test_message_action_control_resolves_exact_proposal_with_utc_timestamps(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_headers: dict[str, str],
) -> None:
    conversation_id = uuid.uuid4().hex
    run_id = uuid.uuid4().hex
    proposal_id = uuid.uuid4().hex
    message_id = uuid.uuid4().hex
    # SQLite intentionally receives a naive UTC value so this test exercises the
    # API's timezone normalization without becoming dependent on the wall clock.
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    db_session.add(
        AgentConversationORM(
            id=conversation_id,
            organization_id="org_sandbox_001",
            created_by_user_id="usr_admin_001",
            status="active",
            next_message_sequence=2,
            version=1,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        AgentRunORM(
            id=run_id,
            conversation_id=conversation_id,
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            user_message_id="message-contract-user",
            client_request_id=f"contract-{uuid.uuid4().hex}",
            active_slot=None,
            status="proposal_ready",
            current_stage="completion",
            final_mode="action_proposal",
            final_message_id=message_id,
            proposal_id=proposal_id,
            attempt_count=1,
            next_event_sequence=2,
            version=1,
            created_at=now,
            started_at=now,
            completed_at=now,
        )
    )
    await db_session.flush()
    db_session.add(
        AgentMessageORM(
            id=message_id,
            conversation_id=conversation_id,
            run_id=run_id,
            sequence=1,
            role="assistant",
            content="Proposal ready",
            mode="action_proposal",
            answer_source="deterministic",
            safe_metadata_json={
                "action_proposal": {"action_name": "invite_organization_user"}
            },
            created_at=now,
        )
    )
    db_session.add(
        AgentActionProposalORM(
            id=proposal_id,
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            source_agent_run_id=run_id,
            action_name="invite_organization_user",
            arguments_json={
                "email": "contract@example.test",
                "display_name": "Contract User",
                "role": "sandbox_reader",
            },
            changes_json=[
                {
                    "field": "organization_membership",
                    "before": None,
                    "after": "invited sandbox_reader",
                }
            ],
            action_fingerprint=f"contract-{proposal_id}",
            risk_level="medium",
            resource_type="organization_membership",
            resource_id="contract@example.test",
            status="pending_approval",
            observed_resource_version=0,
            resource_preconditions_json=[],
            fingerprint_version=4,
            approval_policy_json={
                "self_approval_allowed": True,
                "required_approver_permission": "agent.actions.approve",
                "minimum_approvals": 1,
            },
            expires_at=now + timedelta(minutes=15),
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/workplace/organizations/org_sandbox_001/agent/control/messages/{message_id}/action",
        headers=admin_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == proposal_id
    assert payload["source_conversation_id"] == conversation_id
    assert payload["allowed_operations"]["approve"] is True
    assert payload["allowed_operations"]["reject"] is True
    assert payload["created_at"].endswith(("Z", "+00:00"))
    assert payload["expires_at"].endswith(("Z", "+00:00"))

    listed = await client.get(
        "/workplace/organizations/org_sandbox_001/agent/control/actions?status=pending_approval",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    match = next(
        item for item in listed.json()["proposals"] if item["id"] == proposal_id
    )
    assert match["created_at"].endswith(("Z", "+00:00"))
    assert match["expires_at"].endswith(("Z", "+00:00"))
