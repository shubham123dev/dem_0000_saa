"""Employee API schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import EmployeeStatus


class EmployeeOut(BaseModel):
    """Public employee representation (never exposes ORM objects)."""

    id: str
    display_name: str
    email: str
    status: EmployeeStatus
