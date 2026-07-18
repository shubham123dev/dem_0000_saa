from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Literal

from app.agent.action_contracts import AgentActionProposalInput
from app.workplace_resources.registry import WorkplaceResourceRegistry

RouteKind = Literal["tool", "action"]


@dataclass(frozen=True)
class WorkplaceOperationRoute:
    resource_type: str
    operation: str
    route_kind: RouteKind
    target_name: str
    fields: tuple[str, ...] = ()
    argument_constants: tuple[tuple[str, str], ...] = ()
    description: str = ""

    def public_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "operation": self.operation,
            "route_kind": self.route_kind,
            "target_name": self.target_name,
        }
        if self.fields:
            payload["fields"] = list(self.fields)
        if self.argument_constants:
            payload["argument_constants"] = dict(self.argument_constants)
        if self.description:
            payload["description"] = self.description
        return payload


class WorkplaceOperationRouter:
    """Backend-owned map from business resources to canonical tools/actions."""

    def __init__(
        self,
        registry: WorkplaceResourceRegistry | None = None,
    ) -> None:
        self._registry = registry or WorkplaceResourceRegistry()
        self._routes = self._build_routes()
        self._validate()

    @staticmethod
    def _build_routes() -> tuple[WorkplaceOperationRoute, ...]:
        routes = [
            WorkplaceOperationRoute(
                "organization",
                "read",
                "tool",
                "get_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "organization",
                "search",
                "tool",
                "search_workplace_resources",
            ),
            WorkplaceOperationRoute(
                "organization",
                "update",
                "action",
                "update_workplace_resource",
                fields=("legal_name",),
            ),
            WorkplaceOperationRoute(
                "organization",
                "clear",
                "action",
                "clear_workplace_resource_fields",
                fields=("legal_name",),
            ),
            WorkplaceOperationRoute(
                "organization",
                "update",
                "action",
                "update_nucleus_organization_account_field",
                fields=("display_name",),
                argument_constants=(("field_name", "OrganizationName"),),
                description="Synchronizes the Nucleus and organization projections.",
            ),
            WorkplaceOperationRoute(
                "organization",
                "update",
                "action",
                "update_organization_contact_email",
                fields=("contact_email",),
                description="Uses the canonical contact-email bridge.",
            ),
            WorkplaceOperationRoute(
                "organization",
                "clear",
                "action",
                "clear_nucleus_organization_account_field",
                fields=("contact_email",),
                argument_constants=(("field_name", "Email"),),
                description="Clears the email through the synchronized Nucleus handler.",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "read",
                "tool",
                "get_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "search",
                "tool",
                "search_workplace_resources",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "create",
                "action",
                "create_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "update",
                "action",
                "update_workplace_resource",
                fields=("value", "description"),
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "clear",
                "action",
                "clear_workplace_resource_fields",
                fields=("value", "description"),
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "activate",
                "action",
                "activate_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "deactivate",
                "action",
                "deactivate_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "delete",
                "action",
                "delete_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "restore",
                "action",
                "restore_workplace_resource",
            ),
            WorkplaceOperationRoute(
                "workplace_setting",
                "bulk_update",
                "action",
                "bulk_update_workplace_resources",
                fields=("value", "description"),
            ),
            WorkplaceOperationRoute(
                "organization_overview",
                "read",
                "tool",
                "get_organization_overview",
            ),
            WorkplaceOperationRoute(
                "organization_membership",
                "read",
                "tool",
                "list_organization_users",
            ),
            WorkplaceOperationRoute(
                "organization_membership",
                "invite",
                "action",
                "invite_organization_user",
            ),
            WorkplaceOperationRoute(
                "organization_membership",
                "activate",
                "action",
                "activate_organization_membership",
            ),
            WorkplaceOperationRoute(
                "organization_membership",
                "update_role",
                "action",
                "update_organization_member_role",
            ),
            WorkplaceOperationRoute(
                "organization_membership",
                "remove",
                "action",
                "remove_organization_user",
            ),
            WorkplaceOperationRoute(
                "user",
                "read",
                "tool",
                "list_organization_users",
            ),
            WorkplaceOperationRoute(
                "organization_seat_pool",
                "read",
                "tool",
                "get_organization_seat_summary",
            ),
            WorkplaceOperationRoute(
                "seat_assignment",
                "read",
                "tool",
                "get_organization_seat_summary",
            ),
            WorkplaceOperationRoute(
                "seat_assignment",
                "assign",
                "action",
                "assign_organization_seat",
            ),
            WorkplaceOperationRoute(
                "seat_assignment",
                "revoke",
                "action",
                "revoke_organization_seat",
            ),
            WorkplaceOperationRoute(
                "report",
                "read",
                "tool",
                "list_organization_reports",
            ),
            WorkplaceOperationRoute(
                "organization_report_access",
                "read",
                "tool",
                "list_organization_reports",
            ),
            WorkplaceOperationRoute(
                "organization_report_access",
                "check",
                "tool",
                "check_organization_report_access",
            ),
            WorkplaceOperationRoute(
                "organization_report_access",
                "grant",
                "action",
                "grant_organization_report_access",
            ),
            WorkplaceOperationRoute(
                "organization_report_access",
                "revoke",
                "action",
                "revoke_organization_report_access",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "read",
                "tool",
                "get_nucleus_organization_account",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "read_license",
                "tool",
                "get_nucleus_organization_license",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "read_approval",
                "tool",
                "get_nucleus_organization_approval_status",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "update_profile",
                "action",
                "update_nucleus_organization_account_field",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "clear_profile",
                "action",
                "clear_nucleus_organization_account_field",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "update_username",
                "action",
                "update_nucleus_organization_username",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "update_license",
                "action",
                "update_nucleus_organization_license",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "approve",
                "action",
                "approve_nucleus_organization_account",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "reject",
                "action",
                "reject_nucleus_organization_account",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "activate",
                "action",
                "activate_nucleus_organization_account",
            ),
            WorkplaceOperationRoute(
                "nucleus_organization_account",
                "deactivate",
                "action",
                "deactivate_nucleus_organization_account",
            ),
        ]
        access_specs = (
            (
                "nucleus_category_access",
                "grant_nucleus_category_access",
                "revoke_nucleus_category_access",
            ),
            (
                "nucleus_company_profile_access",
                "grant_nucleus_company_profile_access",
                "revoke_nucleus_company_profile_access",
            ),
            (
                "nucleus_drug_access",
                "grant_nucleus_drug_access",
                "revoke_nucleus_drug_access",
            ),
            (
                "nucleus_indication_access",
                "grant_nucleus_indication_access",
                "revoke_nucleus_indication_access",
            ),
            (
                "nucleus_market_access",
                "grant_nucleus_market_access",
                "revoke_nucleus_market_access",
            ),
            (
                "nucleus_report_access",
                "grant_nucleus_report_access",
                "revoke_nucleus_report_access",
            ),
        )
        for resource_type, grant_action, revoke_action in access_specs:
            routes.extend(
                (
                    WorkplaceOperationRoute(
                        resource_type,
                        "read",
                        "tool",
                        "get_nucleus_organization_entitlements",
                    ),
                    WorkplaceOperationRoute(
                        resource_type,
                        "grant",
                        "action",
                        grant_action,
                    ),
                    WorkplaceOperationRoute(
                        resource_type,
                        "revoke",
                        "action",
                        revoke_action,
                    ),
                )
            )
        routes.extend(
            (
                WorkplaceOperationRoute(
                    "nucleus_permission",
                    "read",
                    "tool",
                    "get_nucleus_organization_entitlements",
                ),
                WorkplaceOperationRoute(
                    "nucleus_permission",
                    "update",
                    "action",
                    "update_nucleus_organization_permissions",
                ),
            )
        )
        return tuple(routes)

    def _validate(self) -> None:
        definitions = {
            item.resource_type: item for item in self._registry.list_definitions()
        }
        seen: set[tuple[str, str, str]] = set()
        for route in self._routes:
            definition = definitions.get(route.resource_type)
            if definition is None:
                raise RuntimeError(
                    f"Unknown workplace route resource: {route.resource_type}"
                )
            field_key = ",".join(route.fields) or "*"
            key = (route.resource_type, route.operation, field_key)
            if key in seen:
                raise RuntimeError("Duplicate workplace operation route")
            seen.add(key)
            for field_name in route.fields:
                if field_name not in definition.field_map:
                    raise RuntimeError(
                        f"Unknown routed field {route.resource_type}.{field_name}"
                    )
            if "password" in route.target_name.lower():
                raise RuntimeError("Credential operations cannot be routed")

        organization = definitions["organization"]
        for protected_name in ("display_name", "contact_email"):
            policy = organization.field_map[protected_name]
            if policy.editable or policy.clearable:
                raise RuntimeError(
                    f"{protected_name} must use its synchronized dedicated action"
                )


    def normalize_action_proposal(
        self,
        proposal: AgentActionProposalInput,
    ) -> AgentActionProposalInput:
        """Route synchronized organization fields to their dedicated actions."""

        arguments = proposal.arguments
        if proposal.action_name == "update_workplace_resource":
            if arguments.get("resource_type") != "organization":
                return proposal
            try:
                changes = json.loads(arguments["changes_json"])
            except (KeyError, json.JSONDecodeError) as exception:
                raise ValueError("Organization changes must be valid JSON") from exception
            if not isinstance(changes, dict) or not changes:
                raise ValueError("Organization changes must be a JSON object")
            synchronized = {"display_name", "contact_email"} & set(changes)
            if not synchronized:
                return proposal
            if len(changes) != 1:
                raise ValueError(
                    "Synchronized and generic organization fields require separate proposals"
                )
            field_name = next(iter(synchronized))
            value = changes[field_name]
            if not isinstance(value, str):
                raise ValueError("Synchronized organization values must be strings")
            if field_name == "display_name":
                return AgentActionProposalInput(
                    action_name="update_nucleus_organization_account_field",
                    arguments={
                        "field_name": "OrganizationName",
                        "value": value,
                    },
                )
            return AgentActionProposalInput(
                action_name="update_organization_contact_email",
                arguments={"contact_email": value},
            )

        if proposal.action_name == "clear_workplace_resource_fields":
            if arguments.get("resource_type") != "organization":
                return proposal
            try:
                fields = json.loads(arguments["fields_json"])
            except (KeyError, json.JSONDecodeError) as exception:
                raise ValueError("Organization clear fields must be valid JSON") from exception
            if not isinstance(fields, list) or not all(
                isinstance(item, str) for item in fields
            ):
                raise ValueError("Organization clear fields must be a JSON list")
            synchronized = {"display_name", "contact_email"} & set(fields)
            if not synchronized:
                return proposal
            if len(fields) != 1:
                raise ValueError(
                    "Synchronized and generic organization fields require separate proposals"
                )
            field_name = next(iter(synchronized))
            if field_name == "display_name":
                raise ValueError("Organization display name cannot be cleared")
            return AgentActionProposalInput(
                action_name="clear_nucleus_organization_account_field",
                arguments={"field_name": "Email"},
            )

        return proposal

    def list_routes(self) -> tuple[WorkplaceOperationRoute, ...]:
        return self._routes

    def public_catalog(self) -> tuple[dict[str, Any], ...]:
        routes_by_resource: dict[str, list[dict[str, Any]]] = {}
        for route in self._routes:
            routes_by_resource.setdefault(route.resource_type, []).append(
                route.public_dict()
            )
        catalog = []
        for definition in self._registry.list_definitions():
            item = definition.public_schema()
            routes = routes_by_resource.get(definition.resource_type, [])
            item["routes"] = routes
            item["available_operations"] = sorted(
                set(item["operations"])
                | {route["operation"] for route in routes}
            )
            catalog.append(item)
        return tuple(catalog)

    def describe(self, resource_type: str) -> dict[str, Any]:
        for item in self.public_catalog():
            if item["resource_type"] == resource_type:
                return item
        raise ValueError("Unknown workplace resource type")
