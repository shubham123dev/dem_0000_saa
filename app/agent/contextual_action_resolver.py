from __future__ import annotations

import re

from app.agent.action_contracts import AgentActionProposalInput
from app.agent.action_selection import conversation_messages, latest_user_turn
from app.agent.contracts import AgentPlan
from app.domain.enums import MembershipStatus
from app.domain.models import OrganizationMember

_USER_ID = re.compile(r"\busr_[a-z0-9_]+\b", re.IGNORECASE)


def resolve_member_action_plan(
    *,
    user_request: str,
    action_name: str,
    members: list[OrganizationMember],
) -> AgentPlan | None:
    if action_name not in {
        "assign_organization_seat",
        "revoke_organization_seat",
    }:
        return None

    candidates = _member_candidates(user_request, members)
    if len(candidates) != 1:
        return AgentPlan(
            intent="clarification_required",
            clarification_question=(
                "Which organization user should this seat change apply to? "
                "Provide the exact user ID or a unique display name."
            ),
            missing_fields=("user_id",),
        )

    member = candidates[0]
    if action_name == "assign_organization_seat":
        if member.has_active_seat:
            return AgentPlan(
                intent="clarification_required",
                clarification_question=(
                    f"{member.display_name} already has an active standard seat. "
                    "Choose a different user or request another change."
                ),
                missing_fields=("eligible_user_id",),
            )
        if member.membership_status == MembershipStatus.ACTIVE:
            return AgentPlan(
                intent="action_proposal",
                action_proposal=AgentActionProposalInput(
                    action_name="assign_organization_seat",
                    arguments={
                        "user_id": member.user_id,
                        "seat_type": "standard",
                    },
                ),
            )
        return AgentPlan(
            intent="action_proposal",
            action_proposal=AgentActionProposalInput(
                action_name="onboard_organization_user",
                arguments={
                    "email": member.email,
                    "display_name": member.display_name,
                    "role": member.role,
                    "seat_type": "standard",
                },
            ),
        )

    if not member.has_active_seat:
        return AgentPlan(
            intent="clarification_required",
            clarification_question=(
                f"{member.display_name} does not have an active standard seat to revoke. "
                "Choose a different user."
            ),
            missing_fields=("eligible_user_id",),
        )
    return AgentPlan(
        intent="action_proposal",
        action_proposal=AgentActionProposalInput(
            action_name="revoke_organization_seat",
            arguments={
                "user_id": member.user_id,
                "seat_type": "standard",
            },
        ),
    )


def _member_candidates(
    user_request: str,
    members: list[OrganizationMember],
) -> list[OrganizationMember]:
    latest = latest_user_turn(user_request)
    direct_ids = {match.lower() for match in _USER_ID.findall(latest)}
    if direct_ids:
        return [member for member in members if member.user_id.lower() in direct_ids]

    messages = conversation_messages(user_request)
    searchable = [message.content for message in reversed(messages)]
    for text in searchable:
        normalized = text.casefold()
        matches = [member for member in members if _mentions_member(normalized, member)]
        if matches:
            return _deduplicate(matches)
    return []


def _mentions_member(text: str, member: OrganizationMember) -> bool:
    identifiers = (
        member.user_id.casefold(),
        member.email.casefold(),
        member.display_name.casefold(),
    )
    return any(identifier and identifier in text for identifier in identifiers)


def _deduplicate(members: list[OrganizationMember]) -> list[OrganizationMember]:
    unique: dict[str, OrganizationMember] = {}
    for member in members:
        unique[member.user_id] = member
    return list(unique.values())
