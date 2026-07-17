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


class AgentActionStaleError(AppError):
    code = "agent_action_stale"
    status_code = status.HTTP_409_CONFLICT
    message = "The resource changed after this action was proposed. Create a new proposal."


class AgentActionCancelledError(AppError):
    code = "agent_action_cancelled"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action was cancelled."


class AgentActionAlreadyDecidedError(AppError):
    code = "agent_action_already_decided"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action already has an approval decision."


class AgentActionExecutionInProgressError(AppError):
    code = "agent_action_execution_in_progress"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action execution is already in progress."


class AgentActionReconciliationRequiredError(AppError):
    code = "agent_action_reconciliation_required"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action execution requires reconciliation."


class AgentActionIdempotencyConflictError(AppError):
    code = "agent_action_idempotency_conflict"
    status_code = status.HTTP_409_CONFLICT
    message = "Agent action was already executed with another idempotency key."
