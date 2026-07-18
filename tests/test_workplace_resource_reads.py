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
