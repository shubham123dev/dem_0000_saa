"""Tests for the conversation store API: listing, history, search, rename, archive."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.agent_run_models import AgentConversationORM, AgentMessageORM

ORG = "org_sandbox_001"
USER = "usr_admin_001"
BASE = f"/workplace/organizations/{ORG}/agent/conversations"


async def _create_conversation(
    db_session: AsyncSession,
    *,
    title: str | None = None,
    message_count: int = 2,
    pinned: bool = False,
) -> str:
    """Helper to insert a conversation with messages directly."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    conv_id = uuid.uuid4().hex
    conv = AgentConversationORM(
        id=conv_id,
        organization_id=ORG,
        created_by_user_id=USER,
        status="active",
        title=title,
        message_count=message_count,
        pinned=pinned,
        last_message_at=now,
        next_message_sequence=message_count + 1,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db_session.add(conv)
    await db_session.flush()

    parent_id = None
    for i in range(1, message_count + 1):
        msg_id = uuid.uuid4().hex
        role = "user" if i % 2 == 1 else "assistant"
        msg = AgentMessageORM(
            id=msg_id,
            conversation_id=conv_id,
            run_id=None,
            parent_id=parent_id,
            sequence=i,
            role=role,
            content=f"Message {i} content for testing" if role == "user" else f"Response {i}",
            mode=None,
            answer_source=None,
            safe_metadata_json=None,
            created_at=now,
        )
        db_session.add(msg)
        parent_id = msg_id

    await db_session.commit()
    return conv_id


@pytest.mark.asyncio
async def test_list_conversations_empty(client, admin_headers):
    response = await client.get(BASE, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["conversations"] == []
    assert data["total"] == 0
    assert data["has_more"] is False


@pytest.mark.asyncio
async def test_list_conversations_returns_items(client, seeded, admin_headers, db_session):
    await _create_conversation(db_session, title="First conversation")
    await _create_conversation(db_session, title="Second conversation")

    response = await client.get(BASE, headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["conversations"]) == 2
    # Most recent first
    assert data["conversations"][0]["title"] == "Second conversation"
    assert data["conversations"][1]["title"] == "First conversation"


@pytest.mark.asyncio
async def test_list_conversations_pagination(client, seeded, admin_headers, db_session):
    for i in range(5):
        await _create_conversation(db_session, title=f"Convo {i}")

    response = await client.get(BASE, headers=admin_headers, params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 2
    assert data["total"] == 5
    assert data["has_more"] is True

    response2 = await client.get(BASE, headers=admin_headers, params={"limit": 2, "offset": 4})
    data2 = response2.json()
    assert len(data2["conversations"]) == 1
    assert data2["has_more"] is False


@pytest.mark.asyncio
async def test_list_conversations_pinned_first(client, seeded, admin_headers, db_session):
    await _create_conversation(db_session, title="Normal")
    await _create_conversation(db_session, title="Pinned", pinned=True)

    response = await client.get(BASE, headers=admin_headers)
    data = response.json()
    assert data["conversations"][0]["title"] == "Pinned"
    assert data["conversations"][0]["pinned"] is True


@pytest.mark.asyncio
async def test_list_conversations_search(client, seeded, admin_headers, db_session):
    await _create_conversation(db_session, title="Deploy the application")
    await _create_conversation(db_session, title="Fix the login bug")

    response = await client.get(BASE, headers=admin_headers, params={"search": "deploy"})
    data = response.json()
    assert data["total"] == 1
    assert data["conversations"][0]["title"] == "Deploy the application"


@pytest.mark.asyncio
async def test_get_conversation_history(client, seeded, admin_headers, db_session):
    conv_id = await _create_conversation(db_session, title="History test", message_count=4)

    response = await client.get(f"{BASE}/{conv_id}/messages", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conv_id
    assert data["title"] == "History test"
    assert len(data["messages"]) == 4
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"
    assert data["messages"][0]["sequence"] == 1


@pytest.mark.asyncio
async def test_get_conversation_history_not_found(client, seeded, admin_headers):
    response = await client.get(f"{BASE}/nonexistent/messages", headers=admin_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rename_conversation(client, seeded, admin_headers, db_session):
    conv_id = await _create_conversation(db_session, title="Old title")

    response = await client.patch(
        f"{BASE}/{conv_id}",
        headers=admin_headers,
        json={"title": "New title"},
    )
    assert response.status_code == 200

    # Verify via list
    list_response = await client.get(BASE, headers=admin_headers)
    data = list_response.json()
    assert data["conversations"][0]["title"] == "New title"


@pytest.mark.asyncio
async def test_pin_conversation(client, seeded, admin_headers, db_session):
    conv_id = await _create_conversation(db_session, title="Pin me")

    response = await client.patch(
        f"{BASE}/{conv_id}",
        headers=admin_headers,
        json={"pinned": True},
    )
    assert response.status_code == 200

    list_response = await client.get(BASE, headers=admin_headers)
    data = list_response.json()
    assert data["conversations"][0]["pinned"] is True


@pytest.mark.asyncio
async def test_delete_conversation_archives(client, seeded, admin_headers, db_session):
    conv_id = await _create_conversation(db_session, title="Delete me")

    response = await client.delete(f"{BASE}/{conv_id}", headers=admin_headers)
    assert response.status_code == 204

    # Should no longer appear in list
    list_response = await client.get(BASE, headers=admin_headers)
    data = list_response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_search_messages(client, seeded, admin_headers, db_session):
    await _create_conversation(db_session, title="Searchable", message_count=2)

    response = await client.get(
        f"{BASE}/search",
        headers=admin_headers,
        params={"q": "Message 1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert "Message 1" in data["results"][0]["snippet"]


@pytest.mark.asyncio
async def test_conversation_isolation_between_users(
    client, seeded, admin_headers, reader_headers, db_session
):
    await _create_conversation(db_session, title="Admin only")

    # Reader should see nothing (conversations belong to admin)
    response = await client.get(BASE, headers=reader_headers)
    data = response.json()
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_branching_history(client, seeded, admin_headers, db_session):
    """Test tree-structured branching via leaf_id parameter."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    conv_id = uuid.uuid4().hex
    conv = AgentConversationORM(
        id=conv_id,
        organization_id=ORG,
        created_by_user_id=USER,
        status="active",
        title="Branch test",
        message_count=3,
        pinned=False,
        last_message_at=now,
        next_message_sequence=4,
        version=1,
        created_at=now,
        updated_at=now,
    )
    db_session.add(conv)
    await db_session.flush()

    # Create a branch: msg1 -> msg2a and msg1 -> msg2b
    msg1_id = uuid.uuid4().hex
    msg2a_id = uuid.uuid4().hex
    msg2b_id = uuid.uuid4().hex

    db_session.add(AgentMessageORM(
        id=msg1_id, conversation_id=conv_id, run_id=None, parent_id=None,
        sequence=1, role="user", content="Original question",
        mode=None, answer_source=None, safe_metadata_json=None, created_at=now,
    ))
    db_session.add(AgentMessageORM(
        id=msg2a_id, conversation_id=conv_id, run_id=None, parent_id=msg1_id,
        sequence=2, role="assistant", content="Response A",
        mode=None, answer_source=None, safe_metadata_json=None, created_at=now,
    ))
    db_session.add(AgentMessageORM(
        id=msg2b_id, conversation_id=conv_id, run_id=None, parent_id=msg1_id,
        sequence=3, role="assistant", content="Response B (regenerated)",
        mode=None, answer_source=None, safe_metadata_json=None, created_at=now,
    ))
    await db_session.commit()

    # Walk branch B
    response = await client.get(
        f"{BASE}/{conv_id}/messages",
        headers=admin_headers,
        params={"leaf_id": msg2b_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_branches"] is True
    assert len(data["messages"]) == 2
    assert data["messages"][0]["content"] == "Original question"
    assert data["messages"][1]["content"] == "Response B (regenerated)"
