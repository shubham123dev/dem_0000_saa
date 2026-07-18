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
def test_synchronized_organization_fields_are_not_generic_writes() -> None:
    definition = WorkplaceResourceRegistry().get("organization")
    assert definition.field_map["display_name"].editable is False
    assert definition.field_map["contact_email"].editable is False
    assert definition.field_map["contact_email"].clearable is False
    assert definition.field_map["legal_name"].editable is True
