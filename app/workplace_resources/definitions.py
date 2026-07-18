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
