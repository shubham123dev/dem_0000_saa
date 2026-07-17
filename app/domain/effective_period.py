from __future__ import annotations

from datetime import datetime, timezone


def convert_datetime_to_utc(datetime_value: datetime) -> datetime:
    if datetime_value.tzinfo is None:
        return datetime_value.replace(tzinfo=timezone.utc)
    return datetime_value.astimezone(timezone.utc)


def is_reference_time_within_effective_period(
    *,
    effective_period_start: datetime | None,
    effective_period_end: datetime | None,
    reference_time_utc: datetime | None = None,
) -> bool:
    evaluated_reference_time_utc = reference_time_utc or datetime.now(timezone.utc)
    normalized_reference_time_utc = convert_datetime_to_utc(evaluated_reference_time_utc)

    if effective_period_start is not None:
        normalized_effective_period_start = convert_datetime_to_utc(effective_period_start)
        if normalized_reference_time_utc < normalized_effective_period_start:
            return False

    if effective_period_end is not None:
        normalized_effective_period_end = convert_datetime_to_utc(effective_period_end)
        if normalized_reference_time_utc >= normalized_effective_period_end:
            return False

    return True
