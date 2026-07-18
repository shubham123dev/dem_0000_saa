from __future__ import annotations

import asyncio

from app.agent.answer_contracts import AgentQueryCompletion
from app.repositories.agent_run_repository import AgentRunRepository
from app.services.agent_run_activity import DatabaseAgentRunActivitySink


async def test_run_submission_is_idempotent(db_session, seeded):
    repository = AgentRunRepository(db_session)
    first = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-0001",
        conversation_id=None,
        request_id="request-1",
    )
    second = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-0001",
        conversation_id=None,
        request_id="request-2",
    )
    assert first.created is True
    assert second.created is False
    assert second.run.id == first.run.id
    assert second.conversation.id == first.conversation.id


async def test_conversation_rejects_a_second_active_run(db_session, seeded):
    from app.repositories.agent_run_repository import (
        AgentConversationBusyRepositoryError,
    )

    repository = AgentRunRepository(db_session)
    first = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="First request",
        client_request_id="client-request-busy-0001",
        conversation_id=None,
        request_id=None,
    )
    try:
        await repository.create_run(
            organization_id="org_sandbox_001",
            requested_by_user_id="usr_admin_001",
            query="Second request",
            client_request_id="client-request-busy-0002",
            conversation_id=first.conversation.id,
            request_id=None,
        )
    except AgentConversationBusyRepositoryError:
        pass
    else:
        raise AssertionError("A conversation accepted two active runs")


async def test_events_replay_after_sequence(db_session, seeded):
    repository = AgentRunRepository(db_session)
    created = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-0002",
        conversation_id=None,
        request_id=None,
    )
    sink = DatabaseAgentRunActivitySink(repository, created.run.id)
    await sink.emit(stage="access_check", message="Checking your access")
    await sink.emit(stage="request_planning", message="Understanding your request")
    replay = await repository.list_events(
        run_id=created.run.id, after_sequence=1
    )
    assert [event.sequence for event in replay] == [2, 3]
    assert [event.safe_message for event in replay] == [
        "Checking your access",
        "Understanding your request",
    ]


async def test_terminal_completion_persists_safe_message(db_session, seeded):
    repository = AgentRunRepository(db_session)
    created = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-0003",
        conversation_id=None,
        request_id=None,
    )
    claimed = await repository.claim_next(worker_id="test-worker")
    assert claimed is not None
    message = await repository.complete_run(
        run_id=created.run.id,
        completion=AgentQueryCompletion(
            mode="read",
            answer="There are active users.",
            answer_source="deterministic",
        ),
    )
    assert message.content == "There are active users."
    events = await repository.list_events(
        run_id=created.run.id, after_sequence=0
    )
    assert events[-1].event_type == "answer.completed"
    assert events[-1].terminal is True
    assert "message" in (events[-1].safe_payload or {})


async def test_cancellation_is_cooperative_and_idempotent(db_session, seeded):
    repository = AgentRunRepository(db_session)
    created = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-0004",
        conversation_id=None,
        request_id=None,
    )
    first = await repository.request_cancellation(created.run.id)
    second = await repository.request_cancellation(created.run.id)
    assert first.cancellation_requested_at is not None
    assert second.cancellation_requested_at is not None
    assert await repository.is_cancellation_requested(created.run.id)


async def test_agent_run_api_creates_and_recovers_conversation(client, admin_headers):
    response = await client.post(
        "/workplace/organizations/org_sandbox_001/agent/runs",
        headers=admin_headers,
        json={
            "query": "List active users",
            "client_request_id": "client-request-api-0001",
            "conversation_id": None,
        },
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["created"] is True
    conversation = await client.get(
        "/workplace/organizations/org_sandbox_001/agent/conversations/"
        + payload["conversation_id"],
        headers=admin_headers,
    )
    assert conversation.status_code == 200
    assert conversation.json()["messages"][0]["content"] == "List active users"


async def test_sse_replays_persisted_event(client, admin_headers, db_session):
    repository = AgentRunRepository(db_session)
    created = await repository.create_run(
        organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001",
        query="List active users",
        client_request_id="client-request-sse-0001",
        conversation_id=None,
        request_id=None,
    )
    await repository.fail_run(created.run.id, "agent_run_failed")
    response = await client.get(
        f"/workplace/organizations/org_sandbox_001/agent/runs/{created.run.id}/events",
        headers={**admin_headers, "Last-Event-ID": "1"},
    )
    assert response.status_code == 200
    assert "event: run.failed" in response.text
    assert "id: 2" in response.text

async def test_action_proposal_source_run_is_idempotent(db_session, seeded):
    import uuid
    from datetime import datetime, timedelta, timezone

    from app.agent.action_contracts import (
        AgentActionChange,
        AgentApprovalPolicy,
    )
    from app.db.agent_run_models import (
        AgentConversationORM,
        AgentMessageORM,
        AgentRunORM,
    )
    from app.repositories.agent_action_repository import AgentActionRepository

    now = datetime.now(timezone.utc)
    conv_id = uuid.uuid4().hex
    run_id = uuid.uuid4().hex
    msg_id = uuid.uuid4().hex
    db_session.add(AgentConversationORM(
        id=conv_id, organization_id="org_sandbox_001",
        created_by_user_id="usr_admin_001", status="active",
        next_message_sequence=2, version=1, created_at=now, updated_at=now,
    ))
    db_session.add(AgentRunORM(
        id=run_id, conversation_id=conv_id, organization_id="org_sandbox_001",
        requested_by_user_id="usr_admin_001", user_message_id=msg_id,
        client_request_id="proposal-src-test", request_id=None, active_slot=1,
        status="completed", current_stage="answer_delivery", attempt_count=1,
        next_event_sequence=2, version=1, created_at=now,
        started_at=now, completed_at=now,
    ))
    await db_session.flush()
    db_session.add(AgentMessageORM(
        id=msg_id, conversation_id=conv_id, run_id=run_id, sequence=1,
        role="user", content="test", mode=None, answer_source=None,
        safe_metadata_json=None, created_at=now,
    ))
    await db_session.commit()

    repository = AgentActionRepository(db_session)
    kwargs = {
        "organization_id": "org_sandbox_001",
        "requested_by_user_id": "usr_admin_001",
        "action_name": "update_organization_contact_email",
        "arguments": {"contact_email": "idempotent@example.test"},
        "changes": (
            AgentActionChange(
                field="contact_email",
                before="old@example.test",
                after="idempotent@example.test",
            ),
        ),
        "action_fingerprint": "phase5-idempotent-fingerprint",
        "risk_level": "low",
        "resource_type": "organization",
        "resource_id": "org_sandbox_001",
        "observed_resource_version": 1,
        "resource_preconditions": (),
        "fingerprint_version": 4,
        "approval_policy": AgentApprovalPolicy(
            self_approval_allowed=True,
            required_approver_permission="organization.profile.update",
            minimum_approvals=1,
        ),
        "expires_at": _utcnow() + timedelta(minutes=15),
        "source_agent_run_id": run_id,
    }
    first = await repository.create_proposal(**kwargs)
    second = await repository.create_proposal(**kwargs)
    assert second.id == first.id


def _utcnow():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
