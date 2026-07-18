from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.workplace_resources.definitions import (
    WorkplaceFieldPolicy,
    WorkplaceResourceDefinition,
)
from app.workplace_resources.registry import WorkplaceResourceRegistry

_SUPPORTED_OPERATORS = frozenset(
    {
        "equals",
        "not_equals",
        "contains",
        "starts_with",
        "in",
        "greater_than",
        "less_than",
        "between",
        "is_null",
        "is_not_null",
    }
)
_MAX_CONDITIONS = 20
_MAX_READ_SIZE = 100
_MAX_MUTATION_SIZE = 50


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return aware.astimezone(timezone.utc).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


@dataclass(frozen=True)
class FrozenWorkplaceTargetSet:
    resource_type: str
    query: dict[str, Any]
    resource_ids: tuple[str, ...]
    versions: tuple[int, ...]
    snapshots: tuple[dict[str, Any], ...]
    target_set_hash: str

    @property
    def resource_count(self) -> int:
        return len(self.resource_ids)


class WorkplaceAdvancedQueryService:
    """Compile a small backend-owned query language into SQLAlchemy expressions."""

    def __init__(
        self,
        session: AsyncSession,
        registry: WorkplaceResourceRegistry | None = None,
    ) -> None:
        self._session = session
        self._registry = registry or WorkplaceResourceRegistry()

    @staticmethod
    def parse_query_json(raw_value: str, *, field_name: str = "query_json") -> dict[str, Any]:
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError as exception:
            raise ValueError(f"{field_name} must be valid JSON") from exception
        if not isinstance(parsed, dict):
            raise ValueError(f"{field_name} must be a JSON object")
        return parsed

    def normalize_query(
        self,
        *,
        resource_type: str,
        query: dict[str, Any],
        for_mutation: bool = False,
    ) -> dict[str, Any]:
        definition = self._generic_definition(resource_type)
        if set(query) - {"all", "any"}:
            raise ValueError("Query supports only all and any condition groups")
        all_conditions = query.get("all", [])
        any_conditions = query.get("any", [])
        if not isinstance(all_conditions, list) or not isinstance(any_conditions, list):
            raise ValueError("Query condition groups must be arrays")
        if not all_conditions and not any_conditions:
            if for_mutation:
                raise ValueError("Mutation queries must contain at least one condition")
            return {"all": [], "any": []}
        total = len(all_conditions) + len(any_conditions)
        if total > _MAX_CONDITIONS:
            raise ValueError("Query contains too many conditions")
        normalized = {
            "all": [
                self._normalize_condition(definition, item)
                for item in all_conditions
            ],
            "any": [
                self._normalize_condition(definition, item)
                for item in any_conditions
            ],
        }
        return normalized

    async def search(
        self,
        *,
        organization_id: str,
        resource_type: str,
        query: dict[str, Any],
        sort_by: str | None = None,
        descending: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[tuple[dict[str, Any], ...], int, dict[str, Any]]:
        definition = self._generic_definition(resource_type)
        normalized = self.normalize_query(
            resource_type=resource_type,
            query=query,
        )
        if limit < 1 or limit > _MAX_READ_SIZE or offset < 0:
            raise ValueError("Invalid advanced-query pagination")
        conditions = self._conditions(
            definition,
            organization_id=organization_id,
            normalized_query=normalized,
        )
        order_column = getattr(definition.orm_type, definition.id_attribute)
        if sort_by is not None:
            policy = definition.field_map.get(sort_by)
            if policy is None or not policy.sortable or policy.sensitive:
                raise ValueError("Unsupported advanced-query sort")
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
        return (
            tuple(self._serialize(definition, row) for row in rows),
            total,
            normalized,
        )

    async def summarize(
        self,
        *,
        organization_id: str,
        resource_type: str,
        query: dict[str, Any],
    ) -> dict[str, Any]:
        items, total, normalized = await self.search(
            organization_id=organization_id,
            resource_type=resource_type,
            query=query,
            limit=10,
            offset=0,
        )
        definition = self._generic_definition(resource_type)
        active_count = None
        if definition.soft_delete_attribute:
            active_column = getattr(
                definition.orm_type,
                definition.soft_delete_attribute,
            )
            conditions = self._conditions(
                definition,
                organization_id=organization_id,
                normalized_query=normalized,
            )
            active_count = int(
                await self._session.scalar(
                    select(func.count())
                    .select_from(definition.orm_type)
                    .where(*conditions, active_column.is_(True))
                )
                or 0
            )
        return {
            "resource_type": resource_type,
            "query": normalized,
            "count": total,
            "active_count": active_count,
            "inactive_count": (
                total - active_count if active_count is not None else None
            ),
            "sample": items,
            "sample_truncated": total > len(items),
        }

    async def compare(
        self,
        *,
        organization_id: str,
        resource_type: str,
        resource_ids: tuple[str, ...],
    ) -> dict[str, Any]:
        if len(resource_ids) < 2 or len(resource_ids) > 10:
            raise ValueError("Comparison requires between two and ten resources")
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Comparison resource IDs must be unique")
        definition = self._generic_definition(resource_type)
        rows = []
        for resource_id in resource_ids:
            row = await self._row(
                definition,
                organization_id=organization_id,
                resource_id=resource_id,
            )
            if row is None:
                raise ValueError("Comparison resource was not found")
            rows.append(self._serialize(definition, row))
        differences: dict[str, list[Any]] = {}
        readable_names = [
            field.name
            for field in definition.fields
            if field.readable and not field.sensitive
        ]
        for name in readable_names:
            values = [item.get(name) for item in rows]
            if any(value != values[0] for value in values[1:]):
                differences[name] = values
        return {
            "resource_type": resource_type,
            "resource_ids": list(resource_ids),
            "items": rows,
            "differences": differences,
        }

    async def freeze_for_mutation(
        self,
        *,
        organization_id: str,
        resource_type: str,
        query: dict[str, Any],
    ) -> FrozenWorkplaceTargetSet:
        definition = self._generic_definition(resource_type)
        normalized = self.normalize_query(
            resource_type=resource_type,
            query=query,
            for_mutation=True,
        )
        conditions = self._conditions(
            definition,
            organization_id=organization_id,
            normalized_query=normalized,
        )
        id_column = getattr(definition.orm_type, definition.id_attribute)
        statement = (
            select(definition.orm_type)
            .where(*conditions)
            .order_by(id_column.asc())
            .limit(_MAX_MUTATION_SIZE + 1)
        )
        rows = tuple((await self._session.execute(statement)).scalars().all())
        if not rows:
            raise ValueError("Mutation query matched no resources")
        if len(rows) > _MAX_MUTATION_SIZE:
            raise ValueError("Mutation query matched more than fifty resources")
        ids = tuple(str(getattr(row, definition.id_attribute)) for row in rows)
        versions = tuple(self._version(definition, row) for row in rows)
        snapshots = tuple(self._serialize(definition, row) for row in rows)
        digest_payload = {
            "organization_id": organization_id,
            "resource_type": resource_type,
            "query": normalized,
            "targets": [
                {"resource_id": resource_id, "version": version}
                for resource_id, version in zip(ids, versions, strict=True)
            ],
        }
        return FrozenWorkplaceTargetSet(
            resource_type=resource_type,
            query=normalized,
            resource_ids=ids,
            versions=versions,
            snapshots=snapshots,
            target_set_hash=hashlib.sha256(
                _canonical_json(digest_payload).encode("utf-8")
            ).hexdigest(),
        )

    def _generic_definition(self, resource_type: str) -> WorkplaceResourceDefinition:
        definition = self._registry.get(resource_type)
        if definition.orm_type is None or definition.organization_attribute is None:
            raise ValueError(
                "This resource uses a dedicated organization-scoped adapter"
            )
        if "search" not in definition.operations:
            raise ValueError("This resource does not support governed search")
        return definition

    def _normalize_condition(
        self,
        definition: WorkplaceResourceDefinition,
        raw: Any,
    ) -> dict[str, Any]:
        if not isinstance(raw, dict) or set(raw) - {"field", "operator", "value"}:
            raise ValueError("Each query condition must contain field, operator and value")
        field_name = raw.get("field")
        operator = raw.get("operator")
        if not isinstance(field_name, str) or not isinstance(operator, str):
            raise ValueError("Query field and operator must be strings")
        if operator not in _SUPPORTED_OPERATORS:
            raise ValueError("Unsupported query operator")
        policy = definition.field_map.get(field_name)
        if policy is None or not policy.searchable or policy.sensitive:
            raise ValueError(f"Unsupported query field: {field_name}")
        requires_value = operator not in {"is_null", "is_not_null"}
        if requires_value and "value" not in raw:
            raise ValueError("Query condition value is required")
        if not requires_value and "value" in raw and raw["value"] is not None:
            raise ValueError("Null-check operators do not accept a value")
        value = raw.get("value")
        if operator == "in":
            if not isinstance(value, list) or not value or len(value) > 50:
                raise ValueError("The in operator requires one to fifty values")
            value = [self._coerce(policy, item) for item in value]
        elif operator == "between":
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("The between operator requires exactly two values")
            value = [self._coerce(policy, item) for item in value]
        elif requires_value:
            value = self._coerce(policy, value)
        if operator in {"contains", "starts_with"} and policy.kind != "string":
            raise ValueError("String matching operators require a string field")
        if operator in {"greater_than", "less_than", "between"} and policy.kind not in {
            "integer",
            "date",
            "datetime",
        }:
            raise ValueError(
                "Ordered comparison operators require an integer or date field"
            )
        return {"field": field_name, "operator": operator, "value": value}

    def _conditions(
        self,
        definition: WorkplaceResourceDefinition,
        *,
        organization_id: str,
        normalized_query: dict[str, Any],
    ) -> list[Any]:
        scope_column = getattr(
            definition.orm_type,
            definition.organization_attribute,
        )
        conditions: list[Any] = [scope_column == organization_id]
        all_expressions = [
            self._expression(definition, item)
            for item in normalized_query["all"]
        ]
        any_expressions = [
            self._expression(definition, item)
            for item in normalized_query["any"]
        ]
        if all_expressions:
            conditions.append(and_(*all_expressions))
        if any_expressions:
            conditions.append(or_(*any_expressions))
        return conditions

    @staticmethod
    def _expression(
        definition: WorkplaceResourceDefinition,
        condition: dict[str, Any],
    ) -> Any:
        policy = definition.field_map[condition["field"]]
        column = getattr(definition.orm_type, policy.attribute)
        operator = condition["operator"]
        value = condition["value"]
        if operator == "equals":
            return column.is_(None) if value is None else column == value
        if operator == "not_equals":
            return column.is_not(None) if value is None else column != value
        if operator == "contains":
            return column.contains(value)
        if operator == "starts_with":
            return column.startswith(value)
        if operator == "in":
            return column.in_(value)
        if operator == "greater_than":
            return column > value
        if operator == "less_than":
            return column < value
        if operator == "between":
            return column.between(value[0], value[1])
        if operator == "is_null":
            return column.is_(None)
        if operator == "is_not_null":
            return column.is_not(None)
        raise ValueError("Unsupported query operator")

    @staticmethod
    def _coerce(policy: WorkplaceFieldPolicy, value: Any) -> Any:
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
        if policy.kind == "datetime":
            if isinstance(value, datetime):
                return value
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError as exception:
                raise ValueError(f"{policy.name} must be an ISO datetime") from exception
            return parsed
        if policy.kind == "date":
            if isinstance(value, date) and not isinstance(value, datetime):
                return value
            try:
                return date.fromisoformat(str(value))
            except ValueError as exception:
                raise ValueError(f"{policy.name} must be an ISO date") from exception
        if policy.kind == "json":
            return value
        raise ValueError(f"Unsupported query field type: {policy.kind}")

    async def _row(
        self,
        definition: WorkplaceResourceDefinition,
        *,
        organization_id: str,
        resource_id: str,
    ) -> Any | None:
        id_policy = next(
            (
                field
                for field in definition.fields
                if field.attribute == definition.id_attribute
            ),
            None,
        )
        coerced_id: Any = resource_id
        if id_policy is not None and id_policy.kind == "integer":
            try:
                coerced_id = int(resource_id)
            except ValueError as exception:
                raise ValueError("Resource ID must be an integer") from exception
        return await self._session.scalar(
            select(definition.orm_type).where(
                getattr(
                    definition.orm_type,
                    definition.organization_attribute,
                )
                == organization_id,
                getattr(definition.orm_type, definition.id_attribute)
                == coerced_id,
            )
        )

    @staticmethod
    def _serialize(
        definition: WorkplaceResourceDefinition,
        row: Any,
    ) -> dict[str, Any]:
        return {
            field.name: _canonical(getattr(row, field.attribute))
            for field in definition.fields
            if field.readable and not field.sensitive
        }

    @staticmethod
    def _version(definition: WorkplaceResourceDefinition, row: Any) -> int:
        if definition.version_attribute is None:
            return 0
        return int(getattr(row, definition.version_attribute))
