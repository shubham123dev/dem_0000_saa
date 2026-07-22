from __future__ import annotations

from fastapi import status

from app.core.errors import AppError


class WorkplaceResourceInvalidError(AppError):
    code = "workplace_resource_invalid"
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "Workplace resource request is invalid."


class WorkplaceResourceNotFoundError(AppError):
    code = "workplace_resource_not_found"
    status_code = status.HTTP_404_NOT_FOUND
    message = "Workplace resource was not found."
