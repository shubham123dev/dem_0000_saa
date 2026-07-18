from __future__ import annotations

from app.agent.action_registry import AgentActionRegistry
from app.domain.enums import Permission, ROLE_PERMISSIONS, Role


def test_full_admin_surface_is_registered_with_scoped_policies() -> None:
    definitions = AgentActionRegistry().list_definitions()
    assert len(definitions) == 43
    by_name = {definition.name: definition for definition in definitions}
    assert by_name["update_nucleus_organization_license"].risk_level == "high"
    assert (
        by_name["update_nucleus_organization_license"]
        .approval_policy.minimum_approvals
        == 2
    )
    assert not (
        by_name["update_nucleus_organization_license"]
        .approval_policy.self_approval_allowed
    )
    assert (
        by_name["revoke_nucleus_market_access"].required_permission
        == Permission.ORGANIZATION_ENTITLEMENTS_DELETE.value
    )
    assert (
        by_name["activate_nucleus_organization_account"]
        .allow_suspended_organization
        is True
    )
    assert all("password" not in name for name in by_name)


def test_sensitive_admin_permissions_are_admin_only() -> None:
    admin_permissions = set(ROLE_PERMISSIONS[Role.SANDBOX_ADMIN])
    reader_permissions = set(ROLE_PERMISSIONS[Role.SANDBOX_READER])
    expected = {
        Permission.ORGANIZATION_ACCOUNT_IDENTITY_UPDATE,
        Permission.ORGANIZATION_LICENSE_UPDATE,
        Permission.ORGANIZATION_LIFECYCLE_UPDATE,
        Permission.ORGANIZATION_ENTITLEMENTS_DELETE,
        Permission.WORKPLACE_WORKFLOWS_MANAGE,
    }
    assert expected.issubset(admin_permissions)
    assert expected.isdisjoint(reader_permissions)
