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
