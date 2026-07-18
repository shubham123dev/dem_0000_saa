#!/usr/bin/env python3
"""Apply the governed workplace-resource runtime vertical slice.

Baseline repository:
    shubham123dev/dem_0000_saa
Baseline commit:
    90e411b697bfed18005ff664372dfc68129e461d

The applicator is fail-closed. It checks the exact branch and commit, refuses
tracked changes, asserts every source edit, restores touched files when an edit
fails, and never stages, commits, pushes, deletes, or modifies unrelated
untracked files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from textwrap import dedent, indent

BASELINE_COMMIT = "90e411b697bfed18005ff664372dfc68129e461d"


class PatchError(RuntimeError):
    pass


def block(value: str) -> str:
    return dedent(value).strip("\n") + "\n"


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise PatchError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def read_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    if not path.is_file():
        raise PatchError(f"Required file is missing: {relative_path}")
    return path.read_text(encoding="utf-8")


def write_text(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def create_exact(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    normalized = content.strip("\n") + "\n"
    if path.exists():
        if path.read_text(encoding="utf-8") == normalized:
            return
        raise PatchError(f"Refusing to overwrite existing file: {relative_path}")
    write_text(root, relative_path, normalized)


def replace_exact(
    root: Path,
    relative_path: str,
    old: str,
    new: str,
    *,
    expected_count: int = 1,
) -> None:
    text = read_text(root, relative_path)
    count = text.count(old)
    if count != expected_count:
        raise PatchError(
            f"{relative_path}: expected {expected_count} occurrence(s), found {count}:\n{old}"
        )
    write_text(root, relative_path, text.replace(old, new))


def insert_before(root: Path, relative_path: str, marker: str, addition: str) -> None:
    text = read_text(root, relative_path)
    if text.count(marker) != 1:
        raise PatchError(f"{relative_path}: marker missing or ambiguous: {marker}")
    write_text(root, relative_path, text.replace(marker, addition + marker, 1))


def validate_repository(root: Path) -> None:
    if not (root / ".git").is_dir():
        raise PatchError("Run this script against the repository root containing .git")
    branch = run_git(root, "branch", "--show-current")
    if branch != "main":
        raise PatchError(f"Expected branch main, found {branch or '<detached>'}")
    head = run_git(root, "rev-parse", "HEAD")
    if head != BASELINE_COMMIT:
        raise PatchError(
            f"Unexpected HEAD. Expected {BASELINE_COMMIT}, found {head}. "
            "Do not force-apply this patch to another source state."
        )
    if run_git(root, "diff", "--name-only"):
        raise PatchError("Tracked working-tree changes exist; commit or revert them first")
    if run_git(root, "diff", "--cached", "--name-only"):
        raise PatchError("Staged changes exist; commit or unstage them first")


def add_database_models(root: Path) -> None:
    create_exact(
        root,
        "app/db/workplace_resource_models.py",
        block(
            '''
            """Persistence for the governed workplace-resource runtime."""

            from __future__ import annotations

            from datetime import datetime, timezone

            from sqlalchemy import (
                Boolean,
                DateTime,
                ForeignKey,
                Index,
                Integer,
                JSON,
                String,
                UniqueConstraint,
            )
            from sqlalchemy.orm import Mapped, mapped_column

            from app.db.base import Base


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            class WorkplaceSettingORM(Base):
                __tablename__ = "workplace_settings"
                __table_args__ = (
                    UniqueConstraint(
                        "organization_id",
                        "namespace",
                        "setting_key",
                        name="uq_workplace_setting_org_namespace_key",
                    ),
                    Index(
                        "ix_workplace_setting_org_active",
                        "organization_id",
                        "is_active",
                    ),
                )

                id: Mapped[str] = mapped_column(String, primary_key=True)
                organization_id: Mapped[str] = mapped_column(
                    String,
                    ForeignKey("organizations.id", ondelete="CASCADE"),
                    nullable=False,
                    index=True,
                )
                namespace: Mapped[str] = mapped_column(String(80), nullable=False)
                setting_key: Mapped[str] = mapped_column(String(120), nullable=False)
                value_json: Mapped[dict | list | str | int | float | bool | None] = (
                    mapped_column(JSON, nullable=True)
                )
                description: Mapped[str | None] = mapped_column(String(500), nullable=True)
                is_active: Mapped[bool] = mapped_column(
                    Boolean, nullable=False, default=True
                )
                version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
                created_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )
                updated_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True),
                    nullable=False,
                    default=_utcnow,
                    onupdate=_utcnow,
                )


            class WorkplaceResourceSnapshotORM(Base):
                __tablename__ = "workplace_resource_snapshots"
                __table_args__ = (
                    Index(
                        "ix_workplace_snapshot_resource",
                        "organization_id",
                        "resource_type",
                        "resource_id",
                    ),
                )

                id: Mapped[str] = mapped_column(String, primary_key=True)
                organization_id: Mapped[str] = mapped_column(
                    String, ForeignKey("organizations.id"), nullable=False
                )
                resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
                resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
                version: Mapped[int] = mapped_column(Integer, nullable=False)
                snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
                snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
                captured_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )


            class WorkplaceMutationPlanORM(Base):
                __tablename__ = "workplace_mutation_plans"
                __table_args__ = (
                    UniqueConstraint("proposal_id", name="uq_workplace_plan_proposal"),
                )

                id: Mapped[str] = mapped_column(String, primary_key=True)
                proposal_id: Mapped[str] = mapped_column(
                    String,
                    ForeignKey("agent_action_proposals.id", ondelete="CASCADE"),
                    nullable=False,
                )
                organization_id: Mapped[str] = mapped_column(
                    String, ForeignKey("organizations.id"), nullable=False
                )
                operation_type: Mapped[str] = mapped_column(String(80), nullable=False)
                resource_count: Mapped[int] = mapped_column(Integer, nullable=False)
                plan_json: Mapped[dict] = mapped_column(JSON, nullable=False)
                status: Mapped[str] = mapped_column(String(40), nullable=False)
                created_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )
                updated_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True),
                    nullable=False,
                    default=_utcnow,
                    onupdate=_utcnow,
                )


            class WorkplaceMutationStepReceiptORM(Base):
                __tablename__ = "workplace_mutation_step_receipts"
                __table_args__ = (
                    UniqueConstraint(
                        "mutation_plan_id",
                        "step_index",
                        name="uq_workplace_plan_step",
                    ),
                )

                id: Mapped[str] = mapped_column(String, primary_key=True)
                mutation_plan_id: Mapped[str] = mapped_column(
                    String,
                    ForeignKey("workplace_mutation_plans.id", ondelete="CASCADE"),
                    nullable=False,
                )
                step_index: Mapped[int] = mapped_column(Integer, nullable=False)
                resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
                resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
                operation: Mapped[str] = mapped_column(String(80), nullable=False)
                before_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
                after_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
                outcome: Mapped[str] = mapped_column(String(40), nullable=False)
                error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
                attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
                completed_at: Mapped[datetime | None] = mapped_column(
                    DateTime(timezone=True), nullable=True
                )


            class WorkplaceResourceTombstoneORM(Base):
                __tablename__ = "workplace_resource_tombstones"
                __table_args__ = (
                    UniqueConstraint(
                        "organization_id",
                        "resource_type",
                        "resource_id",
                        name="uq_workplace_resource_tombstone",
                    ),
                )

                id: Mapped[str] = mapped_column(String, primary_key=True)
                organization_id: Mapped[str] = mapped_column(
                    String, ForeignKey("organizations.id"), nullable=False
                )
                resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
                resource_id: Mapped[str] = mapped_column(String(250), nullable=False)
                version: Mapped[int] = mapped_column(Integer, nullable=False)
                snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
                deleted_by_user_id: Mapped[str] = mapped_column(
                    String, ForeignKey("users.id"), nullable=False
                )
                deleted_at: Mapped[datetime] = mapped_column(
                    DateTime(timezone=True), nullable=False, default=_utcnow
                )
                restored_at: Mapped[datetime | None] = mapped_column(
                    DateTime(timezone=True), nullable=True
                )
            '''
        ),
    )


def add_resource_runtime(root: Path) -> None:
    create_exact(root, "app/workplace_resources/__init__.py", '"""Governed workplace resource runtime."""\n')
    create_exact(
        root,
        "app/workplace_resources/definitions.py",
        block(
            '''
            from __future__ import annotations

            from dataclasses import dataclass
            from typing import Any, Literal


            FieldKind = Literal["string", "integer", "boolean", "json", "datetime", "date"]
            Operation = Literal[
                "read",
                "search",
                "create",
                "update",
                "clear",
                "activate",
                "deactivate",
                "delete",
                "restore",
                "bulk_update",
            ]


            @dataclass(frozen=True)
            class WorkplaceFieldPolicy:
                name: str
                attribute: str
                kind: FieldKind
                nullable: bool = False
                readable: bool = True
                editable: bool = False
                clearable: bool = False
                searchable: bool = False
                sortable: bool = False
                sensitive: bool = False
                maximum_length: int | None = None
                enum_values: tuple[str, ...] = ()


            @dataclass(frozen=True)
            class WorkplaceResourceDefinition:
                resource_type: str
                display_name: str
                orm_type: type | None
                id_attribute: str
                organization_attribute: str | None
                version_attribute: str | None
                fields: tuple[WorkplaceFieldPolicy, ...]
                operations: frozenset[Operation]
                soft_delete_attribute: str | None = None
                dedicated_management: bool = False

                @property
                def field_map(self) -> dict[str, WorkplaceFieldPolicy]:
                    return {field.name: field for field in self.fields}

                def public_schema(self) -> dict[str, Any]:
                    return {
                        "resource_type": self.resource_type,
                        "display_name": self.display_name,
                        "operations": sorted(self.operations),
                        "dedicated_management": self.dedicated_management,
                        "fields": [
                            {
                                "name": field.name,
                                "kind": field.kind,
                                "nullable": field.nullable,
                                "editable": field.editable,
                                "clearable": field.clearable,
                                "searchable": field.searchable,
                                "sortable": field.sortable,
                            }
                            for field in self.fields
                            if field.readable and not field.sensitive
                        ],
                    }
            '''
        ),
    )

    create_exact(
        root,
        "app/workplace_resources/registry.py",
        block(
            '''
            from __future__ import annotations

            from app.db.nucleus_models import (
                NucleusOrganizationAccountORM,
                NucleusOrganizationCategoryAccessORM,
                NucleusOrganizationCompanyProfileAccessORM,
                NucleusOrganizationDrugAccessORM,
                NucleusOrganizationIndicationAccessORM,
                NucleusOrganizationMarketAccessORM,
                NucleusOrganizationPermissionORM,
                NucleusOrganizationReportAccessORM,
            )
            from app.db.orm_models import (
                OrganizationMembershipORM,
                OrganizationORM,
                OrganizationOverviewORM,
                OrganizationReportAccessORM,
                OrganizationSeatPoolORM,
                SeatAssignmentORM,
            )
            from app.db.workplace_resource_models import WorkplaceSettingORM
            from app.workplace_resources.definitions import (
                WorkplaceFieldPolicy,
                WorkplaceResourceDefinition,
            )


            def _field(
                name: str,
                attribute: str,
                kind: str,
                **kwargs,
            ) -> WorkplaceFieldPolicy:
                return WorkplaceFieldPolicy(
                    name=name,
                    attribute=attribute,
                    kind=kind,
                    **kwargs,
                )


            class WorkplaceResourceRegistry:
                def __init__(self) -> None:
                    definitions = (
                        WorkplaceResourceDefinition(
                            resource_type="organization",
                            display_name="Organization",
                            orm_type=OrganizationORM,
                            id_attribute="id",
                            organization_attribute="id",
                            version_attribute="version",
                            operations=frozenset({"read", "search", "update", "clear"}),
                            fields=(
                                _field("id", "id", "string", searchable=True, sortable=True),
                                _field("display_name", "display_name", "string", editable=True, searchable=True, sortable=True, maximum_length=250),
                                _field("legal_name", "legal_name", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=250),
                                _field("contact_email", "contact_email", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=320),
                                _field("environment", "environment", "string", sortable=True),
                                _field("status", "status", "string", sortable=True),
                                _field("version", "version", "integer", sortable=True),
                                _field("created_at", "created_at", "datetime", sortable=True),
                                _field("updated_at", "updated_at", "datetime", sortable=True),
                            ),
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="workplace_setting",
                            display_name="Workplace setting",
                            orm_type=WorkplaceSettingORM,
                            id_attribute="id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            soft_delete_attribute="is_active",
                            operations=frozenset({"read", "search", "create", "update", "clear", "activate", "deactivate", "delete", "restore", "bulk_update"}),
                            fields=(
                                _field("id", "id", "string", searchable=True, sortable=True),
                                _field("namespace", "namespace", "string", editable=False, searchable=True, sortable=True, maximum_length=80),
                                _field("key", "setting_key", "string", editable=False, searchable=True, sortable=True, maximum_length=120),
                                _field("value", "value_json", "json", nullable=True, editable=True, clearable=True),
                                _field("description", "description", "string", nullable=True, editable=True, clearable=True, searchable=True, maximum_length=500),
                                _field("is_active", "is_active", "boolean", sortable=True),
                                _field("version", "version", "integer", sortable=True),
                                _field("created_at", "created_at", "datetime", sortable=True),
                                _field("updated_at", "updated_at", "datetime", sortable=True),
                            ),
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="organization_overview",
                            display_name="Organization overview",
                            orm_type=OrganizationOverviewORM,
                            id_attribute="organization_id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            operations=frozenset({"read", "search"}),
                            fields=(
                                _field("organization_id", "organization_id", "string", searchable=True),
                                _field("organization_type", "organization_type", "string", searchable=True),
                                _field("renewal_date", "renewal_date", "date", nullable=True, sortable=True),
                                _field("workspace_status", "workspace_status", "string", searchable=True),
                                _field("workspace_health_percent", "workspace_health_percent", "integer", sortable=True),
                                _field("version", "version", "integer"),
                            ),
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="organization_membership",
                            display_name="Organization membership",
                            orm_type=OrganizationMembershipORM,
                            id_attribute="id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            operations=frozenset({"read", "search"}),
                            fields=(
                                _field("id", "id", "integer", searchable=True),
                                _field("user_id", "user_id", "string", searchable=True),
                                _field("role", "role", "string", searchable=True),
                                _field("status", "membership_status", "string", searchable=True),
                                _field("version", "version", "integer"),
                            ),
                            dedicated_management=True,
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="organization_seat_pool",
                            display_name="Organization seat pool",
                            orm_type=OrganizationSeatPoolORM,
                            id_attribute="id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            operations=frozenset({"read", "search"}),
                            fields=(
                                _field("id", "id", "string", searchable=True),
                                _field("seat_type", "seat_type", "string", searchable=True),
                                _field("total_seats", "total_seats", "integer", sortable=True),
                                _field("status", "status", "string", searchable=True),
                                _field("version", "version", "integer"),
                            ),
                            dedicated_management=True,
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="seat_assignment",
                            display_name="Seat assignment",
                            orm_type=SeatAssignmentORM,
                            id_attribute="id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            operations=frozenset({"read", "search"}),
                            fields=(
                                _field("id", "id", "string", searchable=True),
                                _field("seat_pool_id", "seat_pool_id", "string", searchable=True),
                                _field("user_id", "user_id", "string", searchable=True),
                                _field("status", "status", "string", searchable=True),
                                _field("version", "version", "integer"),
                            ),
                            dedicated_management=True,
                        ),
                        WorkplaceResourceDefinition(
                            resource_type="organization_report_access",
                            display_name="Organization report access",
                            orm_type=OrganizationReportAccessORM,
                            id_attribute="id",
                            organization_attribute="organization_id",
                            version_attribute="version",
                            operations=frozenset({"read", "search"}),
                            fields=(
                                _field("id", "id", "string", searchable=True),
                                _field("report_id", "report_id", "string", searchable=True),
                                _field("access_level", "access_level", "string", searchable=True),
                                _field("status", "status", "string", searchable=True),
                                _field("version", "version", "integer"),
                            ),
                            dedicated_management=True,
                        ),
                    ) + self._nucleus_definitions()
                    self._definitions = {item.resource_type: item for item in definitions}
                    if len(self._definitions) != len(definitions):
                        raise RuntimeError("Duplicate workplace resource type")
                    self._validate()

                @staticmethod
                def _nucleus_definitions() -> tuple[WorkplaceResourceDefinition, ...]:
                    specs = (
                        ("nucleus_organization_account", "Nucleus organization account", NucleusOrganizationAccountORM, "organization_account_id"),
                        ("nucleus_category_access", "Nucleus category access", NucleusOrganizationCategoryAccessORM, "organization_category_access_id"),
                        ("nucleus_company_profile_access", "Nucleus company profile access", NucleusOrganizationCompanyProfileAccessORM, "organization_company_profile_access_id"),
                        ("nucleus_drug_access", "Nucleus drug access", NucleusOrganizationDrugAccessORM, "organization_drug_access_id"),
                        ("nucleus_indication_access", "Nucleus indication access", NucleusOrganizationIndicationAccessORM, "organization_indication_access_id"),
                        ("nucleus_market_access", "Nucleus market access", NucleusOrganizationMarketAccessORM, "organization_market_access_id"),
                        ("nucleus_permission", "Nucleus permission", NucleusOrganizationPermissionORM, "organization_permission_id"),
                        ("nucleus_report_access", "Nucleus report access", NucleusOrganizationReportAccessORM, "organization_report_access_id"),
                    )
                    return tuple(
                        WorkplaceResourceDefinition(
                            resource_type=resource_type,
                            display_name=display_name,
                            orm_type=orm_type,
                            id_attribute=id_attribute,
                            organization_attribute=None,
                            version_attribute=None,
                            operations=frozenset({"read"}),
                            fields=(
                                _field("id", id_attribute, "integer"),
                            ),
                            dedicated_management=True,
                        )
                        for resource_type, display_name, orm_type, id_attribute in specs
                    )

                def _validate(self) -> None:
                    for definition in self._definitions.values():
                        names = [field.name for field in definition.fields]
                        if len(names) != len(set(names)):
                            raise RuntimeError(f"Duplicate field in {definition.resource_type}")
                        if definition.orm_type is not None:
                            for field in definition.fields:
                                if not hasattr(definition.orm_type, field.attribute):
                                    raise RuntimeError(
                                        f"Unknown ORM attribute {definition.resource_type}.{field.attribute}"
                                    )
                        for field in definition.fields:
                            if field.sensitive and field.readable:
                                raise RuntimeError("Sensitive fields cannot be readable")
                            if field.clearable and not field.nullable:
                                raise RuntimeError("Only nullable fields can be clearable")

                def list_definitions(self) -> tuple[WorkplaceResourceDefinition, ...]:
                    return tuple(self._definitions.values())

                def get(self, resource_type: str) -> WorkplaceResourceDefinition:
                    try:
                        return self._definitions[resource_type]
                    except KeyError as exception:
                        raise ValueError("Unknown workplace resource type") from exception
            '''
        ),
    )


def add_resource_service(root: Path) -> None:
    create_exact(
        root,
        "app/workplace_resources/service.py",
        block(
            '''
            from __future__ import annotations

            from datetime import date, datetime, timezone
            import hashlib
            import json
            import re
            import uuid
            from typing import Any

            from sqlalchemy import func, select, update
            from sqlalchemy.exc import IntegrityError
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.agent.action_contracts import (
                AgentActionChange,
                AgentActionHandlerResult,
                AgentActionPreparation,
                AgentActionProposal,
                AgentActionResourcePrecondition,
            )
            from app.agent.action_handlers import StaleActionResourceError
            from app.db.workplace_resource_models import (
                WorkplaceMutationPlanORM,
                WorkplaceMutationStepReceiptORM,
                WorkplaceResourceSnapshotORM,
                WorkplaceResourceTombstoneORM,
                WorkplaceSettingORM,
            )
            from app.workplace_resources.definitions import (
                WorkplaceFieldPolicy,
                WorkplaceResourceDefinition,
            )
            from app.workplace_resources.registry import WorkplaceResourceRegistry

            _NAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,119}$")
            _MAX_PAGE_SIZE = 100
            _MAX_BULK_SIZE = 50


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            def _canonical(value: Any) -> Any:
                if isinstance(value, datetime):
                    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
                    return aware.astimezone(timezone.utc).isoformat()
                if isinstance(value, date):
                    return value.isoformat()
                return value


            def _hash_snapshot(snapshot: dict[str, Any]) -> str:
                payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
                return hashlib.sha256(payload.encode("utf-8")).hexdigest()


            class WorkplaceResourceService:
                def __init__(
                    self,
                    session: AsyncSession,
                    registry: WorkplaceResourceRegistry | None = None,
                ) -> None:
                    self._session = session
                    self._registry = registry or WorkplaceResourceRegistry()

                def list_resource_types(self) -> tuple[dict[str, Any], ...]:
                    return tuple(
                        definition.public_schema()
                        for definition in self._registry.list_definitions()
                    )

                def describe(self, resource_type: str) -> dict[str, Any]:
                    return self._registry.get(resource_type).public_schema()

                @staticmethod
                def _require_generic(definition: WorkplaceResourceDefinition) -> None:
                    if definition.orm_type is None or definition.organization_attribute is None:
                        raise ValueError(
                            "This resource uses a dedicated organization-scoped adapter"
                        )

                @staticmethod
                def _field_value(row: Any, policy: WorkplaceFieldPolicy) -> Any:
                    return _canonical(getattr(row, policy.attribute))

                def _serialize(
                    self,
                    definition: WorkplaceResourceDefinition,
                    row: Any,
                ) -> dict[str, Any]:
                    return {
                        field.name: self._field_value(row, field)
                        for field in definition.fields
                        if field.readable and not field.sensitive
                    }

                def _scope_condition(
                    self,
                    definition: WorkplaceResourceDefinition,
                    organization_id: str,
                ):
                    attribute = getattr(
                        definition.orm_type, definition.organization_attribute
                    )
                    return attribute == organization_id

                async def get(
                    self,
                    *,
                    organization_id: str,
                    resource_type: str,
                    resource_id: str,
                    include_inactive: bool = True,
                ) -> dict[str, Any] | None:
                    definition = self._registry.get(resource_type)
                    self._require_generic(definition)
                    statement = select(definition.orm_type).where(
                        self._scope_condition(definition, organization_id),
                        getattr(definition.orm_type, definition.id_attribute)
                        == self._coerce_identifier(definition, resource_id),
                    )
                    if definition.soft_delete_attribute and not include_inactive:
                        statement = statement.where(
                            getattr(
                                definition.orm_type,
                                definition.soft_delete_attribute,
                            ).is_(True)
                        )
                    row = await self._session.scalar(statement)
                    return self._serialize(definition, row) if row is not None else None

                async def search(
                    self,
                    *,
                    organization_id: str,
                    resource_type: str,
                    filters: dict[str, Any],
                    sort_by: str | None,
                    descending: bool,
                    limit: int,
                    offset: int,
                ) -> tuple[tuple[dict[str, Any], ...], int]:
                    definition = self._registry.get(resource_type)
                    self._require_generic(definition)
                    if "search" not in definition.operations:
                        raise ValueError("This resource does not support generic search")
                    if limit < 1 or limit > _MAX_PAGE_SIZE or offset < 0:
                        raise ValueError("Invalid resource pagination")
                    conditions = [self._scope_condition(definition, organization_id)]
                    field_map = definition.field_map
                    for name, raw_value in filters.items():
                        policy = field_map.get(name)
                        if policy is None or not policy.searchable or policy.sensitive:
                            raise ValueError(f"Unsupported resource filter: {name}")
                        column = getattr(definition.orm_type, policy.attribute)
                        value = self._coerce_value(policy, raw_value)
                        conditions.append(column.is_(None) if value is None else column == value)
                    order_column = getattr(
                        definition.orm_type, definition.id_attribute
                    )
                    if sort_by is not None:
                        policy = field_map.get(sort_by)
                        if policy is None or not policy.sortable or policy.sensitive:
                            raise ValueError("Unsupported resource sort")
                        order_column = getattr(definition.orm_type, policy.attribute)
                    order = order_column.desc() if descending else order_column.asc()
                    statement = (
                        select(definition.orm_type)
                        .where(*conditions)
                        .order_by(order)
                        .limit(limit)
                        .offset(offset)
                    )
                    rows = tuple((await self._session.execute(statement)).scalars().all())
                    total = int(
                        await self._session.scalar(
                            select(func.count())
                            .select_from(definition.orm_type)
                            .where(*conditions)
                        )
                        or 0
                    )
                    return tuple(self._serialize(definition, row) for row in rows), total

                @staticmethod
                def _coerce_identifier(
                    definition: WorkplaceResourceDefinition,
                    resource_id: str,
                ) -> Any:
                    field = next(
                        (
                            item
                            for item in definition.fields
                            if item.attribute == definition.id_attribute
                        ),
                        None,
                    )
                    if field is not None and field.kind == "integer":
                        try:
                            return int(resource_id)
                        except ValueError as exception:
                            raise ValueError("Resource ID must be an integer") from exception
                    return resource_id

                @staticmethod
                def _coerce_value(policy: WorkplaceFieldPolicy, value: Any) -> Any:
                    if value is None:
                        if not policy.nullable:
                            raise ValueError(f"{policy.name} cannot be null")
                        return None
                    if policy.kind == "string":
                        normalized = str(value).strip()
                        if not normalized and not policy.nullable:
                            raise ValueError(f"{policy.name} is required")
                        if policy.maximum_length and len(normalized) > policy.maximum_length:
                            raise ValueError(f"{policy.name} is too long")
                        if policy.enum_values and normalized not in policy.enum_values:
                            raise ValueError(f"{policy.name} has an invalid value")
                        if policy.name == "contact_email" and normalized:
                            local, separator, domain = normalized.lower().partition("@")
                            if not separator or not local or "." not in domain:
                                raise ValueError("contact_email is invalid")
                            return normalized.lower()
                        return normalized
                    if policy.kind == "integer":
                        try:
                            return int(value)
                        except (TypeError, ValueError) as exception:
                            raise ValueError(f"{policy.name} must be an integer") from exception
                    if policy.kind == "boolean":
                        if isinstance(value, bool):
                            return value
                        normalized = str(value).strip().lower()
                        if normalized in {"true", "1", "yes"}:
                            return True
                        if normalized in {"false", "0", "no"}:
                            return False
                        raise ValueError(f"{policy.name} must be a boolean")
                    if policy.kind == "json":
                        return value
                    raise ValueError(f"Unsupported field kind for {policy.name}")

                @staticmethod
                def _parse_json_object(value: str, *, field_name: str) -> dict[str, Any]:
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError as exception:
                        raise ValueError(f"{field_name} must be valid JSON") from exception
                    if not isinstance(parsed, dict):
                        raise ValueError(f"{field_name} must be a JSON object")
                    return parsed

                @staticmethod
                def _parse_json_list(value: str, *, field_name: str) -> list[Any]:
                    try:
                        parsed = json.loads(value)
                    except json.JSONDecodeError as exception:
                        raise ValueError(f"{field_name} must be valid JSON") from exception
                    if not isinstance(parsed, list):
                        raise ValueError(f"{field_name} must be a JSON list")
                    return parsed

                def _validate_changes(
                    self,
                    definition: WorkplaceResourceDefinition,
                    changes: dict[str, Any],
                    *,
                    clear: bool = False,
                ) -> dict[str, Any]:
                    if not changes:
                        raise ValueError("At least one resource field is required")
                    normalized: dict[str, Any] = {}
                    for name, value in changes.items():
                        policy = definition.field_map.get(name)
                        if policy is None or policy.sensitive:
                            raise ValueError(f"Unknown or protected resource field: {name}")
                        if clear:
                            if not policy.clearable:
                                raise ValueError(f"Resource field cannot be cleared: {name}")
                            normalized[name] = None
                        else:
                            if not policy.editable:
                                raise ValueError(f"Resource field is not editable: {name}")
                            normalized[name] = self._coerce_value(policy, value)
                    return normalized

                async def _row(
                    self,
                    definition: WorkplaceResourceDefinition,
                    organization_id: str,
                    resource_id: str,
                ) -> Any | None:
                    return await self._session.scalar(
                        select(definition.orm_type).where(
                            self._scope_condition(definition, organization_id),
                            getattr(definition.orm_type, definition.id_attribute)
                            == self._coerce_identifier(definition, resource_id),
                        )
                    )

                @staticmethod
                def _version(
                    definition: WorkplaceResourceDefinition,
                    row: Any,
                ) -> int:
                    if definition.version_attribute is None:
                        return 0
                    return int(getattr(row, definition.version_attribute))

                async def prepare(
                    self,
                    *,
                    organization_id: str,
                    operation: str,
                    arguments: dict[str, str],
                ) -> AgentActionPreparation:
                    resource_type = arguments["resource_type"].strip()
                    definition = self._registry.get(resource_type)
                    self._require_generic(definition)
                    if operation not in definition.operations:
                        raise ValueError("Operation is not allowed for this resource")

                    if operation == "create":
                        values = self._parse_json_object(arguments["values_json"], field_name="values_json")
                        if resource_type != "workplace_setting":
                            raise ValueError("Generic creation is currently limited to workplace settings")
                        allowed = {"namespace", "key", "value", "description"}
                        if set(values) - allowed or not {"namespace", "key"}.issubset(values):
                            raise ValueError("Workplace setting fields are invalid")
                        namespace = str(values["namespace"]).strip().lower()
                        key = str(values["key"]).strip().lower()
                        if not _NAME_RE.fullmatch(namespace) or not _NAME_RE.fullmatch(key):
                            raise ValueError("Setting namespace and key are invalid")
                        normalized_values = {
                            "namespace": namespace,
                            "key": key,
                            "value": values.get("value"),
                            "description": (
                                str(values["description"]).strip()
                                if values.get("description") is not None
                                else None
                            ),
                        }
                        existing = await self._session.scalar(
                            select(WorkplaceSettingORM).where(
                                WorkplaceSettingORM.organization_id == organization_id,
                                WorkplaceSettingORM.namespace == namespace,
                                WorkplaceSettingORM.setting_key == key,
                            )
                        )
                        if existing is not None:
                            raise ValueError("Workplace setting already exists")
                        resource_id = f"new:{namespace}:{key}"
                        return AgentActionPreparation(
                            normalized_arguments={
                                "resource_type": resource_type,
                                "values_json": json.dumps(normalized_values, sort_keys=True, separators=(",", ":")),
                            },
                            changes=(AgentActionChange(field="resource", before=None, after=normalized_values),),
                            observed_resource_version=0,
                            resource_type=resource_type,
                            resource_id=resource_id,
                        )

                    if operation == "bulk_update":
                        ids = [str(item) for item in self._parse_json_list(arguments["resource_ids_json"], field_name="resource_ids_json")]
                        if not ids or len(ids) > _MAX_BULK_SIZE or len(ids) != len(set(ids)):
                            raise ValueError("Bulk resource IDs are invalid")
                        changes = self._validate_changes(
                            definition,
                            self._parse_json_object(arguments["changes_json"], field_name="changes_json"),
                        )
                        rows = []
                        for resource_id in ids:
                            row = await self._row(definition, organization_id, resource_id)
                            if row is None:
                                raise ValueError("Bulk resource was not found")
                            rows.append(row)
                        before = [self._serialize(definition, row) for row in rows]
                        after = [
                            {**snapshot, **{name: _canonical(value) for name, value in changes.items()}}
                            for snapshot in before
                        ]
                        preconditions = tuple(
                            AgentActionResourcePrecondition(
                                resource_type=resource_type,
                                resource_id=str(getattr(row, definition.id_attribute)),
                                observed_version=self._version(definition, row),
                            )
                            for row in rows
                        )
                        batch_id = hashlib.sha256("\\n".join(sorted(ids)).encode("utf-8")).hexdigest()
                        return AgentActionPreparation(
                            normalized_arguments={
                                "resource_type": resource_type,
                                "resource_ids_json": json.dumps(ids, separators=(",", ":")),
                                "changes_json": json.dumps(changes, sort_keys=True, separators=(",", ":"), default=str),
                            },
                            changes=(AgentActionChange(field="resources", before=before, after=after),),
                            observed_resource_version=0,
                            resource_type=f"{resource_type}_batch",
                            resource_id=batch_id,
                            resource_preconditions=preconditions,
                        )

                    resource_id = arguments["resource_id"].strip()
                    row = await self._row(definition, organization_id, resource_id)
                    if row is None:
                        raise ValueError("Workplace resource was not found")
                    before = self._serialize(definition, row)
                    version = self._version(definition, row)
                    if operation == "update":
                        changes = self._validate_changes(
                            definition,
                            self._parse_json_object(arguments["changes_json"], field_name="changes_json"),
                        )
                    elif operation == "clear":
                        fields = self._parse_json_list(arguments["fields_json"], field_name="fields_json")
                        if not all(isinstance(item, str) for item in fields):
                            raise ValueError("Clear fields must be strings")
                        changes = self._validate_changes(
                            definition, {str(item): None for item in fields}, clear=True
                        )
                    elif operation in {"activate", "deactivate", "delete", "restore"}:
                        if definition.soft_delete_attribute is None:
                            raise ValueError("Resource has no lifecycle policy")
                        target = operation in {"activate", "restore"}
                        current = bool(getattr(row, definition.soft_delete_attribute))
                        if current == target:
                            raise ValueError("Resource already has this lifecycle state")
                        if operation == "restore":
                            tombstone = await self._session.scalar(
                                select(WorkplaceResourceTombstoneORM).where(
                                    WorkplaceResourceTombstoneORM.organization_id == organization_id,
                                    WorkplaceResourceTombstoneORM.resource_type == resource_type,
                                    WorkplaceResourceTombstoneORM.resource_id == resource_id,
                                    WorkplaceResourceTombstoneORM.restored_at.is_(None),
                                )
                            )
                            if tombstone is None:
                                raise ValueError("Resource has no active tombstone to restore")
                        changes = {"is_active": target}
                    else:
                        raise ValueError("Unsupported workplace resource operation")
                    after = {**before, **{name: _canonical(value) for name, value in changes.items()}}
                    normalized = {
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                    }
                    if operation == "update":
                        normalized["changes_json"] = json.dumps(changes, sort_keys=True, separators=(",", ":"), default=str)
                    elif operation == "clear":
                        normalized["fields_json"] = json.dumps(sorted(changes), separators=(",", ":"))
                    return AgentActionPreparation(
                        normalized_arguments=normalized,
                        changes=tuple(
                            AgentActionChange(field=name, before=before.get(name), after=_canonical(value))
                            for name, value in sorted(changes.items())
                        ),
                        observed_resource_version=version,
                        resource_type=resource_type,
                        resource_id=resource_id,
                    )

                async def _record_plan(
                    self,
                    *,
                    proposal: AgentActionProposal,
                    operation: str,
                    resources: list[dict[str, Any]],
                ) -> WorkplaceMutationPlanORM:
                    existing = await self._session.scalar(
                        select(WorkplaceMutationPlanORM).where(
                            WorkplaceMutationPlanORM.proposal_id == proposal.id
                        )
                    )
                    if existing is not None:
                        return existing
                    plan = WorkplaceMutationPlanORM(
                        id=uuid.uuid4().hex,
                        proposal_id=proposal.id,
                        organization_id=proposal.organization_id,
                        operation_type=operation,
                        resource_count=len(resources),
                        plan_json={"resources": resources},
                        status="executing",
                        created_at=_utcnow(),
                        updated_at=_utcnow(),
                    )
                    self._session.add(plan)
                    await self._session.flush()
                    return plan

                async def _record_snapshot(
                    self,
                    *,
                    organization_id: str,
                    resource_type: str,
                    resource_id: str,
                    version: int,
                    snapshot: dict[str, Any],
                ) -> None:
                    self._session.add(
                        WorkplaceResourceSnapshotORM(
                            id=uuid.uuid4().hex,
                            organization_id=organization_id,
                            resource_type=resource_type,
                            resource_id=resource_id,
                            version=version,
                            snapshot_hash=_hash_snapshot(snapshot),
                            snapshot_json=snapshot,
                            captured_at=_utcnow(),
                        )
                    )

                async def execute(
                    self,
                    *,
                    proposal: AgentActionProposal,
                    operation: str,
                ) -> AgentActionHandlerResult:
                    definition = self._registry.get(proposal.arguments["resource_type"])
                    self._require_generic(definition)
                    now = _utcnow()

                    if operation == "create":
                        values = self._parse_json_object(proposal.arguments["values_json"], field_name="values_json")
                        row = WorkplaceSettingORM(
                            id=uuid.uuid4().hex,
                            organization_id=proposal.organization_id,
                            namespace=values["namespace"],
                            setting_key=values["key"],
                            value_json=values.get("value"),
                            description=values.get("description"),
                            is_active=True,
                            version=1,
                            created_at=now,
                            updated_at=now,
                        )
                        plan = await self._record_plan(
                            proposal=proposal,
                            operation=operation,
                            resources=[{"resource_type": definition.resource_type, "resource_id": row.id}],
                        )
                        self._session.add(row)
                        try:
                            await self._session.flush()
                        except IntegrityError as exception:
                            await self._session.rollback()
                            raise StaleActionResourceError() from exception
                        after = self._serialize(definition, row)
                        await self._record_snapshot(
                            organization_id=proposal.organization_id,
                            resource_type=definition.resource_type,
                            resource_id=row.id,
                            version=1,
                            snapshot=after,
                        )
                        self._session.add(
                            WorkplaceMutationStepReceiptORM(
                                id=uuid.uuid4().hex,
                                mutation_plan_id=plan.id,
                                step_index=0,
                                resource_type=definition.resource_type,
                                resource_id=row.id,
                                operation=operation,
                                before_json=None,
                                after_json=after,
                                outcome="succeeded",
                                completed_at=now,
                            )
                        )
                        plan.status = "succeeded"
                        await self._session.commit()
                        return AgentActionHandlerResult(
                            resource_type=definition.resource_type,
                            resource_id=row.id,
                            before={},
                            after=after,
                        )

                    if operation == "bulk_update":
                        resource_ids = [str(item) for item in self._parse_json_list(proposal.arguments["resource_ids_json"], field_name="resource_ids_json")]
                        changes = self._parse_json_object(proposal.arguments["changes_json"], field_name="changes_json")
                        plan = await self._record_plan(
                            proposal=proposal,
                            operation=operation,
                            resources=[{"resource_type": definition.resource_type, "resource_id": item} for item in resource_ids],
                        )
                        before_rows: list[dict[str, Any]] = []
                        after_rows: list[dict[str, Any]] = []
                        for index, resource_id in enumerate(resource_ids):
                            row = await self._row(definition, proposal.organization_id, resource_id)
                            precondition = next(
                                (
                                    item
                                    for item in proposal.resource_preconditions
                                    if item.resource_type == definition.resource_type
                                    and item.resource_id == resource_id
                                ),
                                None,
                            )
                            if row is None or precondition is None or self._version(definition, row) != precondition.observed_version:
                                await self._session.rollback()
                                raise StaleActionResourceError()
                            before = self._serialize(definition, row)
                            for name, value in changes.items():
                                setattr(row, definition.field_map[name].attribute, value)
                            setattr(row, definition.version_attribute, precondition.observed_version + 1)
                            if hasattr(row, "updated_at"):
                                row.updated_at = now
                            after = self._serialize(definition, row)
                            before_rows.append(before)
                            after_rows.append(after)
                            await self._record_snapshot(
                                organization_id=proposal.organization_id,
                                resource_type=definition.resource_type,
                                resource_id=resource_id,
                                version=precondition.observed_version,
                                snapshot=before,
                            )
                            self._session.add(
                                WorkplaceMutationStepReceiptORM(
                                    id=uuid.uuid4().hex,
                                    mutation_plan_id=plan.id,
                                    step_index=index,
                                    resource_type=definition.resource_type,
                                    resource_id=resource_id,
                                    operation=operation,
                                    before_json=before,
                                    after_json=after,
                                    outcome="succeeded",
                                    completed_at=now,
                                )
                            )
                        plan.status = "succeeded"
                        await self._session.commit()
                        return AgentActionHandlerResult(
                            resource_type=f"{definition.resource_type}_batch",
                            resource_id=proposal.resource_id,
                            before={"resources": before_rows},
                            after={"resources": after_rows},
                        )

                    resource_id = proposal.arguments["resource_id"]
                    row = await self._row(definition, proposal.organization_id, resource_id)
                    if row is None or self._version(definition, row) != proposal.observed_resource_version:
                        raise StaleActionResourceError()
                    before = self._serialize(definition, row)
                    changes = {change.field: change.after for change in proposal.changes}
                    plan = await self._record_plan(
                        proposal=proposal,
                        operation=operation,
                        resources=[{"resource_type": definition.resource_type, "resource_id": resource_id}],
                    )
                    await self._record_snapshot(
                        organization_id=proposal.organization_id,
                        resource_type=definition.resource_type,
                        resource_id=resource_id,
                        version=proposal.observed_resource_version,
                        snapshot=before,
                    )
                    for name, value in changes.items():
                        policy = definition.field_map[name]
                        setattr(row, policy.attribute, value)
                    if definition.version_attribute:
                        setattr(row, definition.version_attribute, proposal.observed_resource_version + 1)
                    if hasattr(row, "updated_at"):
                        row.updated_at = now
                    after = self._serialize(definition, row)
                    if operation == "delete":
                        tombstone = await self._session.scalar(
                            select(WorkplaceResourceTombstoneORM).where(
                                WorkplaceResourceTombstoneORM.organization_id == proposal.organization_id,
                                WorkplaceResourceTombstoneORM.resource_type == definition.resource_type,
                                WorkplaceResourceTombstoneORM.resource_id == resource_id,
                            )
                        )
                        if tombstone is None:
                            tombstone = WorkplaceResourceTombstoneORM(
                                id=uuid.uuid4().hex,
                                organization_id=proposal.organization_id,
                                resource_type=definition.resource_type,
                                resource_id=resource_id,
                                version=proposal.observed_resource_version + 1,
                                snapshot_json=before,
                                deleted_by_user_id=proposal.requested_by_user_id,
                                deleted_at=now,
                                restored_at=None,
                            )
                            self._session.add(tombstone)
                        elif tombstone.restored_at is None:
                            await self._session.rollback()
                            raise StaleActionResourceError()
                        else:
                            tombstone.version = proposal.observed_resource_version + 1
                            tombstone.snapshot_json = before
                            tombstone.deleted_by_user_id = proposal.requested_by_user_id
                            tombstone.deleted_at = now
                            tombstone.restored_at = None
                    elif operation == "restore":
                        tombstone = await self._session.scalar(
                            select(WorkplaceResourceTombstoneORM).where(
                                WorkplaceResourceTombstoneORM.organization_id == proposal.organization_id,
                                WorkplaceResourceTombstoneORM.resource_type == definition.resource_type,
                                WorkplaceResourceTombstoneORM.resource_id == resource_id,
                                WorkplaceResourceTombstoneORM.restored_at.is_(None),
                            )
                        )
                        if tombstone is None:
                            await self._session.rollback()
                            raise StaleActionResourceError()
                        tombstone.restored_at = now
                    self._session.add(
                        WorkplaceMutationStepReceiptORM(
                            id=uuid.uuid4().hex,
                            mutation_plan_id=plan.id,
                            step_index=0,
                            resource_type=definition.resource_type,
                            resource_id=resource_id,
                            operation=operation,
                            before_json=before,
                            after_json=after,
                            outcome="succeeded",
                            completed_at=now,
                        )
                    )
                    plan.status = "succeeded"
                    await self._session.commit()
                    return AgentActionHandlerResult(
                        resource_type=definition.resource_type,
                        resource_id=resource_id,
                        before=before,
                        after=after,
                    )

                async def reconcile(
                    self,
                    *,
                    proposal: AgentActionProposal,
                    operation: str,
                ) -> AgentActionHandlerResult | None:
                    definition = self._registry.get(proposal.arguments["resource_type"])
                    if operation == "create":
                        values = self._parse_json_object(proposal.arguments["values_json"], field_name="values_json")
                        row = await self._session.scalar(
                            select(WorkplaceSettingORM).where(
                                WorkplaceSettingORM.organization_id == proposal.organization_id,
                                WorkplaceSettingORM.namespace == values["namespace"],
                                WorkplaceSettingORM.setting_key == values["key"],
                            )
                        )
                        if row is None:
                            return None
                        after = self._serialize(definition, row)
                        if after.get("value") != values.get("value") or after.get("description") != values.get("description"):
                            return None
                        return AgentActionHandlerResult(
                            resource_type=definition.resource_type,
                            resource_id=row.id,
                            before={},
                            after=after,
                        )
                    if operation == "bulk_update":
                        ids = [str(item) for item in self._parse_json_list(proposal.arguments["resource_ids_json"], field_name="resource_ids_json")]
                        expected = self._parse_json_object(proposal.arguments["changes_json"], field_name="changes_json")
                        rows = []
                        for resource_id in ids:
                            current = await self.get(
                                organization_id=proposal.organization_id,
                                resource_type=definition.resource_type,
                                resource_id=resource_id,
                            )
                            if current is None or any(current.get(name) != _canonical(value) for name, value in expected.items()):
                                return None
                            rows.append(current)
                        return AgentActionHandlerResult(
                            resource_type=f"{definition.resource_type}_batch",
                            resource_id=proposal.resource_id,
                            before={"resources": proposal.changes[0].before},
                            after={"resources": rows},
                        )
                    current = await self.get(
                        organization_id=proposal.organization_id,
                        resource_type=definition.resource_type,
                        resource_id=proposal.arguments["resource_id"],
                    )
                    if current is None:
                        return None
                    if any(current.get(change.field) != change.after for change in proposal.changes):
                        return None
                    return AgentActionHandlerResult(
                        resource_type=definition.resource_type,
                        resource_id=proposal.arguments["resource_id"],
                        before={change.field: change.before for change in proposal.changes},
                        after=current,
                    )
            '''
        ),
    )


def add_action_handlers(root: Path) -> None:
    create_exact(
        root,
        "app/agent/workplace_resource_handlers.py",
        block(
            '''
            from __future__ import annotations

            from app.agent.action_contracts import (
                AgentActionExecutionResult,
                AgentActionHandlerResult,
                AgentActionPreparation,
                AgentActionProposal,
            )
            from app.workplace_resources.service import WorkplaceResourceService


            class WorkplaceResourceActionHandler:
                def __init__(
                    self,
                    service: WorkplaceResourceService,
                    operation: str,
                ) -> None:
                    self._service = service
                    self._operation = operation

                async def prepare(
                    self,
                    *,
                    organization_id: str,
                    arguments: dict[str, str],
                ) -> AgentActionPreparation:
                    return await self._service.prepare(
                        organization_id=organization_id,
                        operation=self._operation,
                        arguments=arguments,
                    )

                async def execute(
                    self,
                    *,
                    proposal: AgentActionProposal,
                ) -> AgentActionHandlerResult:
                    return await self._service.execute(
                        proposal=proposal,
                        operation=self._operation,
                    )

                async def reconcile(
                    self,
                    *,
                    proposal: AgentActionProposal,
                    execution: AgentActionExecutionResult,
                ) -> AgentActionHandlerResult | None:
                    return await self._service.reconcile(
                        proposal=proposal,
                        operation=self._operation,
                    )
            '''
        ),
    )


def add_schemas_and_routes(root: Path) -> None:
    create_exact(
        root,
        "app/workplace_resources/errors.py",
        block(
            '''
            from __future__ import annotations

            from fastapi import status

            from app.core.errors import AppError


            class WorkplaceResourceInvalidError(AppError):
                code = "workplace_resource_invalid"
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
                message = "Workplace resource request is invalid."


            class WorkplaceResourceNotFoundError(AppError):
                code = "workplace_resource_not_found"
                status_code = status.HTTP_404_NOT_FOUND
                message = "Workplace resource was not found."
            '''
        ),
    )
    create_exact(
        root,
        "app/schemas/workplace_resources.py",
        block(
            '''
            from __future__ import annotations

            from typing import Any

            from pydantic import BaseModel, ConfigDict, Field, field_validator


            class WorkplaceResourceTypeListResponse(BaseModel):
                resources: tuple[dict[str, Any], ...]


            class WorkplaceResourceSchemaResponse(BaseModel):
                resource: dict[str, Any]


            class WorkplaceResourceSearchResponse(BaseModel):
                items: tuple[dict[str, Any], ...]
                total: int = Field(ge=0)
                limit: int = Field(ge=1, le=100)
                offset: int = Field(ge=0)


            class WorkplaceResourceCountResponse(BaseModel):
                count: int = Field(ge=0)


            class WorkplaceResourceResponse(BaseModel):
                item: dict[str, Any]


            class WorkplaceResourceSearchRequest(BaseModel):
                model_config = ConfigDict(extra="forbid")

                filters: dict[str, Any] = Field(default_factory=dict, max_length=20)
                sort_by: str | None = Field(default=None, max_length=100)
                descending: bool = False
                limit: int = Field(default=50, ge=1, le=100)
                offset: int = Field(default=0, ge=0)

                @field_validator("filters")
                @classmethod
                def validate_filter_names(cls, value: dict[str, Any]) -> dict[str, Any]:
                    for name in value:
                        if not name or len(name) > 100:
                            raise ValueError("Resource filter name is invalid")
                    return value
            '''
        ),
    )

    create_exact(
        root,
        "app/api/workplace_resource_routes.py",
        block(
            '''
            from __future__ import annotations

            from fastapi import APIRouter

            from app.api.dependencies import SessionDep, UserDep
            from app.domain.enums import Permission
            from app.permissions.permission_service import PermissionService
            from app.repositories.user_repository import UserRepository
            from app.schemas.workplace_resources import (
                WorkplaceResourceCountResponse,
                WorkplaceResourceResponse,
                WorkplaceResourceSchemaResponse,
                WorkplaceResourceSearchRequest,
                WorkplaceResourceSearchResponse,
                WorkplaceResourceTypeListResponse,
            )
            from app.workplace_resources.errors import (
                WorkplaceResourceInvalidError,
                WorkplaceResourceNotFoundError,
            )
            from app.workplace_resources.registry import WorkplaceResourceRegistry
            from app.workplace_resources.service import WorkplaceResourceService

            router = APIRouter(
                prefix="/workplace/organizations/{organization_id}/resources",
                tags=["workplace-resources"],
            )


            async def _authorize(
                *,
                session: SessionDep,
                user: UserDep,
                organization_id: str,
            ) -> None:
                await PermissionService(UserRepository(session)).authorize(
                    user=user,
                    organization_id=organization_id,
                    required_permission=Permission.WORKPLACE_RESOURCES_READ.value,
                )


            @router.get("", response_model=WorkplaceResourceTypeListResponse)
            async def list_resource_types(
                organization_id: str,
                session: SessionDep,
                user: UserDep,
            ) -> WorkplaceResourceTypeListResponse:
                await _authorize(
                    session=session,
                    user=user,
                    organization_id=organization_id,
                )
                service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
                return WorkplaceResourceTypeListResponse(
                    resources=service.list_resource_types()
                )


            @router.get(
                "/{resource_type}/schema",
                response_model=WorkplaceResourceSchemaResponse,
            )
            async def describe_resource(
                organization_id: str,
                resource_type: str,
                session: SessionDep,
                user: UserDep,
            ) -> WorkplaceResourceSchemaResponse:
                await _authorize(
                    session=session,
                    user=user,
                    organization_id=organization_id,
                )
                service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
                try:
                    resource = service.describe(resource_type)
                except ValueError as exception:
                    raise WorkplaceResourceInvalidError(str(exception)) from exception
                return WorkplaceResourceSchemaResponse(resource=resource)


            @router.post(
                "/{resource_type}/search",
                response_model=WorkplaceResourceSearchResponse,
            )
            async def search_resources(
                organization_id: str,
                resource_type: str,
                request: WorkplaceResourceSearchRequest,
                session: SessionDep,
                user: UserDep,
            ) -> WorkplaceResourceSearchResponse:
                await _authorize(
                    session=session,
                    user=user,
                    organization_id=organization_id,
                )
                service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
                try:
                    items, total = await service.search(
                        organization_id=organization_id,
                        resource_type=resource_type,
                        filters=request.filters,
                        sort_by=request.sort_by,
                        descending=request.descending,
                        limit=request.limit,
                        offset=request.offset,
                    )
                except ValueError as exception:
                    raise WorkplaceResourceInvalidError(str(exception)) from exception
                return WorkplaceResourceSearchResponse(
                    items=items,
                    total=total,
                    limit=request.limit,
                    offset=request.offset,
                )


            @router.post(
                "/{resource_type}/count",
                response_model=WorkplaceResourceCountResponse,
            )
            async def count_resources(
                organization_id: str,
                resource_type: str,
                request: WorkplaceResourceSearchRequest,
                session: SessionDep,
                user: UserDep,
            ) -> WorkplaceResourceCountResponse:
                await _authorize(
                    session=session,
                    user=user,
                    organization_id=organization_id,
                )
                service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
                try:
                    _, total = await service.search(
                        organization_id=organization_id,
                        resource_type=resource_type,
                        filters=request.filters,
                        sort_by=None,
                        descending=False,
                        limit=1,
                        offset=0,
                    )
                except ValueError as exception:
                    raise WorkplaceResourceInvalidError(str(exception)) from exception
                return WorkplaceResourceCountResponse(count=total)


            @router.get(
                "/{resource_type}/{resource_id}",
                response_model=WorkplaceResourceResponse,
            )
            async def get_resource(
                organization_id: str,
                resource_type: str,
                resource_id: str,
                session: SessionDep,
                user: UserDep,
            ) -> WorkplaceResourceResponse:
                await _authorize(
                    session=session,
                    user=user,
                    organization_id=organization_id,
                )
                service = WorkplaceResourceService(session, WorkplaceResourceRegistry())
                try:
                    item = await service.get(
                        organization_id=organization_id,
                        resource_type=resource_type,
                        resource_id=resource_id,
                    )
                except ValueError as exception:
                    raise WorkplaceResourceInvalidError(str(exception)) from exception
                if item is None:
                    raise WorkplaceResourceNotFoundError()
                return WorkplaceResourceResponse(item=item)
            '''
        ),
    )


def add_migration(root: Path) -> None:
    create_exact(
        root,
        "alembic/versions/0014_workplace_resources.py",
        block(
            '''
            """add governed workplace resource runtime

            Revision ID: 0014_workplace_resources
            Revises: 0013_nucleus_admin
            Create Date: 2026-07-18
            """

            from __future__ import annotations

            from typing import Sequence, Union

            import sqlalchemy as sa
            from alembic import op

            revision: str = "0014_workplace_resources"
            down_revision: Union[str, None] = "0013_nucleus_admin"
            branch_labels: Union[str, Sequence[str], None] = None
            depends_on: Union[str, Sequence[str], None] = None


            def upgrade() -> None:
                op.create_table(
                    "workplace_settings",
                    sa.Column("id", sa.String(), nullable=False),
                    sa.Column("organization_id", sa.String(), nullable=False),
                    sa.Column("namespace", sa.String(length=80), nullable=False),
                    sa.Column("setting_key", sa.String(length=120), nullable=False),
                    sa.Column("value_json", sa.JSON(), nullable=True),
                    sa.Column("description", sa.String(length=500), nullable=True),
                    sa.Column("is_active", sa.Boolean(), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ["organization_id"], ["organizations.id"], ondelete="CASCADE"
                    ),
                    sa.PrimaryKeyConstraint("id"),
                    sa.UniqueConstraint(
                        "organization_id",
                        "namespace",
                        "setting_key",
                        name="uq_workplace_setting_org_namespace_key",
                    ),
                )
                op.create_index(
                    "ix_workplace_setting_org_active",
                    "workplace_settings",
                    ["organization_id", "is_active"],
                    unique=False,
                )
                op.create_index(
                    "ix_workplace_settings_organization_id",
                    "workplace_settings",
                    ["organization_id"],
                    unique=False,
                )
                op.create_table(
                    "workplace_resource_snapshots",
                    sa.Column("id", sa.String(), nullable=False),
                    sa.Column("organization_id", sa.String(), nullable=False),
                    sa.Column("resource_type", sa.String(length=120), nullable=False),
                    sa.Column("resource_id", sa.String(length=250), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("snapshot_hash", sa.String(length=64), nullable=False),
                    sa.Column("snapshot_json", sa.JSON(), nullable=False),
                    sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
                    sa.PrimaryKeyConstraint("id"),
                )
                op.create_index(
                    "ix_workplace_snapshot_resource",
                    "workplace_resource_snapshots",
                    ["organization_id", "resource_type", "resource_id"],
                    unique=False,
                )
                op.create_table(
                    "workplace_mutation_plans",
                    sa.Column("id", sa.String(), nullable=False),
                    sa.Column("proposal_id", sa.String(), nullable=False),
                    sa.Column("organization_id", sa.String(), nullable=False),
                    sa.Column("operation_type", sa.String(length=80), nullable=False),
                    sa.Column("resource_count", sa.Integer(), nullable=False),
                    sa.Column("plan_json", sa.JSON(), nullable=False),
                    sa.Column("status", sa.String(length=40), nullable=False),
                    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
                    sa.ForeignKeyConstraint(
                        ["proposal_id"], ["agent_action_proposals.id"], ondelete="CASCADE"
                    ),
                    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
                    sa.PrimaryKeyConstraint("id"),
                    sa.UniqueConstraint("proposal_id", name="uq_workplace_plan_proposal"),
                )
                op.create_table(
                    "workplace_mutation_step_receipts",
                    sa.Column("id", sa.String(), nullable=False),
                    sa.Column("mutation_plan_id", sa.String(), nullable=False),
                    sa.Column("step_index", sa.Integer(), nullable=False),
                    sa.Column("resource_type", sa.String(length=120), nullable=False),
                    sa.Column("resource_id", sa.String(length=250), nullable=False),
                    sa.Column("operation", sa.String(length=80), nullable=False),
                    sa.Column("before_json", sa.JSON(), nullable=True),
                    sa.Column("after_json", sa.JSON(), nullable=True),
                    sa.Column("outcome", sa.String(length=40), nullable=False),
                    sa.Column("error_code", sa.String(length=120), nullable=True),
                    sa.Column("attempt_count", sa.Integer(), nullable=False),
                    sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
                    sa.ForeignKeyConstraint(
                        ["mutation_plan_id"],
                        ["workplace_mutation_plans.id"],
                        ondelete="CASCADE",
                    ),
                    sa.PrimaryKeyConstraint("id"),
                    sa.UniqueConstraint(
                        "mutation_plan_id",
                        "step_index",
                        name="uq_workplace_plan_step",
                    ),
                )
                op.create_table(
                    "workplace_resource_tombstones",
                    sa.Column("id", sa.String(), nullable=False),
                    sa.Column("organization_id", sa.String(), nullable=False),
                    sa.Column("resource_type", sa.String(length=120), nullable=False),
                    sa.Column("resource_id", sa.String(length=250), nullable=False),
                    sa.Column("version", sa.Integer(), nullable=False),
                    sa.Column("snapshot_json", sa.JSON(), nullable=False),
                    sa.Column("deleted_by_user_id", sa.String(), nullable=False),
                    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
                    sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
                    sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
                    sa.ForeignKeyConstraint(["deleted_by_user_id"], ["users.id"]),
                    sa.PrimaryKeyConstraint("id"),
                    sa.UniqueConstraint(
                        "organization_id",
                        "resource_type",
                        "resource_id",
                        name="uq_workplace_resource_tombstone",
                    ),
                )


            def downgrade() -> None:
                op.drop_table("workplace_resource_tombstones")
                op.drop_table("workplace_mutation_step_receipts")
                op.drop_table("workplace_mutation_plans")
                op.drop_index(
                    "ix_workplace_snapshot_resource",
                    table_name="workplace_resource_snapshots",
                )
                op.drop_table("workplace_resource_snapshots")
                op.drop_index(
                    "ix_workplace_settings_organization_id",
                    table_name="workplace_settings",
                )
                op.drop_index(
                    "ix_workplace_setting_org_active",
                    table_name="workplace_settings",
                )
                op.drop_table("workplace_settings")
            '''
        ),
    )


def patch_permissions(root: Path) -> None:
    path = "app/domain/enums.py"
    replace_exact(
        root,
        path,
        '    ORGANIZATION_REPORTS_REVOKE = "organization.reports.revoke"\n\n'
        '    AGENT_ACTIONS_READ = "agent.actions.read"\n',
        '    ORGANIZATION_REPORTS_REVOKE = "organization.reports.revoke"\n\n'
        '    WORKPLACE_RESOURCES_READ = "workplace.resources.read"\n'
        '    WORKPLACE_RESOURCES_CREATE = "workplace.resources.create"\n'
        '    WORKPLACE_RESOURCES_UPDATE = "workplace.resources.update"\n'
        '    WORKPLACE_RESOURCES_DELETE = "workplace.resources.delete"\n'
        '    WORKPLACE_RESOURCES_RESTORE = "workplace.resources.restore"\n'
        '    WORKPLACE_RESOURCES_BULK_MANAGE = "workplace.resources.bulk_manage"\n\n'
        '    AGENT_ACTIONS_READ = "agent.actions.read"\n',
    )
    replace_exact(
        root,
        path,
        '    Permission.ORGANIZATION_REPORTS_READ,\n'
        '    Permission.AUDIT_READ,\n',
        '    Permission.ORGANIZATION_REPORTS_READ,\n'
        '    Permission.WORKPLACE_RESOURCES_READ,\n'
        '    Permission.AUDIT_READ,\n',
    )
    replace_exact(
        root,
        path,
        '    Permission.ORGANIZATION_REPORTS_REVOKE,\n'
        '    Permission.AGENT_ACTIONS_READ,\n',
        '    Permission.ORGANIZATION_REPORTS_REVOKE,\n'
        '    Permission.WORKPLACE_RESOURCES_CREATE,\n'
        '    Permission.WORKPLACE_RESOURCES_UPDATE,\n'
        '    Permission.WORKPLACE_RESOURCES_DELETE,\n'
        '    Permission.WORKPLACE_RESOURCES_RESTORE,\n'
        '    Permission.WORKPLACE_RESOURCES_BULK_MANAGE,\n'
        '    Permission.AGENT_ACTIONS_READ,\n',
    )


def patch_action_registry(root: Path) -> None:
    path = "app/agent/action_registry.py"
    marker = '''                self._definition(
                    name="invite_organization_user",
'''
    addition = indent(block(
        '''
                        self._definition(
                            name="create_workplace_resource",
                            description="Create one backend-registered workplace resource after schema and uniqueness validation.",
                            arguments=("resource_type", "values_json"),
                            permission=Permission.WORKPLACE_RESOURCES_CREATE,
                            resource_type="workplace_resource",
                            risk_level="medium",
                        ),
                        self._definition(
                            name="update_workplace_resource",
                            description="Update only allowlisted fields on one registered workplace resource.",
                            arguments=("resource_type", "resource_id", "changes_json"),
                            permission=Permission.WORKPLACE_RESOURCES_UPDATE,
                            resource_type="workplace_resource",
                            risk_level="medium",
                        ),
                        self._definition(
                            name="clear_workplace_resource_fields",
                            description="Clear only nullable fields explicitly marked clearable by the resource registry.",
                            arguments=("resource_type", "resource_id", "fields_json"),
                            permission=Permission.WORKPLACE_RESOURCES_UPDATE,
                            resource_type="workplace_resource",
                            risk_level="medium",
                        ),
                        self._definition(
                            name="activate_workplace_resource",
                            description="Activate one resource with a registered lifecycle policy.",
                            arguments=("resource_type", "resource_id"),
                            permission=Permission.WORKPLACE_RESOURCES_UPDATE,
                            resource_type="workplace_resource",
                            risk_level="medium",
                        ),
                        self._definition(
                            name="deactivate_workplace_resource",
                            description="Deactivate one resource without deleting its source row.",
                            arguments=("resource_type", "resource_id"),
                            permission=Permission.WORKPLACE_RESOURCES_UPDATE,
                            resource_type="workplace_resource",
                            risk_level="high",
                        ),
                        self._definition(
                            name="delete_workplace_resource",
                            description="Apply the registered delete policy and preserve an exact tombstone snapshot.",
                            arguments=("resource_type", "resource_id"),
                            permission=Permission.WORKPLACE_RESOURCES_DELETE,
                            resource_type="workplace_resource",
                            risk_level="high",
                        ),
                        self._definition(
                            name="restore_workplace_resource",
                            description="Restore a previously tombstoned resource when no newer conflict exists.",
                            arguments=("resource_type", "resource_id"),
                            permission=Permission.WORKPLACE_RESOURCES_RESTORE,
                            resource_type="workplace_resource",
                            risk_level="high",
                        ),
                        self._definition(
                            name="bulk_update_workplace_resources",
                            description="Update an exact frozen set of at most fifty registered resources.",
                            arguments=("resource_type", "resource_ids_json", "changes_json"),
                            permission=Permission.WORKPLACE_RESOURCES_BULK_MANAGE,
                            resource_type="workplace_resource_batch",
                            risk_level="high",
                        ),
        '''
    ), "                ")
    insert_before(root, path, marker, addition)


def patch_action_schema(root: Path) -> None:
    path = "app/schemas/agent_actions.py"
    insert_before(
        root,
        path,
        '    "invite_organization_user",\n',
        '    "create_workplace_resource",\n'
        '    "update_workplace_resource",\n'
        '    "clear_workplace_resource_fields",\n'
        '    "activate_workplace_resource",\n'
        '    "deactivate_workplace_resource",\n'
        '    "delete_workplace_resource",\n'
        '    "restore_workplace_resource",\n'
        '    "bulk_update_workplace_resources",\n',
    )
    replace_exact(
        root,
        path,
        '                or len(normalized_value) > 500\n',
        '                or len(normalized_value) > 5000\n',
    )


def patch_action_dependencies(root: Path) -> None:
    path = "app/api/action_dependencies.py"
    replace_exact(
        root,
        path,
        'from app.agent.action_registry import AgentActionRegistry\n',
        'from app.agent.action_registry import AgentActionRegistry\n'
        'from app.agent.workplace_resource_handlers import WorkplaceResourceActionHandler\n',
    )
    replace_exact(
        root,
        path,
        'from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService\n',
        'from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService\n'
        'from app.workplace_resources.registry import WorkplaceResourceRegistry\n'
        'from app.workplace_resources.service import WorkplaceResourceService\n',
    )
    replace_exact(
        root,
        path,
        '    nucleus_projections = NucleusAdministrationProjectionRepository(session)\n'
        '    return {\n',
        '    nucleus_projections = NucleusAdministrationProjectionRepository(session)\n'
        '    workplace_resources = WorkplaceResourceService(\n'
        '        session, WorkplaceResourceRegistry()\n'
        '    )\n'
        '    return {\n',
    )
    insert_before(
        root,
        path,
        '        "invite_organization_user": InviteOrganizationUserHandler(resources),\n',
        '        "create_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "create"),\n'
        '        "update_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "update"),\n'
        '        "clear_workplace_resource_fields": WorkplaceResourceActionHandler(workplace_resources, "clear"),\n'
        '        "activate_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "activate"),\n'
        '        "deactivate_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "deactivate"),\n'
        '        "delete_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "delete"),\n'
        '        "restore_workplace_resource": WorkplaceResourceActionHandler(workplace_resources, "restore"),\n'
        '        "bulk_update_workplace_resources": WorkplaceResourceActionHandler(workplace_resources, "bulk_update"),\n',
    )


def patch_application(root: Path) -> None:
    replace_exact(
        root,
        "app/core/errors.py",
        '        "agent_action_rollback_unavailable",\n'
        '        "internal_error",\n',
        '        "agent_action_rollback_unavailable",\n'
        '        "workplace_resource_invalid",\n'
        '        "workplace_resource_not_found",\n'
        '        "internal_error",\n',
    )
    replace_exact(
        root,
        "alembic/env.py",
        'from app.db import action_models, nucleus_admin_models, nucleus_models, orm_models  # noqa: F401\n',
        'from app.db import (  # noqa: F401\n'
        '    action_models,\n'
        '    nucleus_admin_models,\n'
        '    nucleus_models,\n'
        '    orm_models,\n'
        '    workplace_resource_models,\n'
        ')\n',
    )
    replace_exact(
        root,
        "app/main.py",
        'from app.api import action_routes, agent_routes, health_routes, nucleus_routes, workplace_routes\n',
        'from app.api import (\n'
        '    action_routes,\n'
        '    agent_routes,\n'
        '    health_routes,\n'
        '    nucleus_routes,\n'
        '    workplace_resource_routes,\n'
        '    workplace_routes,\n'
        ')\n',
    )
    replace_exact(
        root,
        "app/main.py",
        '    application.include_router(nucleus_routes.router)\n'
        '    application.include_router(agent_routes.router)\n',
        '    application.include_router(nucleus_routes.router)\n'
        '    application.include_router(workplace_resource_routes.router)\n'
        '    application.include_router(agent_routes.router)\n',
    )


def patch_capabilities(root: Path) -> None:
    path = "app/schemas/organization.py"
    replace_exact(
        root,
        path,
        '            "get_organization_audit_log",\n',
        '            "get_organization_audit_log",\n'
        '            "list_workplace_resource_types",\n'
        '            "describe_workplace_resource",\n'
        '            "search_workplace_resources",\n'
        '            "get_workplace_resource",\n'
        '            "count_workplace_resources",\n',
    )


def patch_execution_context(root: Path) -> None:
    replace_exact(
        root,
        "app/agent/nucleus_admin_action_handlers.py",
        "    requires_execution_context = True\n",
        "    requires_execution_context = True\n"
        "    requires_nucleus_actor = True\n",
        expected_count=5,
    )
    path = "app/services/agent_action_service.py"
    replace_exact(
        root,
        path,
        '        if getattr(handler, "requires_execution_context", False):\n'
        '            nucleus_actor_id = (\n',
        '        if getattr(handler, "requires_nucleus_actor", False):\n'
        '            nucleus_actor_id = (\n',
        expected_count=1,
    )


def patch_generic_handler_context(root: Path) -> None:
    path = "app/agent/workplace_resource_handlers.py"
    replace_exact(
        root,
        path,
        "class WorkplaceResourceActionHandler:\n"
        "    def __init__(\n",
        "class WorkplaceResourceActionHandler:\n"
        "    requires_execution_context = True\n\n"
        "    def __init__(\n",
    )
    replace_exact(
        root,
        path,
        "    async def execute(\n"
        "        self,\n"
        "        *,\n"
        "        proposal: AgentActionProposal,\n"
        "    ) -> AgentActionHandlerResult:\n"
        "        return await self._service.execute(\n"
        "            proposal=proposal,\n"
        "            operation=self._operation,\n"
        "        )\n",
        "    async def execute(\n"
        "        self,\n"
        "        *,\n"
        "        proposal: AgentActionProposal,\n"
        "        context,\n"
        "    ) -> AgentActionHandlerResult:\n"
        "        return await self._service.execute(\n"
        "            proposal=proposal,\n"
        "            operation=self._operation,\n"
        "            executor_user_id=context.executed_by_user_id,\n"
        "        )\n",
    )
    replace_exact(
        root,
        path,
        "        execution: AgentActionExecutionResult,\n"
        "    ) -> AgentActionHandlerResult | None:\n",
        "        execution: AgentActionExecutionResult,\n"
        "        context,\n"
        "    ) -> AgentActionHandlerResult | None:\n",
    )
    path = "app/workplace_resources/service.py"
    replace_exact(
        root,
        path,
        "        proposal: AgentActionProposal,\n"
        "        operation: str,\n"
        "    ) -> AgentActionHandlerResult:\n",
        "        proposal: AgentActionProposal,\n"
        "        operation: str,\n"
        "        executor_user_id: str,\n"
        "    ) -> AgentActionHandlerResult:\n",
        expected_count=1,
    )
    replace_exact(
        root,
        path,
        "                deleted_by_user_id=proposal.requested_by_user_id,\n",
        "                deleted_by_user_id=executor_user_id,\n",
    )


def patch_health(root: Path) -> None:
    path = "app/api/health_routes.py"
    replace_exact(
        root,
        path,
        'EXPECTED_MIGRATION_HEAD = "0013_nucleus_admin"\n',
        'EXPECTED_MIGRATION_HEAD = "0014_workplace_resources"\n',
    )
    insert_before(
        root,
        path,
        '    registry_names = {\n',
        indent(block(
            '''
                try:
                    await session.execute(
                        text(
                            "SELECT id, organization_id, namespace, setting_key, "
                            "version FROM workplace_settings LIMIT 1"
                        )
                    )
                    await session.execute(
                        text(
                            "SELECT proposal_id, plan_json, status "
                            "FROM workplace_mutation_plans LIMIT 1"
                        )
                    )
                    await session.execute(
                        text(
                            "SELECT resource_type, resource_id, snapshot_hash "
                            "FROM workplace_resource_snapshots LIMIT 1"
                        )
                    )
                    workplace_resource_runtime_supported = True
                except SQLAlchemyError:
                    await session.rollback()
                    workplace_resource_runtime_supported = False

            '''
        ), "    "),
    )
    insert_before(
        root,
        path,
        '    audit_pending = int(\n',
        indent(block(
            '''
                workplace_resource_permissions = {
                    Permission.WORKPLACE_RESOURCES_CREATE.value,
                    Permission.WORKPLACE_RESOURCES_UPDATE.value,
                    Permission.WORKPLACE_RESOURCES_DELETE.value,
                    Permission.WORKPLACE_RESOURCES_RESTORE.value,
                    Permission.WORKPLACE_RESOURCES_BULK_MANAGE.value,
                }
                configured_workplace_resource_permissions = set(
                    (
                        await session.execute(
                            select(RolePermissionORM.permission).where(
                                RolePermissionORM.role == Role.SANDBOX_ADMIN.value,
                                RolePermissionORM.permission.in_(
                                    workplace_resource_permissions
                                ),
                            )
                        )
                    ).scalars().all()
                )

            '''
        ), "    "),
    )
    replace_exact(
        root,
        path,
        '        "nucleus_admin_sidecars_supported": nucleus_admin_sidecars_supported,\n'
        '        "nucleus_admin_permissions_seeded": (\n',
        '        "nucleus_admin_sidecars_supported": nucleus_admin_sidecars_supported,\n'
        '        "workplace_resource_runtime_supported": (\n'
        '            workplace_resource_runtime_supported\n'
        '        ),\n'
        '        "workplace_resource_permissions_seeded": (\n'
        '            configured_workplace_resource_permissions\n'
        '            == workplace_resource_permissions\n'
        '        ),\n'
        '        "nucleus_admin_permissions_seeded": (\n',
    )


def patch_existing_tests(root: Path) -> None:
    replace_exact(
        root,
        "tests/test_action_policy_discovery.py",
        "    assert len(actions) == 30\n",
        "    assert len(actions) == 38\n",
    )
    insert_before(
        root,
        "tests/test_action_policy_discovery.py",
        '    assert actions["update_organization_contact_email"]["minimum_approvals"] == 1\n',
        '    assert actions["create_workplace_resource"]["minimum_approvals"] == 1\n'
        '    assert actions["delete_workplace_resource"]["minimum_approvals"] == 2\n'
        '    assert actions["bulk_update_workplace_resources"]["self_approval_allowed"] is False\n',
    )
    path = "tests/test_operational_hardening.py"
    replace_exact(
        root,
        path,
        '    assert body["checks"]["nucleus_admin_permissions_seeded"] is True\n'
        '    assert body["checks"]["action_management_permissions_seeded"] is True\n'
        '    assert body["migration"]["expected"] == "0013_nucleus_admin"\n'
        '    assert body["actions"] == {"registered": 30, "handlers": 30}\n',
        '    assert body["checks"]["nucleus_admin_permissions_seeded"] is True\n'
        '    assert body["checks"]["workplace_resource_runtime_supported"] is True\n'
        '    assert body["checks"]["workplace_resource_permissions_seeded"] is True\n'
        '    assert body["checks"]["action_management_permissions_seeded"] is True\n'
        '    assert body["migration"]["expected"] == "0014_workplace_resources"\n'
        '    assert body["actions"] == {"registered": 38, "handlers": 38}\n',
    )
    replace_exact(
        root,
        "tests/test_migrations.py",
        'EXPECTED_HEAD = "0013_nucleus_admin"\n',
        'EXPECTED_HEAD = "0014_workplace_resources"\n',
    )


def add_tests(root: Path) -> None:
    create_exact(
        root,
        "tests/test_workplace_resource_registry.py",
        block(
            '''
            from __future__ import annotations

            from app.workplace_resources.registry import WorkplaceResourceRegistry


            def test_registry_is_unique_validated_and_secret_free() -> None:
                registry = WorkplaceResourceRegistry()
                definitions = registry.list_definitions()
                names = [definition.resource_type for definition in definitions]
                assert len(names) == len(set(names))
                assert "workplace_setting" in names
                assert "organization" in names
                assert "nucleus_organization_account" in names
                for definition in definitions:
                    for field in definition.fields:
                        assert not (field.sensitive and field.readable)
                        assert "password" not in field.name.lower()


            def test_setting_has_full_governed_lifecycle() -> None:
                definition = WorkplaceResourceRegistry().get("workplace_setting")
                assert definition.operations == {
                    "read",
                    "search",
                    "create",
                    "update",
                    "clear",
                    "activate",
                    "deactivate",
                    "delete",
                    "restore",
                    "bulk_update",
                }
                assert definition.field_map["value"].editable is True
                assert definition.field_map["description"].clearable is True
                assert definition.field_map["id"].editable is False
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_workplace_resource_reads.py",
        block(
            '''
            from __future__ import annotations

            from httpx import AsyncClient

            ORGANIZATION_ID = "org_sandbox_001"
            BASE = f"/workplace/organizations/{ORGANIZATION_ID}/resources"


            async def test_resource_discovery_and_schema_are_permission_scoped(
                client: AsyncClient,
                admin_headers: dict[str, str],
                reader_headers: dict[str, str],
            ) -> None:
                for headers in (admin_headers, reader_headers):
                    response = await client.get(BASE, headers=headers)
                    assert response.status_code == 200
                    resource_types = {
                        item["resource_type"]
                        for item in response.json()["resources"]
                    }
                    assert "organization" in resource_types
                    assert "workplace_setting" in resource_types

                schema = await client.get(
                    f"{BASE}/workplace_setting/schema",
                    headers=reader_headers,
                )
                assert schema.status_code == 200
                field_names = {
                    item["name"] for item in schema.json()["resource"]["fields"]
                }
                assert {"namespace", "key", "value", "description"}.issubset(
                    field_names
                )
                assert "password" not in field_names


            async def test_generic_search_enforces_scope_and_allowed_filters(
                client: AsyncClient,
                admin_headers: dict[str, str],
            ) -> None:
                response = await client.post(
                    f"{BASE}/organization/search",
                    headers=admin_headers,
                    json={
                        "filters": {"id": ORGANIZATION_ID},
                        "sort_by": "display_name",
                        "limit": 10,
                        "offset": 0,
                    },
                )
                assert response.status_code == 200, response.text
                body = response.json()
                assert body["total"] == 1
                assert body["items"][0]["id"] == ORGANIZATION_ID

                rejected = await client.post(
                    f"{BASE}/organization/search",
                    headers=admin_headers,
                    json={"filters": {"unknown_column": "value"}},
                )
                assert rejected.status_code in {400, 422}
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_workplace_resource_actions.py",
        block(
            '''
            from __future__ import annotations

            import json

            from httpx import AsyncClient
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.workplace_resource_models import (
                WorkplaceMutationPlanORM,
                WorkplaceResourceTombstoneORM,
                WorkplaceSettingORM,
            )

            ORGANIZATION_ID = "org_sandbox_001"
            ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"
            APPROVER_ONE = {"X-Mock-User-Id": "usr_approval_admin_001"}
            APPROVER_TWO = {"X-Mock-User-Id": "usr_approval_admin_002"}


            async def _propose(
                client: AsyncClient,
                headers: dict[str, str],
                action_name: str,
                arguments: dict[str, str],
            ) -> dict:
                response = await client.post(
                    f"{ACTION_BASE}/propose",
                    headers=headers,
                    json={"action_name": action_name, "arguments": arguments},
                )
                assert response.status_code == 200, response.text
                return response.json()["proposal"]


            async def _approve(
                client: AsyncClient,
                proposal: dict,
                admin_headers: dict[str, str],
            ) -> None:
                if proposal["approval_policy"]["minimum_approvals"] == 1:
                    headers_list = (admin_headers,)
                else:
                    headers_list = (APPROVER_ONE, APPROVER_TWO)
                for index, headers in enumerate(headers_list):
                    response = await client.post(
                        f"{ACTION_BASE}/{proposal['id']}/approve",
                        headers=headers,
                        json={"reason": f"Resource review {index + 1}"},
                    )
                    assert response.status_code == 200, response.text


            async def _execute(
                client: AsyncClient,
                proposal: dict,
                admin_headers: dict[str, str],
                key: str,
            ) -> dict:
                response = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": key},
                )
                assert response.status_code == 200, response.text
                return response.json()["execution"]


            async def test_setting_full_lifecycle_and_receipts(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                create = await _propose(
                    client,
                    admin_headers,
                    "create_workplace_resource",
                    {
                        "resource_type": "workplace_setting",
                        "values_json": json.dumps(
                            {
                                "namespace": "notifications",
                                "key": "daily_digest",
                                "value": {"enabled": True, "hour": 8},
                                "description": "Daily digest policy",
                            }
                        ),
                    },
                )
                await _approve(client, create, admin_headers)
                created_execution = await _execute(
                    client,
                    create,
                    admin_headers,
                    "create-workplace-setting-001",
                )
                setting_id = created_execution["result"]["resource_id"]

                setting = await db_session.get(WorkplaceSettingORM, setting_id)
                assert setting is not None
                assert setting.value_json == {"enabled": True, "hour": 8}

                update = await _propose(
                    client,
                    admin_headers,
                    "update_workplace_resource",
                    {
                        "resource_type": "workplace_setting",
                        "resource_id": setting_id,
                        "changes_json": json.dumps(
                            {"value": {"enabled": True, "hour": 9}}
                        ),
                    },
                )
                await _approve(client, update, admin_headers)
                await _execute(client, update, admin_headers, "update-workplace-setting-001")

                delete = await _propose(
                    client,
                    admin_headers,
                    "delete_workplace_resource",
                    {
                        "resource_type": "workplace_setting",
                        "resource_id": setting_id,
                    },
                )
                await _approve(client, delete, admin_headers)
                await _execute(client, delete, admin_headers, "delete-workplace-setting-001")
                await db_session.refresh(setting)
                assert setting.is_active is False
                tombstone = await db_session.scalar(
                    select(WorkplaceResourceTombstoneORM).where(
                        WorkplaceResourceTombstoneORM.resource_id == setting_id
                    )
                )
                assert tombstone is not None
                assert tombstone.deleted_by_user_id == "usr_admin_001"

                restore = await _propose(
                    client,
                    admin_headers,
                    "restore_workplace_resource",
                    {
                        "resource_type": "workplace_setting",
                        "resource_id": setting_id,
                    },
                )
                await _approve(client, restore, admin_headers)
                await _execute(client, restore, admin_headers, "restore-workplace-setting-001")
                await db_session.refresh(setting)
                assert setting.is_active is True
                await db_session.refresh(tombstone)
                assert tombstone.restored_at is not None

                plans = (
                    await db_session.execute(select(WorkplaceMutationPlanORM))
                ).scalars().all()
                assert len(plans) == 4
                assert all(plan.status == "succeeded" for plan in plans)


            async def test_protected_fields_and_cross_scope_are_rejected(
                client: AsyncClient,
                admin_headers: dict[str, str],
            ) -> None:
                protected = await client.post(
                    f"{ACTION_BASE}/propose",
                    headers=admin_headers,
                    json={
                        "action_name": "update_workplace_resource",
                        "arguments": {
                            "resource_type": "organization",
                            "resource_id": ORGANIZATION_ID,
                            "changes_json": json.dumps({"version": 99}),
                        },
                    },
                )
                assert protected.status_code == 422

                other_scope = await client.get(
                    f"/workplace/organizations/other-org/resources/organization/{ORGANIZATION_ID}",
                    headers=admin_headers,
                )
                assert other_scope.status_code in {403, 404, 422}
            '''
        ),
    )


def patch_documentation(root: Path) -> None:
    path = "README.md"
    replace_exact(
        root,
        path,
        "0013_nucleus_admin\n",
        "0014_workplace_resources\n",
        expected_count=1,
    )
    insert_before(
        root,
        path,
        "## Database and seed\n",
        block(
            '''
            ## Governed workplace-resource runtime

            The agent can now discover backend-registered internal resources, inspect
            their safe field schemas, search within organization scope, and propose
            controlled mutations without receiving raw SQL, arbitrary ORM access, table
            names, organization scope, actor identity, approval state, or database
            credentials. Generic writes are initially enabled for a fully governed
            `workplace_setting` resource and safe organization profile fields. Existing
            Nucleus, membership, seat, report-access, license and lifecycle operations
            continue to use their stronger dedicated handlers. Every generic mutation
            persists an immutable snapshot, mutation plan and step receipt; deletion is
            soft and tombstoned, and restoration requires a separately approved action.

            '''
        ),
    )

    path = "APPLY_AND_VALIDATE.md"
    replace_exact(
        root,
        path,
        "0013_nucleus_admin (head)",
        "0014_workplace_resources (head)",
    )
    replace_exact(root, path, "30 write actions", "38 write actions")
    replace_exact(
        root,
        path,
        "handler parity of 30/30.",
        "handler parity of 38/38, plus workplace-resource runtime and permission checks.",
    )
    replace_exact(
        root,
        path,
        'git commit -m "add Nucleus full administrative control"',
        'git commit -m "add governed workplace resource runtime"',
    )

    for path in ("docs/ARCHITECTURE.md", "docs/SECURITY_MODEL.md"):
        content = read_text(root, path)
        content += block(
            '''

            ## Governed workplace-resource runtime

            Internal resource discovery and mutation are driven by a backend registry
            that maps public business fields to exact ORM attributes, nullability,
            visibility, searchability and mutation policy. The model never supplies a
            physical table name, ORM attribute, organization scope, actor identity,
            permission, approval or SQL expression. Generic execution is limited to
            registered operations, freezes exact resource versions in the approved
            proposal, records immutable snapshots and per-step receipts, and uses
            reversible soft deletion with tombstones. Sensitive or cross-resource
            domains such as Nucleus identity, licensing, lifecycle, seats and access
            continue through dedicated handlers with stronger invariants.
            '''
        )
        write_text(root, path, content)


MODIFIED_PATHS = (
    "APPLY_AND_VALIDATE.md",
    "README.md",
    "alembic/env.py",
    "app/agent/action_registry.py",
    "app/agent/nucleus_admin_action_handlers.py",
    "app/api/action_dependencies.py",
    "app/api/health_routes.py",
    "app/core/errors.py",
    "app/domain/enums.py",
    "app/main.py",
    "app/schemas/agent_actions.py",
    "app/schemas/organization.py",
    "app/services/agent_action_service.py",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY_MODEL.md",
    "tests/test_action_policy_discovery.py",
    "tests/test_migrations.py",
    "tests/test_operational_hardening.py",
)

NEW_PATHS = (
    "alembic/versions/0014_workplace_resources.py",
    "app/agent/workplace_resource_handlers.py",
    "app/api/workplace_resource_routes.py",
    "app/db/workplace_resource_models.py",
    "app/schemas/workplace_resources.py",
    "app/workplace_resources/__init__.py",
    "app/workplace_resources/definitions.py",
    "app/workplace_resources/errors.py",
    "app/workplace_resources/registry.py",
    "app/workplace_resources/service.py",
    "tests/test_workplace_resource_actions.py",
    "tests/test_workplace_resource_reads.py",
    "tests/test_workplace_resource_registry.py",
)


def restore_after_failure(
    root: Path,
    backups: dict[str, str],
    new_path_existed: dict[str, bool],
) -> None:
    for relative_path, content in backups.items():
        write_text(root, relative_path, content)
    for relative_path, existed_before in new_path_existed.items():
        path = root / relative_path
        if not existed_before and path.exists():
            path.unlink()


def apply_patch(root: Path) -> None:
    validate_repository(root)
    backups = {path: read_text(root, path) for path in MODIFIED_PATHS}
    new_path_existed = {path: (root / path).exists() for path in NEW_PATHS}
    try:
        add_database_models(root)
        add_resource_runtime(root)
        add_resource_service(root)
        add_action_handlers(root)
        add_schemas_and_routes(root)
        add_migration(root)
        patch_permissions(root)
        patch_action_registry(root)
        patch_action_schema(root)
        patch_action_dependencies(root)
        patch_application(root)
        patch_capabilities(root)
        patch_execution_context(root)
        patch_generic_handler_context(root)
        patch_health(root)
        patch_existing_tests(root)
        add_tests(root)
        patch_documentation(root)
    except Exception:
        restore_after_failure(root, backups, new_path_existed)
        raise

    print("Applied governed workplace-resource runtime vertical slice.")
    print("No files were staged, committed, pushed, or deleted.")
    print("Existing Nucleus table definitions and dedicated handlers were preserved.")
    print("Untracked ZIP/download files were not touched.")
    print()
    print("Run exactly:")
    print("  python -m compileall -q app tests alembic")
    print("  git diff --check")
    print("  alembic upgrade head")
    print("  alembic current")
    print("  python -m app.db.seed")
    print("  python -m app.db.seed")
    print("  pytest -q")
    print("  git status --short")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args()
    try:
        apply_patch(args.repo.resolve())
    except PatchError as exception:
        print(f"PATCH FAILED: {exception}", file=sys.stderr)
        return 1
    except Exception as exception:
        print(f"PATCH FAILED: {type(exception).__name__}: {exception}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
