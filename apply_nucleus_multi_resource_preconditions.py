#!/usr/bin/env python3
"""Apply multi-resource action preconditions and Nucleus projection synchronization.

Baseline repository:
    shubham123dev/dem_0000_saa
Baseline commit:
    0c983a59ac9ece2f9f49fc2728f2898f17c0d6c3

The patch is fail-closed. It validates the exact baseline, refuses tracked local
changes, asserts each expected source transformation, restores all touched files
if application fails, and never stages, commits, pushes, or removes unrelated
untracked files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from textwrap import dedent, indent

BASELINE_COMMIT = "0c983a59ac9ece2f9f49fc2728f2898f17c0d6c3"


class PatchError(RuntimeError):
    """Raised when the checkout does not match the expected source state."""


def clean_block(value: str) -> str:
    return dedent(value).strip("\n") + "\n"


def indent_block(value: str, spaces: int) -> str:
    return indent(clean_block(value), " " * spaces)


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
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
        existing = path.read_text(encoding="utf-8")
        if existing == normalized:
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


def replace_section(
    root: Path,
    relative_path: str,
    start_marker: str,
    end_marker: str,
    replacement: str,
) -> None:
    text = read_text(root, relative_path)
    start = text.find(start_marker)
    if start < 0:
        raise PatchError(f"{relative_path}: start marker not found: {start_marker}")
    end = text.find(end_marker, start)
    if end < 0:
        raise PatchError(f"{relative_path}: end marker not found: {end_marker}")
    end += len(end_marker)
    write_text(root, relative_path, text[:start] + replacement + text[end:])


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


def replace_small_files(root: Path) -> None:
    write_text(
        root,
        "app/agent/action_contracts.py",
        clean_block(
            '''
            from __future__ import annotations

            from datetime import datetime
            from typing import Any, Literal, Protocol

            from pydantic import BaseModel, ConfigDict, Field, model_validator

            from app.domain.models import OrganizationOverview, OrganizationProfile


            class AgentApprovalPolicy(BaseModel):
                model_config = ConfigDict(frozen=True)

                self_approval_allowed: bool = True
                required_approver_permission: str
                minimum_approvals: int = Field(default=1, ge=1, le=10)


            class AgentActionDefinition(BaseModel):
                model_config = ConfigDict(frozen=True)

                name: str
                description: str
                required_argument_names: tuple[str, ...]
                required_permission: str
                resource_type: str
                risk_level: Literal["low", "medium", "high"]
                requires_approval: bool
                supports_dry_run: bool
                approval_policy: AgentApprovalPolicy


            class AgentActionProposalInput(BaseModel):
                model_config = ConfigDict(extra="forbid", frozen=True)

                action_name: str
                arguments: dict[str, str] = Field(default_factory=dict)


            class AgentActionChange(BaseModel):
                model_config = ConfigDict(frozen=True)

                field: str
                before: Any
                after: Any


            class AgentActionResourcePrecondition(BaseModel):
                """One immutable resource version reviewed by an approver."""

                model_config = ConfigDict(frozen=True)

                resource_type: str = Field(min_length=1, max_length=120)
                resource_id: str = Field(min_length=1, max_length=250)
                observed_version: int = Field(ge=0)


            def _canonical_resource_preconditions(
                *,
                resource_type: str,
                resource_id: str,
                observed_resource_version: int,
                resource_preconditions: tuple[AgentActionResourcePrecondition, ...],
            ) -> tuple[AgentActionResourcePrecondition, ...]:
                primary = AgentActionResourcePrecondition(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    observed_version=observed_resource_version,
                )
                by_key: dict[tuple[str, str], AgentActionResourcePrecondition] = {}
                for item in resource_preconditions:
                    key = (item.resource_type, item.resource_id)
                    previous = by_key.get(key)
                    if previous is not None and previous.observed_version != item.observed_version:
                        raise ValueError("Conflicting action resource preconditions")
                    by_key[key] = item

                primary_key = (primary.resource_type, primary.resource_id)
                previous_primary = by_key.get(primary_key)
                if (
                    previous_primary is not None
                    and previous_primary.observed_version != primary.observed_version
                ):
                    raise ValueError("Primary resource precondition does not match proposal")
                by_key[primary_key] = primary
                return tuple(
                    sorted(
                        by_key.values(),
                        key=lambda item: (item.resource_type, item.resource_id),
                    )
                )


            class AgentActionPreparation(BaseModel):
                model_config = ConfigDict(frozen=True)

                normalized_arguments: dict[str, str]
                changes: tuple[AgentActionChange, ...]
                observed_resource_version: int
                resource_type: str
                resource_id: str
                resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = ()

                @model_validator(mode="after")
                def normalize_resource_preconditions(self) -> "AgentActionPreparation":
                    normalized = _canonical_resource_preconditions(
                        resource_type=self.resource_type,
                        resource_id=self.resource_id,
                        observed_resource_version=self.observed_resource_version,
                        resource_preconditions=self.resource_preconditions,
                    )
                    if normalized != self.resource_preconditions:
                        object.__setattr__(self, "resource_preconditions", normalized)
                    return self


            class AgentActionHandlerResult(BaseModel):
                model_config = ConfigDict(frozen=True)

                resource_type: str
                resource_id: str
                before: dict[str, Any]
                after: dict[str, Any]
                external_operation_id: str | None = None


            class AgentActionProposal(BaseModel):
                model_config = ConfigDict(frozen=True)

                id: str
                organization_id: str
                requested_by_user_id: str
                action_name: str
                arguments: dict[str, str]
                action_fingerprint: str
                fingerprint_version: int = Field(default=2, ge=2, le=3)
                risk_level: Literal["low", "medium", "high"]
                resource_type: str
                resource_id: str
                status: Literal[
                    "pending_approval",
                    "approved",
                    "rejected",
                    "expired",
                    "cancelled",
                    "stale",
                    "executing",
                    "succeeded",
                    "failed",
                    "reconciliation_required",
                ]
                changes: tuple[AgentActionChange, ...]
                observed_resource_version: int
                resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = ()
                approval_policy: AgentApprovalPolicy
                expires_at: datetime
                cancelled_at: datetime | None = None
                stale_at: datetime | None = None
                created_at: datetime

                @model_validator(mode="after")
                def normalize_resource_preconditions(self) -> "AgentActionProposal":
                    normalized = _canonical_resource_preconditions(
                        resource_type=self.resource_type,
                        resource_id=self.resource_id,
                        observed_resource_version=self.observed_resource_version,
                        resource_preconditions=self.resource_preconditions,
                    )
                    if normalized != self.resource_preconditions:
                        object.__setattr__(self, "resource_preconditions", normalized)
                    return self


            class AgentActionApproval(BaseModel):
                model_config = ConfigDict(frozen=True)

                proposal_id: str
                decision: Literal["approved", "rejected"]
                decided_by_user_id: str
                decision_reason: str | None
                decided_at: datetime
                consumed_at: datetime | None


            class AgentActionExecutionResult(BaseModel):
                model_config = ConfigDict(frozen=True)

                proposal_id: str
                idempotency_key: str
                outcome: Literal[
                    "executing",
                    "succeeded",
                    "failed",
                    "reconciliation_required",
                ]
                result: dict[str, Any] | None
                error_code: str | None
                attempt_count: int = 1
                last_attempt_at: datetime | None = None
                provider_operation_id: str | None = None
                reconciliation_status: str | None = None
                audit_pending: bool = False
                started_at: datetime
                completed_at: datetime | None


            class AgentActionHandler(Protocol):
                async def prepare(
                    self,
                    *,
                    organization_id: str,
                    arguments: dict[str, str],
                ) -> AgentActionPreparation:
                    ...

                async def execute(
                    self,
                    *,
                    proposal: AgentActionProposal,
                ) -> AgentActionHandlerResult:
                    ...

                async def reconcile(
                    self,
                    *,
                    proposal: AgentActionProposal,
                    execution: AgentActionExecutionResult,
                ) -> AgentActionHandlerResult | None:
                    ...


            class VersionedOrganizationMutationGateway(Protocol):
                async def get_profile(self, organization_id: str) -> OrganizationProfile:
                    ...

                async def get_overview(self, organization_id: str) -> OrganizationOverview:
                    ...

                async def update_contact_email_if_version(
                    self,
                    organization_id: str,
                    contact_email: str | None,
                    expected_version: int,
                ) -> OrganizationProfile | None:
                    ...

                async def update_display_name_if_version(
                    self,
                    organization_id: str,
                    display_name: str,
                    expected_version: int,
                ) -> OrganizationProfile | None:
                    ...

                async def update_organization_type_if_version(
                    self,
                    organization_id: str,
                    organization_type: str,
                    expected_version: int,
                ) -> OrganizationOverview | None:
                    ...
            '''
        ),
    )

    write_text(
        root,
        "app/repositories/organization_repository.py",
        clean_block(
            '''
            """Organization repository: organization profile persistence."""

            from __future__ import annotations

            from datetime import datetime, timezone

            from sqlalchemy import update
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.orm_models import OrganizationORM
            from app.domain.enums import Environment, OrganizationStatus
            from app.domain.models import OrganizationProfile


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            class OrganizationRepository:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                async def get_profile(self, organization_id: str) -> OrganizationProfile | None:
                    row = await self._session.get(OrganizationORM, organization_id)
                    if row is None:
                        return None
                    return self._to_domain(row)

                async def update_contact_email(
                    self,
                    organization_id: str,
                    contact_email: str | None,
                ) -> OrganizationProfile | None:
                    row = await self._session.get(OrganizationORM, organization_id)
                    if row is None:
                        return None
                    row.contact_email = contact_email
                    row.version += 1
                    row.updated_at = _utcnow()
                    await self._session.commit()
                    await self._session.refresh(row)
                    return self._to_domain(row)

                async def update_contact_email_if_version(
                    self,
                    organization_id: str,
                    contact_email: str | None,
                    expected_version: int,
                ) -> OrganizationProfile | None:
                    return await self._update_profile_if_version(
                        organization_id=organization_id,
                        expected_version=expected_version,
                        values={"contact_email": contact_email},
                    )

                async def update_display_name_if_version(
                    self,
                    organization_id: str,
                    display_name: str,
                    expected_version: int,
                ) -> OrganizationProfile | None:
                    return await self._update_profile_if_version(
                        organization_id=organization_id,
                        expected_version=expected_version,
                        values={"display_name": display_name},
                    )

                async def _update_profile_if_version(
                    self,
                    *,
                    organization_id: str,
                    expected_version: int,
                    values: dict,
                ) -> OrganizationProfile | None:
                    statement = (
                        update(OrganizationORM)
                        .where(
                            OrganizationORM.id == organization_id,
                            OrganizationORM.version == expected_version,
                        )
                        .values(
                            **values,
                            version=expected_version + 1,
                            updated_at=_utcnow(),
                        )
                    )
                    result = await self._session.execute(statement)
                    if result.rowcount != 1:
                        await self._session.rollback()
                        return None
                    await self._session.commit()
                    row = await self._session.get(OrganizationORM, organization_id)
                    return self._to_domain(row) if row is not None else None

                @staticmethod
                def _to_domain(row: OrganizationORM) -> OrganizationProfile:
                    return OrganizationProfile(
                        id=row.id,
                        display_name=row.display_name,
                        legal_name=row.legal_name,
                        contact_email=row.contact_email,
                        environment=Environment(row.environment),
                        status=OrganizationStatus(row.status),
                        version=row.version,
                        created_at=row.created_at,
                        updated_at=row.updated_at,
                    )
            '''
        ),
    )

    write_text(
        root,
        "app/repositories/organization_overview_repository.py",
        clean_block(
            '''
            """Persistence mapping for the organization overview page."""

            from __future__ import annotations

            from datetime import datetime, timezone

            from sqlalchemy import update
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.orm_models import OrganizationOverviewORM
            from app.domain.enums import WorkspaceHealthStatus
            from app.domain.models import (
                OrganizationOverview,
                OrganizationOverviewMetrics,
                OrganizationProfile,
            )


            def _utcnow() -> datetime:
                return datetime.now(timezone.utc)


            class OrganizationOverviewRepository:
                def __init__(self, session: AsyncSession) -> None:
                    self._session = session

                async def get_for_profile(
                    self,
                    profile: OrganizationProfile,
                ) -> OrganizationOverview:
                    row = await self._session.get(OrganizationOverviewORM, profile.id)
                    if row is None:
                        return OrganizationOverview(
                            organization=profile,
                            organization_type="organization",
                            renewal_date=None,
                            workspace_status=WorkspaceHealthStatus.UNKNOWN,
                            metrics=OrganizationOverviewMetrics(
                                licensed_modules=0,
                                available_areas=0,
                                organization_logins=0,
                                workspace_health_percent=0,
                            ),
                            version=1,
                            updated_at=profile.updated_at,
                        )
                    return self._to_domain(row, profile)

                async def update_organization_type_if_version(
                    self,
                    *,
                    profile: OrganizationProfile,
                    organization_type: str,
                    expected_version: int,
                ) -> OrganizationOverview | None:
                    statement = (
                        update(OrganizationOverviewORM)
                        .where(
                            OrganizationOverviewORM.organization_id == profile.id,
                            OrganizationOverviewORM.version == expected_version,
                        )
                        .values(
                            organization_type=organization_type,
                            version=expected_version + 1,
                            updated_at=_utcnow(),
                        )
                    )
                    result = await self._session.execute(statement)
                    if result.rowcount != 1:
                        await self._session.rollback()
                        return None
                    await self._session.commit()
                    row = await self._session.get(OrganizationOverviewORM, profile.id)
                    return self._to_domain(row, profile) if row is not None else None

                @staticmethod
                def _to_domain(
                    row: OrganizationOverviewORM,
                    profile: OrganizationProfile,
                ) -> OrganizationOverview:
                    return OrganizationOverview(
                        organization=profile,
                        organization_type=row.organization_type,
                        renewal_date=row.renewal_date,
                        workspace_status=WorkspaceHealthStatus(row.workspace_status),
                        metrics=OrganizationOverviewMetrics(
                            licensed_modules=row.licensed_modules,
                            available_areas=row.available_areas,
                            organization_logins=row.organization_logins,
                            workspace_health_percent=row.workspace_health_percent,
                        ),
                        version=row.version,
                        updated_at=row.updated_at,
                    )
            '''
        ),
    )


def patch_action_registry(root: Path) -> None:
    path = "app/agent/action_registry.py"
    replace_exact(
        root,
        path,
        "    AgentActionProposalInput,\n    AgentApprovalPolicy,\n",
        "    AgentActionProposalInput,\n    AgentActionResourcePrecondition,\n    AgentApprovalPolicy,\n",
    )
    replace_section(
        root,
        path,
        "def build_action_fingerprint(\n",
        "    return hashlib.sha256(canonical.encode(\"utf-8\")).hexdigest()\n",
        clean_block(
            '''
            def build_action_fingerprint(
                *,
                organization_id: str,
                requested_by_user_id: str,
                action_name: str,
                arguments: dict[str, str],
                changes: tuple[AgentActionChange, ...],
                observed_resource_version: int,
                approval_policy: AgentApprovalPolicy,
                resource_type: str,
                resource_id: str,
                expires_at: datetime,
                resource_preconditions: tuple[AgentActionResourcePrecondition, ...] = (),
                fingerprint_version: int = 3,
            ) -> str:
                payload = {
                    "organization_id": organization_id,
                    "requested_by_user_id": requested_by_user_id,
                    "action_name": action_name,
                    "arguments": dict(sorted(arguments.items())),
                    "changes": [change.model_dump(mode="json") for change in changes],
                    "observed_resource_version": observed_resource_version,
                    "approval_policy": approval_policy.model_dump(mode="json"),
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "expires_at": _canonical_utc_datetime(expires_at),
                }
                if fingerprint_version == 2:
                    payload["version"] = 2
                elif fingerprint_version == 3:
                    if not resource_preconditions:
                        resource_preconditions = (
                            AgentActionResourcePrecondition(
                                resource_type=resource_type,
                                resource_id=resource_id,
                                observed_version=observed_resource_version,
                            ),
                        )
                    payload["resource_preconditions"] = [
                        item.model_dump(mode="json")
                        for item in sorted(
                            resource_preconditions,
                            key=lambda item: (item.resource_type, item.resource_id),
                        )
                    ]
                    payload["version"] = 3
                else:
                    raise ValueError("Unsupported action fingerprint version")
                canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
                return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            '''
        ),
    )


def patch_action_persistence(root: Path) -> None:
    replace_exact(
        root,
        "app/db/action_models.py",
        "    observed_resource_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)\n"
        "    approval_policy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)\n",
        "    observed_resource_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)\n"
        "    resource_preconditions_json: Mapped[list] = mapped_column(\n"
        "        JSON, nullable=False, default=list\n"
        "    )\n"
        "    fingerprint_version: Mapped[int] = mapped_column(Integer, nullable=False, default=3)\n"
        "    approval_policy_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)\n",
    )

    path = "app/repositories/agent_action_repository.py"
    replace_exact(
        root,
        path,
        "    AgentActionProposal,\n    AgentApprovalPolicy,\n",
        "    AgentActionProposal,\n    AgentActionResourcePrecondition,\n    AgentApprovalPolicy,\n",
    )
    replace_exact(
        root,
        path,
        "        observed_resource_version: int,\n        approval_policy: AgentApprovalPolicy,\n",
        "        observed_resource_version: int,\n"
        "        resource_preconditions: tuple[AgentActionResourcePrecondition, ...],\n"
        "        fingerprint_version: int,\n"
        "        approval_policy: AgentApprovalPolicy,\n",
    )
    replace_exact(
        root,
        path,
        "            observed_resource_version=observed_resource_version,\n"
        "            approval_policy_json=approval_policy.model_dump(mode=\"json\"),\n",
        "            observed_resource_version=observed_resource_version,\n"
        "            resource_preconditions_json=[\n"
        "                item.model_dump(mode=\"json\") for item in resource_preconditions\n"
        "            ],\n"
        "            fingerprint_version=fingerprint_version,\n"
        "            approval_policy_json=approval_policy.model_dump(mode=\"json\"),\n",
    )
    replace_exact(
        root,
        path,
        "            action_fingerprint=row.action_fingerprint,\n"
        "            risk_level=row.risk_level,\n",
        "            action_fingerprint=row.action_fingerprint,\n"
        "            fingerprint_version=row.fingerprint_version,\n"
        "            risk_level=row.risk_level,\n",
    )
    replace_exact(
        root,
        path,
        "            observed_resource_version=row.observed_resource_version,\n"
        "            approval_policy=AgentApprovalPolicy.model_validate(policy_payload),\n",
        "            observed_resource_version=row.observed_resource_version,\n"
        "            resource_preconditions=tuple(\n"
        "                AgentActionResourcePrecondition.model_validate(item)\n"
        "                for item in (row.resource_preconditions_json or [])\n"
        "            ),\n"
        "            approval_policy=AgentApprovalPolicy.model_validate(policy_payload),\n",
    )


def add_migration(root: Path) -> None:
    create_exact(
        root,
        "alembic/versions/0012_resource_preconditions.py",
        clean_block(
            '''
            """add multi-resource action preconditions

            Revision ID: 0012_resource_preconditions
            Revises: 0011_nucleus_organization_schema
            Create Date: 2026-07-18
            """

            from __future__ import annotations

            from typing import Sequence, Union

            import sqlalchemy as sa
            from alembic import op

            revision: str = "0012_resource_preconditions"
            down_revision: Union[str, None] = "0011_nucleus_organization_schema"
            branch_labels: Union[str, Sequence[str], None] = None
            depends_on: Union[str, Sequence[str], None] = None


            def upgrade() -> None:
                with op.batch_alter_table("agent_action_proposals") as batch_op:
                    batch_op.add_column(
                        sa.Column(
                            "resource_preconditions_json",
                            sa.JSON(),
                            nullable=False,
                            server_default=sa.text("'[]'"),
                        )
                    )
                    batch_op.add_column(
                        sa.Column(
                            "fingerprint_version",
                            sa.Integer(),
                            nullable=False,
                            server_default=sa.text("2"),
                        )
                    )

                proposals = sa.table(
                    "agent_action_proposals",
                    sa.column("id", sa.String()),
                    sa.column("resource_type", sa.String()),
                    sa.column("resource_id", sa.String()),
                    sa.column("observed_resource_version", sa.Integer()),
                    sa.column("resource_preconditions_json", sa.JSON()),
                    sa.column("fingerprint_version", sa.Integer()),
                )
                connection = op.get_bind()
                rows = list(
                    connection.execute(
                        sa.select(
                            proposals.c.id,
                            proposals.c.resource_type,
                            proposals.c.resource_id,
                            proposals.c.observed_resource_version,
                        )
                    ).mappings()
                )
                for row in rows:
                    connection.execute(
                        proposals.update()
                        .where(proposals.c.id == row["id"])
                        .values(
                            resource_preconditions_json=[
                                {
                                    "resource_type": row["resource_type"],
                                    "resource_id": row["resource_id"],
                                    "observed_version": row["observed_resource_version"],
                                }
                            ],
                            fingerprint_version=2,
                        )
                    )

                with op.batch_alter_table("agent_action_proposals") as batch_op:
                    batch_op.alter_column(
                        "fingerprint_version",
                        existing_type=sa.Integer(),
                        server_default=sa.text("3"),
                    )


            def downgrade() -> None:
                with op.batch_alter_table("agent_action_proposals") as batch_op:
                    batch_op.drop_column("fingerprint_version")
                    batch_op.drop_column("resource_preconditions_json")
            '''
        ),
    )


def patch_action_service(root: Path) -> None:
    path = "app/services/agent_action_service.py"
    replace_exact(
        root,
        path,
        "            changes=preparation.changes,\n"
        "            observed_resource_version=preparation.observed_resource_version,\n"
        "            approval_policy=action_definition.approval_policy,\n"
        "            resource_type=preparation.resource_type,\n",
        "            changes=preparation.changes,\n"
        "            observed_resource_version=preparation.observed_resource_version,\n"
        "            resource_preconditions=preparation.resource_preconditions,\n"
        "            fingerprint_version=3,\n"
        "            approval_policy=action_definition.approval_policy,\n"
        "            resource_type=preparation.resource_type,\n",
    )
    replace_exact(
        root,
        path,
        "            resource_id=preparation.resource_id,\n"
        "            observed_resource_version=preparation.observed_resource_version,\n"
        "            approval_policy=action_definition.approval_policy,\n"
        "            expires_at=expires_at,\n",
        "            resource_id=preparation.resource_id,\n"
        "            observed_resource_version=preparation.observed_resource_version,\n"
        "            resource_preconditions=preparation.resource_preconditions,\n"
        "            fingerprint_version=3,\n"
        "            approval_policy=action_definition.approval_policy,\n"
        "            expires_at=expires_at,\n",
    )
    replace_exact(
        root,
        path,
        "            current_preparation.observed_resource_version\n"
        "            != proposal.observed_resource_version\n"
        "            or current_preparation.changes != proposal.changes\n",
        "            current_preparation.resource_preconditions\n"
        "            != proposal.resource_preconditions\n"
        "            or current_preparation.changes != proposal.changes\n",
    )
    replace_exact(
        root,
        path,
        "            observed_resource_version=proposal.observed_resource_version,\n"
        "            approval_policy=proposal.approval_policy,\n",
        "            observed_resource_version=proposal.observed_resource_version,\n"
        "            resource_preconditions=proposal.resource_preconditions,\n"
        "            fingerprint_version=proposal.fingerprint_version,\n"
        "            approval_policy=proposal.approval_policy,\n",
    )


def patch_nucleus_gateway_and_repository(root: Path) -> None:
    contract_path = "app/adapters/nucleus/contract.py"
    replace_exact(
        root,
        contract_path,
        indent_block(
            '''
            async def get_contact_email_bridge_state(
                self,
                organization_code: str,
            ) -> tuple[NucleusOrganizationAccount, int] | None:
                ...

            async def update_contact_email_bridge_if_version(
                self,
                *,
                organization_code: str,
                value: str,
                expected_legacy_version: int,
                expected_nucleus_email: str | None,
            ) -> NucleusOrganizationAccount | None:
                ...
            ''',
            4,
        ),
        "",
    )

    path = "app/repositories/nucleus_organization_repository.py"
    replace_exact(
        root,
        path,
        "from app.db.orm_models import OrganizationORM, OrganizationOverviewORM\n",
        "",
    )
    replace_section(
        root,
        path,
        "    async def get_contact_email_bridge_state(\n",
        "        return self._account_to_domain(row, next_nucleus_version)\n",
        "",
    )
    replace_exact(
        root,
        path,
        "        await self._synchronize_legacy_overview(\n"
        "            organization_code=organization_code,\n"
        "            field_name=field_name,\n"
        "            value=value,\n"
        "        )\n",
        "",
    )
    replace_section(
        root,
        path,
        "    async def _synchronize_legacy_overview(\n",
        "                overview.version += 1\n",
        "",
    )

def patch_organization_gateway_implementation(root: Path) -> None:
    path = "app/mock_api/service.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            async def update_contact_email_if_version(
                self,
                organization_id: str,
                contact_email: str,
                expected_version: int,
            ) -> OrganizationProfile | None:
                await self._require_organization_profile(organization_id)
                return await self._organization_repository.update_contact_email_if_version(
                    organization_id,
                    contact_email,
                    expected_version,
                )
            ''',
            4,
        ),
        indent_block(
            '''
            async def update_contact_email_if_version(
                self,
                organization_id: str,
                contact_email: str | None,
                expected_version: int,
            ) -> OrganizationProfile | None:
                await self._require_organization_profile(organization_id)
                return await self._organization_repository.update_contact_email_if_version(
                    organization_id,
                    contact_email,
                    expected_version,
                )

            async def update_display_name_if_version(
                self,
                organization_id: str,
                display_name: str,
                expected_version: int,
            ) -> OrganizationProfile | None:
                await self._require_organization_profile(organization_id)
                return await self._organization_repository.update_display_name_if_version(
                    organization_id,
                    display_name,
                    expected_version,
                )

            async def update_organization_type_if_version(
                self,
                organization_id: str,
                organization_type: str,
                expected_version: int,
            ) -> OrganizationOverview | None:
                profile = await self._require_organization_profile(organization_id)
                return await self._overview_repository.update_organization_type_if_version(
                    profile=profile,
                    organization_type=organization_type,
                    expected_version=expected_version,
                )
            ''',
            4,
        ),
    )

    path = "app/adapters/organization/mock_adapter.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            async def update_contact_email_if_version(
                self,
                organization_id: str,
                contact_email: str,
                expected_version: int,
            ) -> OrganizationProfile | None:
                return await self._api.update_contact_email_if_version(
                    organization_id,
                    contact_email,
                    expected_version,
                )
            ''',
            4,
        ),
        indent_block(
            '''
            async def update_contact_email_if_version(
                self,
                organization_id: str,
                contact_email: str | None,
                expected_version: int,
            ) -> OrganizationProfile | None:
                return await self._api.update_contact_email_if_version(
                    organization_id,
                    contact_email,
                    expected_version,
                )

            async def update_display_name_if_version(
                self,
                organization_id: str,
                display_name: str,
                expected_version: int,
            ) -> OrganizationProfile | None:
                return await self._api.update_display_name_if_version(
                    organization_id,
                    display_name,
                    expected_version,
                )

            async def update_organization_type_if_version(
                self,
                organization_id: str,
                organization_type: str,
                expected_version: int,
            ) -> OrganizationOverview | None:
                return await self._api.update_organization_type_if_version(
                    organization_id,
                    organization_type,
                    expected_version,
                )
            ''',
            4,
        ),
    )

def patch_nucleus_handlers(root: Path) -> None:
    path = "app/agent/nucleus_action_handlers.py"
    replacement = clean_block(
        '''
        """Approval-gated handlers for safe Nucleus account and access mutations."""

        from __future__ import annotations

        from dataclasses import dataclass
        from typing import Any

        from app.adapters.nucleus.contract import NucleusOrganizationGateway
        from app.agent.action_contracts import (
            AgentActionChange,
            AgentActionExecutionResult,
            AgentActionHandlerResult,
            AgentActionPreparation,
            AgentActionProposal,
            AgentActionResourcePrecondition,
            VersionedOrganizationMutationGateway,
        )
        from app.agent.action_handlers import StaleActionResourceError, normalize_email
        from app.domain.nucleus_policy import (
            CLEARABLE_NUCLEUS_ACCOUNT_FIELDS,
            EDITABLE_NUCLEUS_ACCOUNT_FIELDS,
            NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS,
        )

        _NULL_SENTINELS = {"null", "none", "-"}
        _FIELD_MAX_LENGTHS = NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS
        _CLEARABLE_FIELDS = CLEARABLE_NUCLEUS_ACCOUNT_FIELDS
        _PROJECTED_FIELDS = frozenset({"OrganizationName", "OrganizationType", "Email"})


        @dataclass(frozen=True)
        class _ProjectionState:
            field: str
            resource_type: str
            resource_id: str
            value: Any
            version: int


        def _normalize_field_name(value: str) -> str:
            normalized = value.strip()
            for allowed in EDITABLE_NUCLEUS_ACCOUNT_FIELDS:
                if allowed.lower() == normalized.lower():
                    return allowed
            raise ValueError("Organization account field is not editable")


        def _normalize_account_value(field_name: str, value: str) -> str:
            normalized = value.strip()
            if not normalized:
                raise ValueError("Organization account value is required")
            if len(normalized) > _FIELD_MAX_LENGTHS[field_name]:
                raise ValueError("Organization account value is too long")
            if field_name == "Email":
                lowered = normalized.lower()
                local, separator, domain = lowered.partition("@")
                if not separator or not local or "." not in domain:
                    raise ValueError("Email is invalid")
                return lowered
            return normalized


        def _nullable_int(value: str, *, field_name: str) -> int | None:
            normalized = value.strip().lower()
            if normalized in _NULL_SENTINELS:
                return None
            try:
                parsed = int(normalized)
            except ValueError as exception:
                raise ValueError(f"{field_name} must be an integer or null") from exception
            if parsed <= 0:
                raise ValueError(f"{field_name} must be positive")
            return parsed


        def _required_int(value: str, *, field_name: str) -> int:
            parsed = _nullable_int(value, field_name=field_name)
            if parsed is None:
                raise ValueError(f"{field_name} is required")
            return parsed


        def _nullable_bool(value: str, *, field_name: str) -> bool | None:
            normalized = value.strip().lower()
            if normalized in _NULL_SENTINELS:
                return None
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
            raise ValueError(f"{field_name} must be true, false, or null")


        def _required_bool(value: str, *, field_name: str) -> bool:
            parsed = _nullable_bool(value, field_name=field_name)
            if parsed is None:
                raise ValueError(f"{field_name} is required")
            return parsed


        def _sentinel(value: int | bool | None) -> str:
            if value is None:
                return "null"
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)


        def _projection_target(field_name: str, value: str | None) -> str | None:
            if field_name == "OrganizationType" and value is None:
                return "organization"
            return value


        async def _read_projection(
            gateway: VersionedOrganizationMutationGateway,
            *,
            organization_id: str,
            field_name: str,
        ) -> _ProjectionState | None:
            if field_name == "OrganizationName":
                profile = await gateway.get_profile(organization_id)
                return _ProjectionState(
                    field="organization.display_name",
                    resource_type="organization",
                    resource_id=organization_id,
                    value=profile.display_name,
                    version=profile.version,
                )
            if field_name == "Email":
                profile = await gateway.get_profile(organization_id)
                return _ProjectionState(
                    field="organization.contact_email",
                    resource_type="organization",
                    resource_id=organization_id,
                    value=profile.contact_email,
                    version=profile.version,
                )
            if field_name == "OrganizationType":
                overview = await gateway.get_overview(organization_id)
                return _ProjectionState(
                    field="organization_overview.organization_type",
                    resource_type="organization_overview",
                    resource_id=organization_id,
                    value=overview.organization_type,
                    version=overview.version,
                )
            return None


        async def _update_projection_if_version(
            gateway: VersionedOrganizationMutationGateway,
            *,
            organization_id: str,
            field_name: str,
            value: str | None,
            expected_version: int,
        ) -> _ProjectionState | None:
            target = _projection_target(field_name, value)
            if field_name == "OrganizationName":
                if target is None:
                    raise ValueError("Organization name cannot be cleared")
                profile = await gateway.update_display_name_if_version(
                    organization_id,
                    target,
                    expected_version,
                )
                if profile is None:
                    return None
                return _ProjectionState(
                    field="organization.display_name",
                    resource_type="organization",
                    resource_id=organization_id,
                    value=profile.display_name,
                    version=profile.version,
                )
            if field_name == "Email":
                profile = await gateway.update_contact_email_if_version(
                    organization_id,
                    target,
                    expected_version,
                )
                if profile is None:
                    return None
                return _ProjectionState(
                    field="organization.contact_email",
                    resource_type="organization",
                    resource_id=organization_id,
                    value=profile.contact_email,
                    version=profile.version,
                )
            if field_name == "OrganizationType":
                if target is None:
                    target = "organization"
                overview = await gateway.update_organization_type_if_version(
                    organization_id,
                    target,
                    expected_version,
                )
                if overview is None:
                    return None
                return _ProjectionState(
                    field="organization_overview.organization_type",
                    resource_type="organization_overview",
                    resource_id=organization_id,
                    value=overview.organization_type,
                    version=overview.version,
                )
            return None


        def _find_precondition(
            proposal: AgentActionProposal,
            *,
            resource_type: str,
            resource_id: str | None = None,
        ) -> AgentActionResourcePrecondition:
            matches = [
                item
                for item in proposal.resource_preconditions
                if item.resource_type == resource_type
                and (resource_id is None or item.resource_id == resource_id)
            ]
            if len(matches) != 1:
                raise ValueError("Action resource precondition is missing or ambiguous")
            return matches[0]


        def _change_by_field(proposal: AgentActionProposal, field: str) -> AgentActionChange:
            matches = [item for item in proposal.changes if item.field == field]
            if len(matches) != 1:
                raise ValueError("Reviewed action change is missing or ambiguous")
            return matches[0]


        async def _apply_projection_after_nucleus(
            gateway: VersionedOrganizationMutationGateway,
            *,
            proposal: AgentActionProposal,
            field_name: str,
            value: str | None,
        ) -> _ProjectionState | None:
            current = await _read_projection(
                gateway,
                organization_id=proposal.organization_id,
                field_name=field_name,
            )
            if current is None:
                return None
            target = _projection_target(field_name, value)
            approved_change = _change_by_field(proposal, current.field)
            precondition = _find_precondition(
                proposal,
                resource_type=current.resource_type,
                resource_id=current.resource_id,
            )
            if current.value == target:
                return current
            if (
                current.version != precondition.observed_version
                or current.value != approved_change.before
            ):
                return None
            return await _update_projection_if_version(
                gateway,
                organization_id=proposal.organization_id,
                field_name=field_name,
                value=value,
                expected_version=current.version,
            )


        class UpdateOrganizationContactEmailBridgeHandler:
            """Coordinate canonical Nucleus email with the legacy Overview projection."""

            def __init__(
                self,
                gateway: NucleusOrganizationGateway,
                organization_gateway: VersionedOrganizationMutationGateway,
            ) -> None:
                self._gateway = gateway
                self._organization_gateway = organization_gateway

            async def prepare(
                self,
                *,
                organization_id: str,
                arguments: dict[str, str],
            ) -> AgentActionPreparation:
                contact_email = normalize_email(arguments["contact_email"])
                state = await self._gateway.get_account_field_state(
                    organization_id,
                    "Email",
                )
                if state is None:
                    raise ValueError("Nucleus organization account was not found")
                account, nucleus_before = state
                projection = await _read_projection(
                    self._organization_gateway,
                    organization_id=organization_id,
                    field_name="Email",
                )
                if projection is None:
                    raise ValueError("Organization contact projection was not found")
                if nucleus_before == contact_email and projection.value == contact_email:
                    raise ValueError("Organization contact email already has this value")
                return AgentActionPreparation(
                    normalized_arguments={"contact_email": contact_email},
                    changes=(
                        AgentActionChange(
                            field="nucleus.Email",
                            before=nucleus_before,
                            after=contact_email,
                        ),
                        AgentActionChange(
                            field=projection.field,
                            before=projection.value,
                            after=contact_email,
                        ),
                    ),
                    observed_resource_version=projection.version,
                    resource_type="organization",
                    resource_id=organization_id,
                    resource_preconditions=(
                        AgentActionResourcePrecondition(
                            resource_type="OrganizationAccount",
                            resource_id=str(account.organization_account_id),
                            observed_version=account.version,
                        ),
                        AgentActionResourcePrecondition(
                            resource_type=projection.resource_type,
                            resource_id=projection.resource_id,
                            observed_version=projection.version,
                        ),
                    ),
                )

            async def execute(
                self,
                *,
                proposal: AgentActionProposal,
            ) -> AgentActionHandlerResult:
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                target = proposal.arguments["contact_email"]
                updated = await self._gateway.update_account_field_if_version(
                    organization_code=proposal.organization_id,
                    field_name="Email",
                    value=target,
                    expected_version=nucleus_precondition.observed_version,
                )
                if updated is None:
                    raise StaleActionResourceError()
                projection = await _apply_projection_after_nucleus(
                    self._organization_gateway,
                    proposal=proposal,
                    field_name="Email",
                    value=target,
                )
                if projection is None:
                    raise RuntimeError("Contact-email projection requires reconciliation")
                return AgentActionHandlerResult(
                    resource_type="organization",
                    resource_id=proposal.organization_id,
                    before={
                        "contact_email": _change_by_field(
                            proposal,
                            "nucleus.Email",
                        ).before,
                        "version": proposal.observed_resource_version,
                        "nucleus_version": nucleus_precondition.observed_version,
                    },
                    after={
                        "contact_email": target,
                        "version": projection.version,
                        "nucleus_version": updated.version,
                    },
                )

            async def reconcile(
                self,
                *,
                proposal: AgentActionProposal,
                execution: AgentActionExecutionResult,
            ) -> AgentActionHandlerResult | None:
                target = proposal.arguments["contact_email"]
                state = await self._gateway.get_account_field_state(
                    proposal.organization_id,
                    "Email",
                )
                if state is None:
                    return None
                account, value = state
                if value != target:
                    return None
                projection = await _apply_projection_after_nucleus(
                    self._organization_gateway,
                    proposal=proposal,
                    field_name="Email",
                    value=target,
                )
                if projection is None:
                    return None
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                return AgentActionHandlerResult(
                    resource_type="organization",
                    resource_id=proposal.organization_id,
                    before={
                        "contact_email": _change_by_field(
                            proposal,
                            "nucleus.Email",
                        ).before,
                        "version": proposal.observed_resource_version,
                        "nucleus_version": nucleus_precondition.observed_version,
                    },
                    after={
                        "contact_email": target,
                        "version": projection.version,
                        "nucleus_version": account.version,
                    },
                )


        class UpdateNucleusOrganizationAccountFieldHandler:
            def __init__(
                self,
                gateway: NucleusOrganizationGateway,
                organization_gateway: VersionedOrganizationMutationGateway,
            ) -> None:
                self._gateway = gateway
                self._organization_gateway = organization_gateway

            async def prepare(
                self,
                *,
                organization_id: str,
                arguments: dict[str, str],
            ) -> AgentActionPreparation:
                field_name = _normalize_field_name(arguments["field_name"])
                value = _normalize_account_value(field_name, arguments["value"])
                state = await self._gateway.get_account_field_state(
                    organization_id,
                    field_name,
                )
                if state is None:
                    raise ValueError("Nucleus organization account was not found")
                account, before = state
                projection = (
                    await _read_projection(
                        self._organization_gateway,
                        organization_id=organization_id,
                        field_name=field_name,
                    )
                    if field_name in _PROJECTED_FIELDS
                    else None
                )
                target_projection = _projection_target(field_name, value)
                if before == value and (
                    projection is None or projection.value == target_projection
                ):
                    raise ValueError("Organization account field already has this value")
                changes = [
                    AgentActionChange(field=field_name, before=before, after=value)
                ]
                preconditions = [
                    AgentActionResourcePrecondition(
                        resource_type="OrganizationAccount",
                        resource_id=str(account.organization_account_id),
                        observed_version=account.version,
                    )
                ]
                if projection is not None:
                    changes.append(
                        AgentActionChange(
                            field=projection.field,
                            before=projection.value,
                            after=target_projection,
                        )
                    )
                    preconditions.append(
                        AgentActionResourcePrecondition(
                            resource_type=projection.resource_type,
                            resource_id=projection.resource_id,
                            observed_version=projection.version,
                        )
                    )
                return AgentActionPreparation(
                    normalized_arguments={"field_name": field_name, "value": value},
                    changes=tuple(changes),
                    observed_resource_version=account.version,
                    resource_type="OrganizationAccount",
                    resource_id=str(account.organization_account_id),
                    resource_preconditions=tuple(preconditions),
                )

            async def execute(
                self,
                *,
                proposal: AgentActionProposal,
            ) -> AgentActionHandlerResult:
                field_name = proposal.arguments["field_name"]
                value = proposal.arguments["value"]
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                updated = await self._gateway.update_account_field_if_version(
                    organization_code=proposal.organization_id,
                    field_name=field_name,
                    value=value,
                    expected_version=nucleus_precondition.observed_version,
                )
                if updated is None:
                    raise StaleActionResourceError()
                projection_version = None
                if field_name in _PROJECTED_FIELDS:
                    projection = await _apply_projection_after_nucleus(
                        self._organization_gateway,
                        proposal=proposal,
                        field_name=field_name,
                        value=value,
                    )
                    if projection is None:
                        raise RuntimeError("Organization projection requires reconciliation")
                    projection_version = projection.version
                return AgentActionHandlerResult(
                    resource_type="OrganizationAccount",
                    resource_id=str(updated.organization_account_id),
                    before={
                        "field_name": field_name,
                        "value": proposal.changes[0].before,
                        "version": nucleus_precondition.observed_version,
                    },
                    after={
                        "field_name": field_name,
                        "value": value,
                        "version": updated.version,
                        "projection_version": projection_version,
                    },
                )

            async def reconcile(
                self,
                *,
                proposal: AgentActionProposal,
                execution: AgentActionExecutionResult,
            ) -> AgentActionHandlerResult | None:
                field_name = proposal.arguments["field_name"]
                target = proposal.arguments["value"]
                state = await self._gateway.get_account_field_state(
                    proposal.organization_id,
                    field_name,
                )
                if state is None:
                    return None
                account, value = state
                if value != target:
                    return None
                projection_version = None
                if field_name in _PROJECTED_FIELDS:
                    projection = await _apply_projection_after_nucleus(
                        self._organization_gateway,
                        proposal=proposal,
                        field_name=field_name,
                        value=target,
                    )
                    if projection is None:
                        return None
                    projection_version = projection.version
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                return AgentActionHandlerResult(
                    resource_type="OrganizationAccount",
                    resource_id=str(account.organization_account_id),
                    before={
                        "field_name": field_name,
                        "value": proposal.changes[0].before,
                        "version": nucleus_precondition.observed_version,
                    },
                    after={
                        "field_name": field_name,
                        "value": value,
                        "version": account.version,
                        "projection_version": projection_version,
                    },
                )


        class ClearNucleusOrganizationAccountFieldHandler:
            def __init__(
                self,
                gateway: NucleusOrganizationGateway,
                organization_gateway: VersionedOrganizationMutationGateway,
            ) -> None:
                self._gateway = gateway
                self._organization_gateway = organization_gateway

            async def prepare(
                self,
                *,
                organization_id: str,
                arguments: dict[str, str],
            ) -> AgentActionPreparation:
                field_name = _normalize_field_name(arguments["field_name"])
                if field_name not in _CLEARABLE_FIELDS:
                    raise ValueError("This organization account field cannot be cleared")
                state = await self._gateway.get_account_field_state(
                    organization_id,
                    field_name,
                )
                if state is None:
                    raise ValueError("Nucleus organization account was not found")
                account, before = state
                projection = (
                    await _read_projection(
                        self._organization_gateway,
                        organization_id=organization_id,
                        field_name=field_name,
                    )
                    if field_name in _PROJECTED_FIELDS
                    else None
                )
                target_projection = _projection_target(field_name, None)
                if before is None and (
                    projection is None or projection.value == target_projection
                ):
                    raise ValueError("Organization account field is already empty")
                changes = [
                    AgentActionChange(field=field_name, before=before, after=None)
                ]
                preconditions = [
                    AgentActionResourcePrecondition(
                        resource_type="OrganizationAccount",
                        resource_id=str(account.organization_account_id),
                        observed_version=account.version,
                    )
                ]
                if projection is not None:
                    changes.append(
                        AgentActionChange(
                            field=projection.field,
                            before=projection.value,
                            after=target_projection,
                        )
                    )
                    preconditions.append(
                        AgentActionResourcePrecondition(
                            resource_type=projection.resource_type,
                            resource_id=projection.resource_id,
                            observed_version=projection.version,
                        )
                    )
                return AgentActionPreparation(
                    normalized_arguments={"field_name": field_name},
                    changes=tuple(changes),
                    observed_resource_version=account.version,
                    resource_type="OrganizationAccount",
                    resource_id=str(account.organization_account_id),
                    resource_preconditions=tuple(preconditions),
                )

            async def execute(
                self,
                *,
                proposal: AgentActionProposal,
            ) -> AgentActionHandlerResult:
                field_name = proposal.arguments["field_name"]
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                updated = await self._gateway.update_account_field_if_version(
                    organization_code=proposal.organization_id,
                    field_name=field_name,
                    value=None,
                    expected_version=nucleus_precondition.observed_version,
                )
                if updated is None:
                    raise StaleActionResourceError()
                projection_version = None
                if field_name in _PROJECTED_FIELDS:
                    projection = await _apply_projection_after_nucleus(
                        self._organization_gateway,
                        proposal=proposal,
                        field_name=field_name,
                        value=None,
                    )
                    if projection is None:
                        raise RuntimeError("Organization projection requires reconciliation")
                    projection_version = projection.version
                return AgentActionHandlerResult(
                    resource_type="OrganizationAccount",
                    resource_id=str(updated.organization_account_id),
                    before={
                        "field_name": field_name,
                        "value": proposal.changes[0].before,
                        "version": nucleus_precondition.observed_version,
                    },
                    after={
                        "field_name": field_name,
                        "value": None,
                        "version": updated.version,
                        "projection_version": projection_version,
                    },
                )

            async def reconcile(
                self,
                *,
                proposal: AgentActionProposal,
                execution: AgentActionExecutionResult,
            ) -> AgentActionHandlerResult | None:
                field_name = proposal.arguments["field_name"]
                state = await self._gateway.get_account_field_state(
                    proposal.organization_id,
                    field_name,
                )
                if state is None:
                    return None
                account, value = state
                if value is not None:
                    return None
                projection_version = None
                if field_name in _PROJECTED_FIELDS:
                    projection = await _apply_projection_after_nucleus(
                        self._organization_gateway,
                        proposal=proposal,
                        field_name=field_name,
                        value=None,
                    )
                    if projection is None:
                        return None
                    projection_version = projection.version
                nucleus_precondition = _find_precondition(
                    proposal,
                    resource_type="OrganizationAccount",
                )
                return AgentActionHandlerResult(
                    resource_type="OrganizationAccount",
                    resource_id=str(account.organization_account_id),
                    before={
                        "field_name": field_name,
                        "value": proposal.changes[0].before,
                        "version": nucleus_precondition.observed_version,
                    },
                    after={
                        "field_name": field_name,
                        "value": None,
                        "version": account.version,
                        "projection_version": projection_version,
                    },
                )


        '''
    )
    replace_section(
        root,
        path,
        '"""Approval-gated handlers for safe Nucleus account and access mutations."""\n',
        "class GrantNucleusCategoryAccessHandler:\n",
        replacement + "class GrantNucleusCategoryAccessHandler:\n",
    )


def patch_dependencies(root: Path) -> None:
    write_text(
        root,
        "app/api/dependencies.py",
        clean_block(
            '''
            """FastAPI request dependencies and service wiring."""

            from __future__ import annotations

            from typing import Annotated

            from fastapi import Depends, Header
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.adapters.nucleus.contract import NucleusOrganizationGateway
            from app.adapters.organization.contract import OrganizationApiGateway
            from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
            from app.agent.action_contracts import VersionedOrganizationMutationGateway
            from app.core.errors import UnauthenticatedError, UserDisabledError
            from app.db.session import get_session
            from app.domain.models import User
            from app.mock_api.service import MockOrganizationApi
            from app.permissions.permission_service import PermissionService
            from app.repositories.audit_repository import AuditRepository
            from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository
            from app.repositories.user_repository import UserRepository
            from app.services.nucleus_organization_service import NucleusOrganizationService
            from app.services.organization_service import OrganizationService

            SessionDep = Annotated[AsyncSession, Depends(get_session)]
            MOCK_USER_HEADER = "X-Mock-User-Id"


            def get_user_repository(session: SessionDep) -> UserRepository:
                return UserRepository(session)


            def get_audit_repository(session: SessionDep) -> AuditRepository:
                return AuditRepository(session)


            def get_nucleus_organization_repository(
                session: SessionDep,
            ) -> NucleusOrganizationRepository:
                return NucleusOrganizationRepository(session)


            NucleusOrganizationRepositoryDep = Annotated[
                NucleusOrganizationRepository,
                Depends(get_nucleus_organization_repository),
            ]


            def get_nucleus_organization_gateway(
                repository: NucleusOrganizationRepositoryDep,
            ) -> NucleusOrganizationGateway:
                return repository


            NucleusOrganizationGatewayDep = Annotated[
                NucleusOrganizationGateway,
                Depends(get_nucleus_organization_gateway),
            ]


            def get_mock_organization_api(session: SessionDep) -> MockOrganizationApi:
                return MockOrganizationApi(session)


            MockOrganizationApiDep = Annotated[
                MockOrganizationApi, Depends(get_mock_organization_api)
            ]


            def get_organization_gateway(
                api: MockOrganizationApiDep,
            ) -> MockOrganizationApiAdapter:
                return MockOrganizationApiAdapter(api)


            OrganizationGatewayDep = Annotated[
                OrganizationApiGateway,
                Depends(get_organization_gateway),
            ]
            VersionedOrganizationMutationGatewayDep = Annotated[
                VersionedOrganizationMutationGateway,
                Depends(get_organization_gateway),
            ]


            def get_organization_service(
                organization_gateway: OrganizationGatewayDep,
                user_repo: Annotated[UserRepository, Depends(get_user_repository)],
                audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
            ) -> OrganizationService:
                return OrganizationService(
                    organization_gateway=organization_gateway,
                    permission_service=PermissionService(user_repo),
                    audit_repository=audit_repo,
                )


            def get_nucleus_organization_service(
                organization_gateway: OrganizationGatewayDep,
                user_repo: Annotated[UserRepository, Depends(get_user_repository)],
                audit_repo: Annotated[AuditRepository, Depends(get_audit_repository)],
                nucleus_gateway: NucleusOrganizationGatewayDep,
            ) -> NucleusOrganizationService:
                return NucleusOrganizationService(
                    organization_gateway=organization_gateway,
                    permission_service=PermissionService(user_repo),
                    nucleus_gateway=nucleus_gateway,
                    audit_repository=audit_repo,
                )


            async def get_authenticated_user(
                user_repo: Annotated[UserRepository, Depends(get_user_repository)],
                x_mock_user_id: Annotated[str | None, Header(alias=MOCK_USER_HEADER)] = None,
            ) -> User:
                if not x_mock_user_id:
                    raise UnauthenticatedError("Missing X-Mock-User-Id header")
                user = await user_repo.get_by_id(x_mock_user_id)
                if user is None:
                    raise UnauthenticatedError("Unknown user")
                if not user.is_active:
                    raise UserDisabledError()
                return user


            UserDep = Annotated[User, Depends(get_authenticated_user)]
            OrganizationServiceDep = Annotated[
                OrganizationService, Depends(get_organization_service)
            ]
            NucleusOrganizationServiceDep = Annotated[
                NucleusOrganizationService,
                Depends(get_nucleus_organization_service),
            ]
            '''
        ),
    )

    write_text(
        root,
        "app/api/action_dependencies.py",
        clean_block(
            '''
            from __future__ import annotations

            from typing import Annotated

            from fastapi import Depends

            from app.agent.action_contracts import AgentActionHandler
            from app.agent.action_handlers import (
                ActivateOrganizationMembershipHandler,
                AssignOrganizationSeatHandler,
                GrantOrganizationReportAccessHandler,
                InviteOrganizationUserHandler,
                RemoveOrganizationUserHandler,
                RevokeOrganizationReportAccessHandler,
                RevokeOrganizationSeatHandler,
                UpdateOrganizationMemberRoleHandler,
            )
            from app.agent.action_registry import AgentActionRegistry
            from app.agent.nucleus_action_handlers import (
                ClearNucleusOrganizationAccountFieldHandler,
                GrantNucleusCategoryAccessHandler,
                GrantNucleusReportAccessHandler,
                RevokeNucleusCategoryAccessHandler,
                RevokeNucleusReportAccessHandler,
                UpdateNucleusOrganizationAccountFieldHandler,
                UpdateNucleusOrganizationPermissionsHandler,
                UpdateOrganizationContactEmailBridgeHandler,
            )
            from app.api.dependencies import (
                NucleusOrganizationGatewayDep,
                OrganizationGatewayDep,
                SessionDep,
                VersionedOrganizationMutationGatewayDep,
                get_audit_repository,
                get_user_repository,
            )
            from app.permissions.permission_service import PermissionService
            from app.repositories.agent_action_repository import AgentActionRepository
            from app.repositories.audit_repository import AuditRepository
            from app.repositories.hardened_agent_action_repository import (
                HardenedAgentActionRepository,
            )
            from app.repositories.user_repository import UserRepository
            from app.services.agent_action_reconciliation_service import AgentActionReconciliationService
            from app.services.operational_resource_service import OperationalResourceService
            from app.services.release_ready_agent_action_service import ReleaseReadyAgentActionService


            def get_agent_action_repository(session: SessionDep) -> AgentActionRepository:
                return HardenedAgentActionRepository(session)


            def get_agent_action_registry() -> AgentActionRegistry:
                return AgentActionRegistry()


            def get_agent_action_handlers(
                session: SessionDep,
                nucleus: NucleusOrganizationGatewayDep,
                organization_mutations: VersionedOrganizationMutationGatewayDep,
            ) -> dict[str, AgentActionHandler]:
                resources = OperationalResourceService(session)
                return {
                    "update_organization_contact_email": (
                        UpdateOrganizationContactEmailBridgeHandler(
                            nucleus,
                            organization_mutations,
                        )
                    ),
                    "update_nucleus_organization_account_field": (
                        UpdateNucleusOrganizationAccountFieldHandler(
                            nucleus,
                            organization_mutations,
                        )
                    ),
                    "clear_nucleus_organization_account_field": (
                        ClearNucleusOrganizationAccountFieldHandler(
                            nucleus,
                            organization_mutations,
                        )
                    ),
                    "grant_nucleus_category_access": GrantNucleusCategoryAccessHandler(nucleus),
                    "revoke_nucleus_category_access": RevokeNucleusCategoryAccessHandler(nucleus),
                    "grant_nucleus_report_access": GrantNucleusReportAccessHandler(nucleus),
                    "revoke_nucleus_report_access": RevokeNucleusReportAccessHandler(nucleus),
                    "update_nucleus_organization_permissions": (
                        UpdateNucleusOrganizationPermissionsHandler(nucleus)
                    ),
                    "invite_organization_user": InviteOrganizationUserHandler(resources),
                    "activate_organization_membership": ActivateOrganizationMembershipHandler(
                        resources
                    ),
                    "update_organization_member_role": UpdateOrganizationMemberRoleHandler(
                        resources
                    ),
                    "remove_organization_user": RemoveOrganizationUserHandler(resources),
                    "assign_organization_seat": AssignOrganizationSeatHandler(resources),
                    "revoke_organization_seat": RevokeOrganizationSeatHandler(resources),
                    "grant_organization_report_access": GrantOrganizationReportAccessHandler(
                        resources
                    ),
                    "revoke_organization_report_access": RevokeOrganizationReportAccessHandler(
                        resources
                    ),
                }


            def get_agent_action_service(
                organization_gateway: OrganizationGatewayDep,
                user_repository: Annotated[UserRepository, Depends(get_user_repository)],
                audit_repository: Annotated[AuditRepository, Depends(get_audit_repository)],
                action_repository: Annotated[
                    AgentActionRepository,
                    Depends(get_agent_action_repository),
                ],
                action_registry: Annotated[
                    AgentActionRegistry,
                    Depends(get_agent_action_registry),
                ],
                action_handlers: Annotated[
                    dict[str, AgentActionHandler],
                    Depends(get_agent_action_handlers),
                ],
            ) -> ReleaseReadyAgentActionService:
                return ReleaseReadyAgentActionService(
                    organization_gateway=organization_gateway,
                    permission_service=PermissionService(user_repository),
                    action_repository=action_repository,
                    audit_repository=audit_repository,
                    action_registry=action_registry,
                    action_handlers=action_handlers,
                )


            def get_agent_action_reconciliation_service(
                action_service: Annotated[
                    ReleaseReadyAgentActionService,
                    Depends(get_agent_action_service),
                ],
            ) -> AgentActionReconciliationService:
                return AgentActionReconciliationService(action_service)


            AgentActionServiceDep = Annotated[
                ReleaseReadyAgentActionService,
                Depends(get_agent_action_service),
            ]
            AgentActionReconciliationServiceDep = Annotated[
                AgentActionReconciliationService,
                Depends(get_agent_action_reconciliation_service),
            ]
            '''
        ),
    )


def patch_health_and_migrations(root: Path) -> None:
    path = "app/api/health_routes.py"
    replace_exact(
        root,
        path,
        'EXPECTED_MIGRATION_HEAD = "0011_nucleus_organization_schema"\n',
        'EXPECTED_MIGRATION_HEAD = "0012_resource_preconditions"\n',
    )
    replace_exact(
        root,
        path,
        "    registry_names = {\n",
        indent_block(
            '''
            try:
                await session.execute(
                    text(
                        "SELECT resource_preconditions_json, fingerprint_version "
                        "FROM agent_action_proposals LIMIT 1"
                    )
                )
                proposal_preconditions_supported = True
            except SQLAlchemyError:
                await session.rollback()
                proposal_preconditions_supported = False

            registry_names = {
            ''',
            4,
        ),
    )
    replace_exact(
        root,
        path,
        '        "migration_at_expected_head": migration_head == EXPECTED_MIGRATION_HEAD,\n'
        '        "registry_handler_parity": registry_names == handler_names,\n',
        '        "migration_at_expected_head": migration_head == EXPECTED_MIGRATION_HEAD,\n'
        '        "proposal_resource_preconditions_supported": proposal_preconditions_supported,\n'
        '        "registry_handler_parity": registry_names == handler_names,\n',
    )

    path = "tests/test_migrations.py"
    replace_exact(root, path, "import os\n", "import json\nimport os\n")
    replace_exact(
        root,
        path,
        'EXPECTED_HEAD = "0011_nucleus_organization_schema"\n',
        'EXPECTED_HEAD = "0012_resource_preconditions"\n',
    )
    replace_exact(
        root,
        path,
        "    proposal_indexes = read_index_names(connection, \"agent_action_proposals\")\n",
        indent_block(
            '''
            proposal_columns = read_column_names(connection, "agent_action_proposals")
            assert {
                "resource_preconditions_json",
                "fingerprint_version",
            }.issubset(proposal_columns)

            proposal_indexes = read_index_names(connection, "agent_action_proposals")
            ''',
            4,
        ),
    )
    replace_exact(
        root,
        path,
        "        execution = connection.execute(\n"
        "            \"SELECT id, outcome, audit_pending, audit_replay_attempts, \"\n",
        indent_block(
            '''
            proposal = connection.execute(
                "SELECT resource_preconditions_json, fingerprint_version "
                "FROM agent_action_proposals WHERE id = 'proposal_upgrade_001'"
            ).fetchone()
            assert proposal is not None
            assert json.loads(proposal[0]) == [
                {
                    "resource_type": "organization",
                    "resource_id": "org_upgrade_001",
                    "observed_version": 1,
                }
            ]
            assert proposal[1] == 2

            execution = connection.execute(
                "SELECT id, outcome, audit_pending, audit_replay_attempts, "
            ''',
            8,
        ),
    )

def patch_existing_tests(root: Path) -> None:
    path = "tests/test_agent_action_security.py"
    replace_exact(
        root,
        path,
        "from app.agent.action_contracts import AgentActionChange, AgentApprovalPolicy\n",
        "from app.agent.action_contracts import (\n"
        "    AgentActionChange,\n"
        "    AgentActionResourcePrecondition,\n"
        "    AgentApprovalPolicy,\n"
        ")\n",
    )
    replace_exact(
        root,
        path,
        '        "resource_id": "org_001",\n'
        '        "expires_at": datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),\n',
        '        "resource_id": "org_001",\n'
        '        "resource_preconditions": (\n'
        '            AgentActionResourcePrecondition(\n'
        '                resource_type="organization",\n'
        '                resource_id="org_001",\n'
        '                observed_version=1,\n'
        '            ),\n'
        '        ),\n'
        '        "fingerprint_version": 3,\n'
        '        "expires_at": datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc),\n',
    )
    replace_exact(
        root,
        path,
        "        build_fingerprint(resource_id=\"org_002\"),\n",
        "        build_fingerprint(resource_id=\"org_002\"),\n"
        "        build_fingerprint(\n"
        "            resource_preconditions=(\n"
        "                AgentActionResourcePrecondition(\n"
        "                    resource_type=\"organization\",\n"
        "                    resource_id=\"org_001\",\n"
        "                    observed_version=2,\n"
        "                ),\n"
        "            )\n"
        "        ),\n",
    )
    replace_exact(root, path, "    assert len(variants) == 8\n", "    assert len(variants) == 9\n")
    replace_exact(
        root,
        path,
        clean_block(
            '''
            def test_action_fingerprint_treats_naive_sqlite_datetime_as_utc() -> None:
                aware = datetime(2026, 7, 17, 12, 0, 0, 123456, tzinfo=timezone.utc)
                naive = aware.replace(tzinfo=None)

                assert build_fingerprint(expires_at=aware) == build_fingerprint(expires_at=naive)
            '''
        ),
        clean_block(
            '''
            def test_action_fingerprint_treats_naive_sqlite_datetime_as_utc() -> None:
                aware = datetime(2026, 7, 17, 12, 0, 0, 123456, tzinfo=timezone.utc)
                naive = aware.replace(tzinfo=None)

                assert build_fingerprint(expires_at=aware) == build_fingerprint(expires_at=naive)


            def test_version_two_fingerprint_remains_backward_compatible() -> None:
                assert build_fingerprint(fingerprint_version=2) == (
                    "2f612e8430834954193e3046d794074bccf5f483ce59887399cb9b0ceb7c0a86"
                )
            '''
        ),
    )

    path = "tests/test_agent_action_query.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "contact_email",
                    "before": "operations@example.test",
                    "after": "agent.operations@example.test",
                }
            ]
            ''',
            4,
        ),
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "nucleus.Email",
                    "before": "operations@example.test",
                    "after": "agent.operations@example.test",
                },
                {
                    "field": "organization.contact_email",
                    "before": "operations@example.test",
                    "after": "agent.operations@example.test",
                },
            ]
            ''',
            4,
        ),
    )

    path = "tests/test_agent_actions.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "contact_email",
                    "before": "operations@example.test",
                    "after": "new.operations@example.test",
                }
            ]
            ''',
            4,
        ),
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "nucleus.Email",
                    "before": "operations@example.test",
                    "after": "new.operations@example.test",
                },
                {
                    "field": "organization.contact_email",
                    "before": "operations@example.test",
                    "after": "new.operations@example.test",
                },
            ]
            assert len(proposal["resource_preconditions"]) == 2
            ''',
            4,
        ),
    )
    replace_exact(
        root,
        path,
        indent_block(
            '''
            assert execution["result"] == {
                "resource_type": "organization",
                "resource_id": ORGANIZATION_ID,
                "before": {"contact_email": "operations@example.test", "version": 1},
                "after": {"contact_email": "new.operations@example.test", "version": 2},
                "external_operation_id": None,
            }
            ''',
            4,
        ),
        indent_block(
            '''
            assert execution["result"] == {
                "resource_type": "organization",
                "resource_id": ORGANIZATION_ID,
                "before": {
                    "contact_email": "operations@example.test",
                    "version": 1,
                    "nucleus_version": 1,
                },
                "after": {
                    "contact_email": "new.operations@example.test",
                    "version": 2,
                    "nucleus_version": 2,
                },
                "external_operation_id": None,
            }
            ''',
            4,
        ),
    )

    path = "tests/test_multi_approval_and_rollback.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            assert rollback["changes"] == [
                {
                    "field": "contact_email",
                    "before": "changed@example.test",
                    "after": "operations@example.test",
                }
            ]
            ''',
            4,
        ),
        indent_block(
            '''
            assert rollback["changes"] == [
                {
                    "field": "nucleus.Email",
                    "before": "changed@example.test",
                    "after": "operations@example.test",
                },
                {
                    "field": "organization.contact_email",
                    "before": "changed@example.test",
                    "after": "operations@example.test",
                },
            ]
            ''',
            4,
        ),
    )

    path = "tests/test_nucleus_organization_actions.py"
    replace_exact(
        root,
        path,
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "OrganizationName",
                    "before": "Demo Enterprise Sandbox",
                    "after": "Updated Nucleus Sandbox",
                }
            ]
            ''',
            4,
        ),
        indent_block(
            '''
            assert proposal["changes"] == [
                {
                    "field": "OrganizationName",
                    "before": "Demo Enterprise Sandbox",
                    "after": "Updated Nucleus Sandbox",
                },
                {
                    "field": "organization.display_name",
                    "before": "Demo Enterprise Sandbox",
                    "after": "Updated Nucleus Sandbox",
                },
            ]
            assert len(proposal["resource_preconditions"]) == 2
            ''',
            4,
        ),
    )

    path = "tests/test_operational_hardening.py"
    replace_exact(
        root,
        path,
        '    assert body["checks"]["registry_handler_parity"] is True\n',
        '    assert body["checks"]["registry_handler_parity"] is True\n'
        '    assert body["checks"]["proposal_resource_preconditions_supported"] is True\n',
    )
    replace_exact(
        root,
        path,
        '    assert body["migration"]["expected"] == "0011_nucleus_organization_schema"\n',
        '    assert body["migration"]["expected"] == "0012_resource_preconditions"\n',
    )

    path = "tests/test_nucleus_gateway_boundary.py"
    replace_exact(
        root,
        path,
        "from app.adapters.nucleus.contract import NucleusOrganizationGateway\n",
        "from app.adapters.nucleus.contract import NucleusOrganizationGateway\n"
        "from app.agent.action_contracts import VersionedOrganizationMutationGateway\n",
    )
    replace_exact(
        root,
        path,
        clean_block(
            '''
            @pytest.mark.parametrize("handler_type", HANDLER_TYPES)
            def test_nucleus_action_handler_depends_on_gateway_port(handler_type: type) -> None:
                hints = get_type_hints(handler_type.__init__)
                assert hints["gateway"] is NucleusOrganizationGateway
            '''
        ),
        clean_block(
            '''
            @pytest.mark.parametrize("handler_type", HANDLER_TYPES)
            def test_nucleus_action_handler_depends_on_gateway_port(handler_type: type) -> None:
                hints = get_type_hints(handler_type.__init__)
                assert hints["gateway"] is NucleusOrganizationGateway


            @pytest.mark.parametrize(
                "handler_type",
                (
                    UpdateOrganizationContactEmailBridgeHandler,
                    UpdateNucleusOrganizationAccountFieldHandler,
                    ClearNucleusOrganizationAccountFieldHandler,
                ),
            )
            def test_projected_account_handlers_depend_on_organization_mutation_port(
                handler_type: type,
            ) -> None:
                hints = get_type_hints(handler_type.__init__)
                assert (
                    hints["organization_gateway"]
                    is VersionedOrganizationMutationGateway
                )
            '''
        ),
    )

def add_tests(root: Path) -> None:
    create_exact(
        root,
        "tests/test_action_resource_preconditions.py",
        clean_block(
            '''
            from __future__ import annotations

            from httpx import AsyncClient
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.db.action_models import AgentActionProposalORM

            ORGANIZATION_ID = "org_sandbox_001"
            ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


            async def test_single_resource_action_persists_one_precondition(
                client: AsyncClient,
                admin_headers: dict[str, str],
            ) -> None:
                response = await client.post(
                    f"{ACTION_BASE}/propose",
                    headers=admin_headers,
                    json={
                        "action_name": "clear_nucleus_organization_account_field",
                        "arguments": {"field_name": "Website"},
                    },
                )
                assert response.status_code == 200
                proposal = response.json()["proposal"]
                assert proposal["fingerprint_version"] == 3
                assert proposal["resource_preconditions"] == [
                    {
                        "resource_type": "OrganizationAccount",
                        "resource_id": "1",
                        "observed_version": 1,
                    }
                ]


            async def test_contact_email_action_persists_both_reviewed_resources(
                client: AsyncClient,
                admin_headers: dict[str, str],
            ) -> None:
                response = await client.post(
                    f"{ACTION_BASE}/propose",
                    headers=admin_headers,
                    json={
                        "action_name": "update_organization_contact_email",
                        "arguments": {"contact_email": "two-resource@example.test"},
                    },
                )
                assert response.status_code == 200
                proposal = response.json()["proposal"]
                assert proposal["fingerprint_version"] == 3
                assert {
                    (item["resource_type"], item["resource_id"])
                    for item in proposal["resource_preconditions"]
                } == {
                    ("OrganizationAccount", "1"),
                    ("organization", ORGANIZATION_ID),
                }


            async def test_tampered_resource_precondition_invalidates_fingerprint(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                response = await client.post(
                    f"{ACTION_BASE}/propose",
                    headers=admin_headers,
                    json={
                        "action_name": "update_organization_contact_email",
                        "arguments": {"contact_email": "precondition@example.test"},
                    },
                )
                proposal_id = response.json()["proposal"]["id"]
                approved = await client.post(
                    f"{ACTION_BASE}/{proposal_id}/approve",
                    headers=admin_headers,
                    json={"reason": "Reviewed"},
                )
                assert approved.status_code == 200

                row = await db_session.get(AgentActionProposalORM, proposal_id)
                assert row is not None
                tampered = list(row.resource_preconditions_json)
                tampered[0] = {**tampered[0], "observed_version": 999}
                row.resource_preconditions_json = tampered
                await db_session.commit()

                executed = await client.post(
                    f"{ACTION_BASE}/{proposal_id}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "tampered-precondition-001"},
                )
                assert executed.status_code == 409
                assert executed.json()["error"]["code"] == "agent_action_state_conflict"
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_nucleus_projection_synchronization.py",
        clean_block(
            '''
            from __future__ import annotations

            from httpx import AsyncClient
            from sqlalchemy import select
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter
            from app.agent.nucleus_action_handlers import (
                UpdateOrganizationContactEmailBridgeHandler,
            )
            from app.api.action_dependencies import get_agent_action_handlers
            from app.db.nucleus_models import NucleusOrganizationAccountORM
            from app.db.orm_models import OrganizationORM, OrganizationOverviewORM
            from app.main import app
            from app.mock_api.service import MockOrganizationApi
            from app.repositories.nucleus_organization_repository import (
                NucleusOrganizationRepository,
            )

            ORGANIZATION_ID = "org_sandbox_001"
            ACTION_BASE = f"/workplace/organizations/{ORGANIZATION_ID}/agent/actions"


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
                assert response.status_code == 200
                return response.json()["proposal"]


            async def _approve(
                client: AsyncClient,
                headers: dict[str, str],
                proposal_id: str,
            ) -> None:
                response = await client.post(
                    f"{ACTION_BASE}/{proposal_id}/approve",
                    headers=headers,
                    json={"reason": "Reviewed projection state"},
                )
                assert response.status_code == 200


            class FailFirstContactProjectionGateway:
                def __init__(self, delegate: MockOrganizationApiAdapter) -> None:
                    self._delegate = delegate
                    self._fail_contact_update = True

                async def get_profile(self, organization_id: str):
                    return await self._delegate.get_profile(organization_id)

                async def get_overview(self, organization_id: str):
                    return await self._delegate.get_overview(organization_id)

                async def update_contact_email_if_version(
                    self,
                    organization_id: str,
                    contact_email: str | None,
                    expected_version: int,
                ):
                    if self._fail_contact_update:
                        self._fail_contact_update = False
                        return None
                    return await self._delegate.update_contact_email_if_version(
                        organization_id,
                        contact_email,
                        expected_version,
                    )

                async def update_display_name_if_version(
                    self,
                    organization_id: str,
                    display_name: str,
                    expected_version: int,
                ):
                    return await self._delegate.update_display_name_if_version(
                        organization_id,
                        display_name,
                        expected_version,
                    )

                async def update_organization_type_if_version(
                    self,
                    organization_id: str,
                    organization_type: str,
                    expected_version: int,
                ):
                    return await self._delegate.update_organization_type_if_version(
                        organization_id,
                        organization_type,
                        expected_version,
                    )


            def _install_fail_first_contact_handler(db_session: AsyncSession) -> None:
                nucleus = NucleusOrganizationRepository(db_session)
                projection = FailFirstContactProjectionGateway(
                    MockOrganizationApiAdapter(MockOrganizationApi(db_session))
                )
                handler = UpdateOrganizationContactEmailBridgeHandler(
                    nucleus,
                    projection,
                )
                app.dependency_overrides[get_agent_action_handlers] = lambda: {
                    "update_organization_contact_email": handler
                }


            async def test_legacy_profile_drift_marks_contact_action_stale(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_organization_contact_email",
                    {"contact_email": "approved-contact@example.test"},
                )
                await _approve(client, admin_headers, proposal["id"])

                organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
                assert organization is not None
                organization.contact_email = "concurrent@example.test"
                organization.version += 1
                await db_session.commit()

                response = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "legacy-drift-contact-001"},
                )
                assert response.status_code == 409
                assert response.json()["error"]["code"] == "agent_action_stale"


            async def test_nucleus_drift_marks_contact_action_stale(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_organization_contact_email",
                    {"contact_email": "approved-nucleus@example.test"},
                )
                await _approve(client, admin_headers, proposal["id"])

                account = await db_session.scalar(
                    select(NucleusOrganizationAccountORM).where(
                        NucleusOrganizationAccountORM.organization_code == ORGANIZATION_ID
                    )
                )
                assert account is not None
                account.email = "concurrent-nucleus@example.test"
                await db_session.commit()

                response = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "nucleus-drift-contact-001"},
                )
                assert response.status_code == 409
                assert response.json()["error"]["code"] == "agent_action_stale"


            async def test_partial_contact_update_reconciles_missing_projection_once(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                _install_fail_first_contact_handler(db_session)
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_organization_contact_email",
                    {"contact_email": "repaired-projection@example.test"},
                )
                await _approve(client, admin_headers, proposal["id"])

                execute = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "partial-contact-projection-001"},
                )
                assert execute.status_code == 409
                assert execute.json()["error"]["code"] == (
                    "agent_action_reconciliation_required"
                )

                account = await db_session.scalar(
                    select(NucleusOrganizationAccountORM).where(
                        NucleusOrganizationAccountORM.organization_code == ORGANIZATION_ID
                    )
                )
                organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
                assert account is not None
                assert organization is not None
                await db_session.refresh(account)
                await db_session.refresh(organization)
                assert account.email == "repaired-projection@example.test"
                assert organization.contact_email == "operations@example.test"

                reconciled = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/reconcile",
                    headers=admin_headers,
                )
                assert reconciled.status_code == 200
                execution = reconciled.json()["execution"]
                assert execution["outcome"] == "succeeded"
                assert execution["reconciliation_status"] == "resolved"

                await db_session.refresh(organization)
                assert organization.contact_email == "repaired-projection@example.test"
                assert organization.version == 2

                repeated = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/reconcile",
                    headers=admin_headers,
                )
                assert repeated.status_code == 200
                assert repeated.json()["execution"] == execution


            async def test_reconciliation_does_not_overwrite_conflicting_projection(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                _install_fail_first_contact_handler(db_session)
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_organization_contact_email",
                    {"contact_email": "must-not-overwrite@example.test"},
                )
                await _approve(client, admin_headers, proposal["id"])
                execute = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "conflicting-projection-001"},
                )
                assert execute.status_code == 409

                organization = await db_session.get(OrganizationORM, ORGANIZATION_ID)
                assert organization is not None
                organization.contact_email = "newer-human-change@example.test"
                organization.version += 1
                await db_session.commit()

                reconciled = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/reconcile",
                    headers=admin_headers,
                )
                assert reconciled.status_code == 200
                assert reconciled.json()["execution"]["outcome"] == (
                    "reconciliation_required"
                )
                await db_session.refresh(organization)
                assert organization.contact_email == "newer-human-change@example.test"


            async def test_organization_type_updates_nucleus_and_overview_projection(
                client: AsyncClient,
                db_session: AsyncSession,
                admin_headers: dict[str, str],
            ) -> None:
                proposal = await _propose(
                    client,
                    admin_headers,
                    "update_nucleus_organization_account_field",
                    {"field_name": "OrganizationType", "value": "Research Network"},
                )
                assert {
                    item["resource_type"]
                    for item in proposal["resource_preconditions"]
                } == {"OrganizationAccount", "organization_overview"}
                await _approve(client, admin_headers, proposal["id"])
                response = await client.post(
                    f"{ACTION_BASE}/{proposal['id']}/execute",
                    headers=admin_headers,
                    json={"idempotency_key": "organization-type-sync-001"},
                )
                assert response.status_code == 200

                overview = await db_session.get(OrganizationOverviewORM, ORGANIZATION_ID)
                assert overview is not None
                await db_session.refresh(overview)
                assert overview.organization_type == "Research Network"
                assert overview.version == 2
            '''
        ),
    )


def patch_documentation(root: Path) -> None:
    replace_exact(
        root,
        "docs/ARCHITECTURE.md",
        "→ proposal fingerprint recheck\n"
        "→ sidecar version compare-and-advance\n",
        "→ proposal fingerprint and all resource-precondition recheck\n"
        "→ sidecar version compare-and-advance\n",
    )
    replace_exact(
        root,
        "docs/ARCHITECTURE.md",
        "The existing `update_organization_contact_email` action now uses the exact\n"
        "Nucleus account as canonical storage and keeps the legacy Overview profile in\n"
        "sync.\n",
        "The existing `update_organization_contact_email` action uses the exact Nucleus\n"
        "account as canonical storage and coordinates the legacy Overview projection at\n"
        "the action layer. OrganizationName, Email and OrganizationType proposals bind\n"
        "approval to both reviewed resource versions. A partial cross-store outcome is\n"
        "reconciled without silently overwriting an unexpected concurrent value.\n",
    )
    replace_exact(
        root,
        "README.md",
        "Every write follows:\n\n"
        "```text\n"
        "inspect\n"
        "→ immutable before/after proposal\n"
        "→ approval threshold\n"
        "→ permission and fingerprint revalidation\n"
        "→ optimistic version check\n",
        "Every write follows:\n\n"
        "```text\n"
        "inspect\n"
        "→ immutable before/after proposal\n"
        "→ approval threshold\n"
        "→ permission, fingerprint and all resource-precondition revalidation\n"
        "→ optimistic version check\n",
    )
    replace_exact(
        root,
        "README.md",
        "Current migration head:\n\n"
        "```text\n"
        "0011_nucleus_organization_schema\n"
        "```\n",
        "Current migration head:\n\n"
        "```text\n"
        "0012_resource_preconditions\n"
        "```\n",
    )
    replace_exact(
        root,
        "APPLY_AND_VALIDATE.md",
        "0011_nucleus_organization_schema (head)",
        "0012_resource_preconditions (head)",
    )
    replace_exact(
        root,
        "APPLY_AND_VALIDATE.md",
        "Readiness must report migration `0011_nucleus_organization_schema`",
        "Readiness must report migration `0012_resource_preconditions`",
    )
    replace_exact(
        root,
        "APPLY_AND_VALIDATE.md",
        'git commit -m "add Nucleus organization schema vertical slice"',
        'git commit -m "add multi-resource preconditions and projection synchronization"',
    )
    security_path = "docs/SECURITY_MODEL.md"
    security = read_text(root, security_path)
    security += clean_block(
        '''

        ## Multi-resource review binding

        New action proposals persist a canonical list of every reviewed resource and
        observed version. Fingerprint version 3 covers that complete list, while
        migrated version-2 proposals retain their original verification semantics.
        Execution re-prepares and compares all preconditions before consuming the
        approval. Cross-store reconciliation repairs only an unchanged reviewed
        projection and never overwrites a conflicting newer value.
        '''
    )
    write_text(root, security_path, security)


MODIFIED_PATHS = (
    "APPLY_AND_VALIDATE.md",
    "README.md",
    "app/adapters/nucleus/contract.py",
    "app/adapters/organization/mock_adapter.py",
    "app/agent/action_contracts.py",
    "app/agent/action_registry.py",
    "app/agent/nucleus_action_handlers.py",
    "app/api/action_dependencies.py",
    "app/api/dependencies.py",
    "app/api/health_routes.py",
    "app/db/action_models.py",
    "app/mock_api/service.py",
    "app/repositories/agent_action_repository.py",
    "app/repositories/nucleus_organization_repository.py",
    "app/repositories/organization_overview_repository.py",
    "app/repositories/organization_repository.py",
    "app/services/agent_action_service.py",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY_MODEL.md",
    "tests/test_agent_action_query.py",
    "tests/test_agent_action_security.py",
    "tests/test_agent_actions.py",
    "tests/test_migrations.py",
    "tests/test_multi_approval_and_rollback.py",
    "tests/test_nucleus_gateway_boundary.py",
    "tests/test_nucleus_organization_actions.py",
    "tests/test_operational_hardening.py",
)

NEW_PATHS = (
    "alembic/versions/0012_resource_preconditions.py",
    "tests/test_action_resource_preconditions.py",
    "tests/test_nucleus_projection_synchronization.py",
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
        replace_small_files(root)
        patch_action_registry(root)
        patch_action_persistence(root)
        add_migration(root)
        patch_action_service(root)
        patch_nucleus_gateway_and_repository(root)
        patch_organization_gateway_implementation(root)
        patch_nucleus_handlers(root)
        patch_dependencies(root)
        patch_health_and_migrations(root)
        patch_existing_tests(root)
        add_tests(root)
        patch_documentation(root)
    except Exception:
        restore_after_failure(root, backups, new_path_existed)
        raise

    print("Applied multi-resource preconditions and Nucleus projection synchronization.")
    print("No files were staged, committed, pushed, or deleted.")
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
