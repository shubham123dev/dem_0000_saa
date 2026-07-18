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
            batch_id = hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
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
        executor_user_id: str,
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
                    deleted_by_user_id=executor_user_id,
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
