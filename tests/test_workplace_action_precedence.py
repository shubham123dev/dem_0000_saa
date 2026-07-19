from __future__ import annotations

from app.agent.action_registry import AgentActionRegistry
from app.agent.contracts import AgentToolDefinition
from app.agent.providers.workplace_openai_responses import OpenAIResponsesAgentModelGateway


def _gateway() -> OpenAIResponsesAgentModelGateway:
    return OpenAIResponsesAgentModelGateway(
        api_key="test-key",
        model="test-model",
        endpoint="https://provider.test/v1/responses",
        timeout_seconds=1,
        maximum_attempts=1,
        retry_delay_seconds=0,
        maximum_output_tokens=500,
    )


def _tools() -> tuple[AgentToolDefinition, ...]:
    return (
        AgentToolDefinition(
            name="list_organization_users",
            description="List organization users.",
        ),
        AgentToolDefinition(
            name="get_organization_profile",
            description="Read the organization profile.",
        ),
    )


def _function_names(payload: dict) -> set[str]:
    return {item["name"] for item in payload["tools"]}


def test_exact_invitation_command_exposes_only_invite_action_and_clarification() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request=(
            "Invite a user named Demo Analyst with email "
            "demo.analyst.20260719@example.test as sandbox_reader."
        ),
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    names = _function_names(payload)
    assert names == {
        "action__invite_organization_user",
        "clarify__request",
    }
    assert "explicit change command" in payload["input"][0]["content"][0]["text"]


def test_polite_invitation_command_keeps_action_precedence() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request=(
            "Could you please invite a user named Demo Analyst with email "
            "demo.analyst.20260719@example.test as sandbox_reader?"
        ),
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    assert _function_names(payload) == {
        "action__invite_organization_user",
        "clarify__request",
    }


def test_capability_question_is_not_forced_into_an_action() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request="Can a user be invited as a sandbox reader?",
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    names = _function_names(payload)
    assert "read__list_organization_users" in names
    assert "action__invite_organization_user" in names
    assert "clarify__request" in names


def test_onboarding_command_prefers_onboarding_not_invitation() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request=(
            "Onboard Demo Analyst with email demo.analyst@example.test as "
            "sandbox_reader with a standard seat."
        ),
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    assert _function_names(payload) == {
        "action__onboard_organization_user",
        "clarify__request",
    }


def test_conversation_follow_up_scopes_from_latest_user_turn() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request=(
            "Conversation context:\n\n"
            "User: Show the exact user ID for Demo Analyst.\n\n"
            "Assistant: The exact user ID for Demo Analyst is "
            "usr_invited_e32175a743ac6dcbdc35.\n\n"
            "User: Assign a standard seat to user "
            "usr_invited_e32175a743ac6dcbdc35.\n\n"
            "Respond to the latest user message using the earlier messages only as context."
        ),
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    assert _function_names(payload) == {
        "action__assign_organization_seat",
        "clarify__request",
    }
    assert payload["parallel_tool_calls"] is False


def test_short_seat_follow_up_never_falls_back_to_read_tools() -> None:
    payload = _gateway()._build_plan_request_payload(
        user_request=(
            "Conversation context:\n\n"
            "User: What is pending for Demo Analyst?\n\n"
            "Assistant: Demo Analyst needs an active seat.\n\n"
            "User: assign an active seat pls\n\n"
            "Respond to the latest user message using the earlier messages only as context."
        ),
        available_tools=_tools(),
        available_actions=AgentActionRegistry().list_model_definitions(),
    )

    names = _function_names(payload)
    assert "action__assign_organization_seat" in names
    assert "clarify__request" in names
    assert not any(name.startswith("read__") for name in names)
    assert payload["parallel_tool_calls"] is False
