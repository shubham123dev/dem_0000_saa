from __future__ import annotations

from fastapi import status

from app.core.errors import AppError


class AgentModelUnavailableError(AppError):
    code = "agent_model_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "Agent model is not configured."


class AgentToolCallInvalidError(AppError):
    code = "agent_tool_call_invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Agent proposed an invalid tool call."
