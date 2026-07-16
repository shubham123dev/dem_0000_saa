"""Chatbot adapter package.

Defines the ``ChatbotGateway`` contract and ships a ``MockChatbotGateway`` for
future chatbot-backed workplace tools (e.g. "answer this market question using
only reports licensed to this organization").

IMPORTANT: This package is intentionally **defined but not wired** in Step 0.
Step 0 is read-only and exposes no chatbot tools. The contract exists so that a
future ``SaraChatbotApiGateway`` can replace ``MockChatbotGateway`` without
changing the Workplace Agent core.

The invariant, enforced by the agent layer (never by the model/prompt): the
backend computes the allowed report ids first, then calls the chatbot gateway
with exactly those ids. The chatbot can never choose unauthorized reports.
"""
