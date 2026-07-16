"""Mock chatbot gateway (defined but unwired in Step 0).

``MockChatbotGateway`` satisfies the ``ChatbotGateway`` contract with a
deterministic, side-effect-free stub. It does NOT call any real model and is
NOT registered as a Step 0 tool. It exists to prove the contract and to be the
seam a future ``SaraChatbotApiGateway`` replaces.

It never decides access: it only echoes the backend-authorized report ids it
was given.
"""

from __future__ import annotations


class MockChatbotGateway:
    """Deterministic stand-in for a report-aware chatbot backend."""

    async def query_report(
        self,
        *,
        organization_id: str,
        user_id: str,
        report_ids: list[str],
        query: str,
    ) -> dict:
        """Return a canned answer scoped strictly to the authorized reports."""

        return {
            "organization_id": organization_id,
            "user_id": user_id,
            "report_ids": list(report_ids),
            "query": query,
            "answer": (
                "This is a mock chatbot response. It is restricted to the "
                f"{len(report_ids)} report(s) authorized by the backend."
            ),
            "source": "mock",
        }
