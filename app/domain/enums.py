"""Domain enumerations and canonical permission/role constants.

These are the backend-owned vocabulary. Roles and permissions are never
accepted from the request body or user text.
"""

from __future__ import annotations

from enum import Enum


class Environment(str, Enum):
    """Deployment environment. Step 0 supports only ``sandbox``."""

    SANDBOX = "sandbox"