from fastapi import status

from app.core.errors import AppError


class AgentActionInvalidError(AppError):
    code = "agent_action_invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    message = "Agent action proposal is invalid."


class AgentActionProposalNotFoundError(AppError):
    code = "agent_action_proposal_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Agent action proposal was not found."


class AgentActionStateConflictError(AppError):
    code = "agent_action_state_conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action is not in a valid state for this operation."


class AgentActionExpiredError(AppError):
    code = "agent_action_expired"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action approval has expired."
