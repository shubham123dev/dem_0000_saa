"""Domain enumerations and canonical permission/role constants.

These are the backend-owned vocabulary. Roles and permissions are never
accepted from request bodies or user text.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Deployment environment. The current product supports sandbox only."""

    SANDBOX = "sandbox"
    # Defined so