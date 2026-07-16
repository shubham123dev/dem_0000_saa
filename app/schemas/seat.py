"""Seat entitlement / assignment API schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.domain.enums import SeatType
from app.domain.models import SeatSummary
from app.schemas.organization import OrganizationAccessOut


class SeatSummaryOut(BaseModel):
    """Computed seat entitlement vs. usage.

    ``available_seats`` is derived (``total_seats - active_assignments``); it is
    never stored.
    """

    organization_id: str
    seat_type: SeatType
    total_seats: int
    active_assignments: int
    available_seats: int
    seated_user_ids: list[str]

    @classmethod
    def from_domain(cls, summary: SeatSummary) -> "SeatSummaryOut":
        return cls(
            organization_id=summary.organization_id,
            seat_type=summary.seat_type,
            total_seats=summary.total_seats,
            active_assignments=summary.active_assignments,
            available_seats=summary.available_seats,
            seated_user_ids=list(summary.seated_user_ids),
        )


class OrganizationSeatsResponse(BaseModel):
    """Response body for the seat-summary endpoint."""

    organization_id: str
    seats: SeatSummaryOut
    access: OrganizationAccessOut
