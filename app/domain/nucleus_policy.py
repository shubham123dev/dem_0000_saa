"""Backend-owned policy for editable Nucleus organization account fields."""

from __future__ import annotations

NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS: dict[str, int] = {
    "OrganizationName": 250,
    "OrganizationType": 100,
    "Industry": 150,
    "Website": 250,
    "Email": 150,
    "ContactPersonName": 150,
    "ContactPersonDesignation": 150,
    "ContactPhone": 50,
    "AddressLine1": 250,
    "AddressLine2": 250,
    "City": 100,
    "State": 100,
    "Country": 100,
    "PostalCode": 30,
}

EDITABLE_NUCLEUS_ACCOUNT_FIELDS = frozenset(
    NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS
)
CLEARABLE_NUCLEUS_ACCOUNT_FIELDS = (
    EDITABLE_NUCLEUS_ACCOUNT_FIELDS - {"OrganizationName"}
)
