from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from app.agent.action_contracts import AgentActionDefinition

_CONTEXT_PREFIX = "Conversation context:"
_CONTEXT_TRAILER = "Respond to the latest user message"
_MESSAGE_PATTERN = re.compile(r"(?:^|\n\n)(User|Assistant): ")
_WORDS = re.compile(r"[a-z0-9]+")
_PREFIX_WORDS = {
    "please",
    "kindly",
    "can",
    "could",
    "would",
    "will",
    "you",
    "i",
    "want",
    "need",
    "to",
    "just",
    "me",
}
_GENERIC_ACTION_WORDS = {
    "organization",
    "workplace",
    "nucleus",
    "resource",
    "resources",
    "account",
}


@dataclass(frozen=True)
class ConversationMessage:
    role: Literal["user", "assistant"]
    content: str


def conversation_messages(value: str) -> tuple[ConversationMessage, ...]:
    text = value.strip()
    if not text.startswith(_CONTEXT_PREFIX):
        return (ConversationMessage(role="user", content=text),) if text else ()

    body = text[len(_CONTEXT_PREFIX) :].strip()
    trailer_index = body.rfind(f"\n\n{_CONTEXT_TRAILER}")
    if trailer_index >= 0:
        body = body[:trailer_index].rstrip()

    matches = list(_MESSAGE_PATTERN.finditer(body))
    messages: list[ConversationMessage] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        if not content:
            continue
        role = "user" if match.group(1) == "User" else "assistant"
        messages.append(ConversationMessage(role=role, content=content))
    return tuple(messages)


def latest_user_turn(value: str) -> str:
    for message in reversed(conversation_messages(value)):
        if message.role == "user":
            return message.content
    return value.strip()


def scope_actions(
    request: str,
    actions: tuple[AgentActionDefinition, ...],
) -> tuple[AgentActionDefinition, ...]:
    tokens = list(_words(latest_user_turn(request)))
    while tokens and tokens[0] in _PREFIX_WORDS:
        tokens.pop(0)
    if not tokens:
        return ()

    verb = _stem(tokens[0])
    candidates = [
        action
        for action in actions
        if _words(action.name) and _stem(_words(action.name)[0]) == verb
    ]
    if not candidates:
        return ()

    request_words = set(tokens[1:])
    scored: list[tuple[int, AgentActionDefinition]] = []
    for action in candidates:
        cues = {
            word
            for word in _words(action.name)[1:]
            if word not in _GENERIC_ACTION_WORDS
        }
        scored.append((len(cues & request_words), action))
    best_score = max(score for score, _ in scored)
    return tuple(action for score, action in scored if score == best_score)


def _words(value: str) -> tuple[str, ...]:
    return tuple(_WORDS.findall(value.lower()))


def _stem(value: str) -> str:
    normalized = value.lower()
    for suffix in ("ing", "ed"):
        if normalized.endswith(suffix) and len(normalized) > len(suffix) + 2:
            normalized = normalized[: -len(suffix)]
            break
    return (
        normalized[:-1]
        if normalized.endswith("e") and len(normalized) > 3
        else normalized
    )
