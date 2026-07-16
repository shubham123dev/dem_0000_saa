"""Chatbot adapter contract.

Defines the stable gateway the Workplace Agent will use for chatbot-backed
tools. Callers depend on this Protocol, never on a concrete chatbot client, so
the mock can later be swapped for ``SaraChatbotApiGateway`` without changes.

Contract invariant: ``report_ids`` are the backend-computed set of reports the
organization/user is allowed to use. The gateway must treat them as the only
permitted scope; it must never widen access.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatbotGateway(Protocol):
    """Replaceable gateway to a report-aware chatbot backend."""

    async def query_report(
        self,
        *,
        organization_id: str,
        user_id: str,
        report_ids: list[str],
        query: str,
    ) -> dict:
        """Answer ``query`` using only the supplied (already-authorized) reports.

        Args:
            organization_id: the tenant the request is scoped to.
            user_id: the resolved, authenticated user.
            report_ids: backend-authorized report ids; the only permitted scope.
            query: the natural-language question.

        Returns:
            A structured answer payload (implementation-defined).
        """
        ...
