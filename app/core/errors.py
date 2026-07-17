"""Consistent error contract and exception handling.

Every error response has the shape::

    {
      "error": {
        "code": "permission_denied",
        "message": "...",
        "request_id": "<generated request id>"
      }
    }

Responses never leak stack traces, database paths, SQL, or secrets.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

REQUEST_ID_HEADER = "X-Request-Id"

ERROR_CODES = frozenset(
    {
        "unauthenticated",
        "user_disabled",
        "organization_not_found",
        "organization_suspended",
        "report_not_found",
        "organization_access_denied",
        "permission_denied",
        "production_access_blocked",
        "internal_error",
    }
)


class AppError(Exception):
    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = "An internal error occurred."

    def __init__(self, message: str | None = None) -> None:
        if message is not None:
            self.message = message
        super().__init__(self.message)


class UnauthenticatedError(AppError):
    code = "unauthenticated"
    status_code = status.HTTP_401_UNAUTHORIZED
    message = "Authentication is required."


class UserDisabledError(AppError):
    code = "user_disabled"
    status_code = status.HTTP_403_FORBIDDEN
    message = "User account is disabled."


EmployeeDisabledError = UserDisabledError


class OrganizationNotFoundError(AppError):
    code = "organization_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Organization not found."


class OrganizationSuspendedError(AppError):
    code = "organization_suspended"
    status_code = status.HTTP_403_FORBIDDEN
    message = "Organization access is suspended."


class ReportNotFoundError(AppError):
    code = "report_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Report not found."


class OrganizationAccessDeniedError(AppError):
    code = "organization_access_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "User does not have access to the requested organization."


class PermissionDeniedError(AppError):
    code = "permission_denied"
    status_code = status.HTTP_403_FORBIDDEN
    message = "User does not have the required permission."


class ProductionAccessBlockedError(AppError):
    code = "production_access_blocked"
    status_code = status.HTTP_403_FORBIDDEN
    message = "Production access is blocked in the sandbox environment."


class InternalError(AppError):
    code = "internal_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "An internal error occurred."


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = uuid.uuid4().hex
    return request_id


def _error_body(code: str, message: str, request_id: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def _json_error(
    request: Request, status_code: int, code: str, message: str
) -> JSONResponse:
    request_id = _request_id(request)
    return JSONResponse(
        status_code=status_code,
        content=_error_body(code, message, request_id),
        headers={REQUEST_ID_HEADER: request_id},
    )


async def _app_error_handler(request: Request, exception: AppError) -> JSONResponse:
    return _json_error(
        request,
        exception.status_code,
        exception.code,
        exception.message,
    )


async def _http_exception_handler(
    request: Request, exception: StarletteHTTPException
) -> JSONResponse:
    if exception.status_code == status.HTTP_401_UNAUTHORIZED:
        error_code = "unauthenticated"
    elif exception.status_code == status.HTTP_403_FORBIDDEN:
        error_code = "permission_denied"
    elif exception.status_code == status.HTTP_404_NOT_FOUND:
        error_code = "organization_not_found"
    else:
        error_code = "internal_error"

    error_message = (
        exception.detail
        if isinstance(exception.detail, str)
        else "Request could not be processed."
    )
    return _json_error(request, exception.status_code, error_code, error_message)


async def _validation_exception_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    return _json_error(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "internal_error",
        "Request validation failed.",
    )


async def _unhandled_exception_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    logger.exception("Unhandled exception during request", exc_info=exception)
    return _json_error(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An internal error occurred.",
    )


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(AppError, _app_error_handler)
    application.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    application.add_exception_handler(
        RequestValidationError,
        _validation_exception_handler,
    )
    application.add_exception_handler(Exception, _unhandled_exception_handler)
