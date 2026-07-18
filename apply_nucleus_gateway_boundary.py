#!/usr/bin/env python3
"""Apply the Nucleus gateway-boundary vertical slice.

Baseline repository:
    shubham123dev/dem_0000_saa
Baseline commit:
    cf131fdb5f642e9f63aed84315a1df7665c76cce

The patch is intentionally fail-closed. It validates the baseline, refuses tracked
local modifications, asserts every expected source replacement, and never stages,
commits, pushes, or touches unrelated untracked files.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

BASELINE_COMMIT = "cf131fdb5f642e9f63aed84315a1df7665c76cce"


def clean_block(value: str) -> str:
    return dedent(value).strip("\n") + "\n"


class PatchError(RuntimeError):
    """Raised when the repository does not match the expected source state."""


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


def validate_repository(root: Path, allow_nonbaseline: bool) -> None:
    if not (root / ".git").is_dir():
        raise PatchError("Run this script from the repository root containing .git")

    head = run_git(root, "rev-parse", "HEAD")
    if not allow_nonbaseline and head != BASELINE_COMMIT:
        raise PatchError(
            "Unexpected HEAD. Expected "
            f"{BASELINE_COMMIT}, found {head}. "
            "Use --allow-nonbaseline only after manually verifying compatibility."
        )

    if run_git(root, "diff", "--name-only"):
        raise PatchError("Tracked working-tree changes exist; commit or revert them first")
    if run_git(root, "diff", "--cached", "--name-only"):
        raise PatchError("Staged changes exist; commit or unstage them first")


def add_new_files(root: Path) -> None:
    create_exact(
        root,
        "app/adapters/nucleus/__init__.py",
        clean_block(
            '''
            """Stable Nucleus organization adapter boundary."""

            from app.adapters.nucleus.contract import NucleusOrganizationGateway

            __all__ = ["NucleusOrganizationGateway"]
            '''
        ),
    )

    create_exact(
        root,
        "app/adapters/nucleus/contract.py",
        clean_block(
            '''
            """Port consumed by Nucleus organization services and action handlers.

            Implementations may use the exact-schema SQLite sandbox, a future Nucleus
            HTTP API, or another production-safe persistence adapter. Callers depend
            only on this framework-neutral contract.
            """

            from __future__ import annotations

            from typing import Any, Protocol, runtime_checkable

            from app.domain.nucleus_models import (
                NucleusCategoryAccess,
                NucleusOrganizationAccount,
                NucleusOrganizationApprovalStatus,
                NucleusOrganizationEntitlements,
                NucleusOrganizationLicense,
                NucleusReportAccess,
                NucleusSpecialPermissions,
            )


            @runtime_checkable
            class NucleusOrganizationGateway(Protocol):
                async def get_account(
                    self,
                    organization_code: str,
                ) -> NucleusOrganizationAccount | None:
                    ...

                async def get_license(
                    self,
                    organization_code: str,
                ) -> NucleusOrganizationLicense | None:
                    ...

                async def get_approval_status(
                    self,
                    organization_code: str,
                ) -> NucleusOrganizationApprovalStatus | None:
                    ...

                async def get_entitlements(
                    self,
                    organization_code: str,
                ) -> NucleusOrganizationEntitlements | None:
                    ...

                async def get_account_field_state(
                    self,
                    organization_code: str,
                    field_name: str,
                ) -> tuple[NucleusOrganizationAccount, Any] | None:
                    ...

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

                async def update_account_field_if_version(
                    self,
                    *,
                    organization_code: str,
                    field_name: str,
                    value: str | None,
                    expected_version: int,
                ) -> NucleusOrganizationAccount | None:
                    ...

                async def inspect_category_grant(
                    self,
                    *,
                    organization_code: str,
                    category_id: int,
                    category_sample_id: int | None,
                ) -> tuple[NucleusCategoryAccess | None, int] | None:
                    ...

                async def get_category_access(
                    self,
                    *,
                    organization_code: str,
                    access_id: int,
                ) -> NucleusCategoryAccess | None:
                    ...

                async def grant_category_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    category_id: int,
                    category_sample_id: int | None,
                    expected_version: int,
                ) -> NucleusCategoryAccess | None:
                    ...

                async def revoke_category_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_id: int,
                    expected_version: int,
                ) -> NucleusCategoryAccess | None:
                    ...

                async def inspect_report_grant(
                    self,
                    *,
                    organization_code: str,
                    reports_id: int | None,
                    sample_id: int | None,
                    sample_toc_id: int | None,
                    speciality_id: int | None,
                    is_executive_access: bool | None,
                ) -> tuple[NucleusReportAccess | None, int] | None:
                    ...

                async def get_report_access(
                    self,
                    *,
                    organization_code: str,
                    access_id: int,
                ) -> NucleusReportAccess | None:
                    ...

                async def grant_report_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    reports_id: int | None,
                    sample_id: int | None,
                    sample_toc_id: int | None,
                    speciality_id: int | None,
                    is_executive_access: bool | None,
                    expected_version: int,
                ) -> NucleusReportAccess | None:
                    ...

                async def revoke_report_access_if_version(
                    self,
                    *,
                    organization_code: str,
                    access_id: int,
                    expected_version: int,
                ) -> NucleusReportAccess | None:
                    ...

                async def get_permission(
                    self,
                    *,
                    organization_code: str,
                    permission_id: int,
                ) -> NucleusSpecialPermissions | None:
                    ...

                async def set_permission_if_version(
                    self,
                    *,
                    organization_code: str,
                    permission_id: int | None,
                    values: dict[str, int | bool | None],
                    expected_version: int,
                ) -> NucleusSpecialPermissions | None:
                    ...
            '''
        ),
    )

    create_exact(
        root,
        "app/domain/nucleus_policy.py",
        clean_block(
            '''
            """Backend-owned policy for editable Nucleus organization account fields."""

            from __future__ import annotations

            NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS: dict[str, int] = {
                "OrganizationName": 250,
                "OrganizationType": 100,
                "Industry": 150,
                "Website": 250,
                "Email": 150,
                "ContactPersonName": 150,
                "ContactPersonDesignation": 150,
                "ContactPhone": 50,
                "AddressLine1": 250,
                "AddressLine2": 250,
                "City": 100,
                "State": 100,
                "Country": 100,
                "PostalCode": 30,
            }

            EDITABLE_NUCLEUS_ACCOUNT_FIELDS = frozenset(
                NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS
            )
            CLEARABLE_NUCLEUS_ACCOUNT_FIELDS = (
                EDITABLE_NUCLEUS_ACCOUNT_FIELDS - {"OrganizationName"}
            )
            '''
        ),
    )

    create_exact(
        root,
        "tests/test_nucleus_gateway_boundary.py",
        clean_block(
            '''
            """Contract tests for the Nucleus persistence adapter boundary."""

            from __future__ import annotations

            from typing import get_type_hints

            import pytest
            from sqlalchemy.ext.asyncio import AsyncSession

            from app.adapters.nucleus.contract import NucleusOrganizationGateway
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
            from app.repositories.nucleus_organization_repository import (
                NucleusOrganizationRepository,
            )
            from app.services.nucleus_organization_service import (
                NucleusOrganizationService,
            )


            HANDLER_TYPES = (
                UpdateOrganizationContactEmailBridgeHandler,
                UpdateNucleusOrganizationAccountFieldHandler,
                ClearNucleusOrganizationAccountFieldHandler,
                GrantNucleusCategoryAccessHandler,
                RevokeNucleusCategoryAccessHandler,
                GrantNucleusReportAccessHandler,
                RevokeNucleusReportAccessHandler,
                UpdateNucleusOrganizationPermissionsHandler,
            )


            async def test_sqlite_repository_satisfies_nucleus_gateway(
                db_session: AsyncSession,
            ) -> None:
                repository = NucleusOrganizationRepository(db_session)
                assert isinstance(repository, NucleusOrganizationGateway)


            def test_nucleus_read_service_depends_on_gateway_port() -> None:
                hints = get_type_hints(NucleusOrganizationService.__init__)
                assert hints["nucleus_gateway"] is NucleusOrganizationGateway


            @pytest.mark.parametrize("handler_type", HANDLER_TYPES)
            def test_nucleus_action_handler_depends_on_gateway_port(handler_type: type) -> None:
                hints = get_type_hints(handler_type.__init__)
                assert hints["gateway"] is NucleusOrganizationGateway
            '''
        ),
    )


def patch_service(root: Path) -> None:
    path = "app/services/nucleus_organization_service.py"
    replace_exact(
        root,
        path,
        "from app.adapters.organization.contract import OrganizationApiGateway\n",
        "from app.adapters.nucleus.contract import NucleusOrganizationGateway\n"
        "from app.adapters.organization.contract import OrganizationApiGateway\n",
    )
    replace_exact(
        root,
        path,
        "from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository\n",
        "",
    )
    replace_exact(
        root,
        path,
        "        repository: NucleusOrganizationRepository,\n",
        "        nucleus_gateway: NucleusOrganizationGateway,\n",
    )
    replace_exact(
        root,
        path,
        "        self._repository = repository\n",
        "        self._nucleus_gateway = nucleus_gateway\n",
    )
    replace_exact(
        root,
        path,
        "self._repository",
        "self._nucleus_gateway",
        expected_count=4,
    )


def patch_handlers(root: Path) -> None:
    path = "app/agent/nucleus_action_handlers.py"
    replace_exact(
        root,
        path,
        clean_block(
            '''
            from app.repositories.nucleus_organization_repository import (
                ACCOUNT_FIELD_ATTRIBUTES,
                NucleusOrganizationRepository,
            )
            '''
        ),
        clean_block(
            '''
            from app.adapters.nucleus.contract import NucleusOrganizationGateway
            from app.domain.nucleus_policy import (
                CLEARABLE_NUCLEUS_ACCOUNT_FIELDS,
                EDITABLE_NUCLEUS_ACCOUNT_FIELDS,
                NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS,
            )
            '''
        ),
    )

    replace_section(
        root,
        path,
        "_FIELD_MAX_LENGTHS = {",
        '_CLEARABLE_FIELDS = set(ACCOUNT_FIELD_ATTRIBUTES) - {"OrganizationName"}',
        "_FIELD_MAX_LENGTHS = NUCLEUS_ACCOUNT_FIELD_MAX_LENGTHS\n"
        "_CLEARABLE_FIELDS = CLEARABLE_NUCLEUS_ACCOUNT_FIELDS",
    )
    replace_exact(
        root,
        path,
        "for allowed in ACCOUNT_FIELD_ATTRIBUTES:",
        "for allowed in EDITABLE_NUCLEUS_ACCOUNT_FIELDS:",
    )
    replace_exact(
        root,
        path,
        "repository: NucleusOrganizationRepository",
        "gateway: NucleusOrganizationGateway",
        expected_count=8,
    )
    replace_exact(
        root,
        path,
        "self._repository = repository",
        "self._gateway = gateway",
        expected_count=8,
    )
    text = read_text(root, path)
    repository_call_count = text.count("self._repository")
    if repository_call_count < 16:
        raise PatchError(
            f"{path}: expected at least 16 repository calls, found {repository_call_count}"
        )
    write_text(root, path, text.replace("self._repository", "self._gateway"))


def patch_repository(root: Path) -> None:
    path = "app/repositories/nucleus_organization_repository.py"
    replace_exact(
        root,
        path,
        ")\n\n\nACCOUNT_FIELD_ATTRIBUTES: dict[str, str] = {",
        ")\nfrom app.domain.nucleus_policy import EDITABLE_NUCLEUS_ACCOUNT_FIELDS\n\n\n"
        "ACCOUNT_FIELD_ATTRIBUTES: dict[str, str] = {",
    )
    replace_exact(
        root,
        path,
        '}\n\n\ndef _utcnow() -> datetime:\n',
        '}\n\n'
        'if frozenset(ACCOUNT_FIELD_ATTRIBUTES) != EDITABLE_NUCLEUS_ACCOUNT_FIELDS:\n'
        '    raise RuntimeError("Nucleus editable-field policy and SQLite mapping diverged")\n\n\n'
        'def _utcnow() -> datetime:\n',
    )


def patch_dependencies(root: Path) -> None:
    path = "app/api/dependencies.py"
    replace_exact(
        root,
        path,
        "from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter\n",
        "from app.adapters.nucleus.contract import NucleusOrganizationGateway\n"
        "from app.adapters.organization.mock_adapter import MockOrganizationApiAdapter\n",
    )
    replace_exact(
        root,
        path,
        clean_block(
            '''
            def get_nucleus_organization_repository(
                session: SessionDep,
            ) -> NucleusOrganizationRepository:
                return NucleusOrganizationRepository(session)


            def get_mock_organization_api(session: SessionDep) -> MockOrganizationApi:
            '''
        ),
        clean_block(
            '''
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
            '''
        ),
    )
    replace_exact(
        root,
        path,
        clean_block(
            '''
                repository: Annotated[
                    NucleusOrganizationRepository,
                    Depends(get_nucleus_organization_repository),
                ],
            ) -> NucleusOrganizationService:
                return NucleusOrganizationService(
                    organization_gateway=MockOrganizationApiAdapter(api),
                    permission_service=PermissionService(user_repo),
                    repository=repository,
                    audit_repository=audit_repo,
                )
            '''
        ),
        clean_block(
            '''
                nucleus_gateway: NucleusOrganizationGatewayDep,
            ) -> NucleusOrganizationService:
                return NucleusOrganizationService(
                    organization_gateway=MockOrganizationApiAdapter(api),
                    permission_service=PermissionService(user_repo),
                    nucleus_gateway=nucleus_gateway,
                    audit_repository=audit_repo,
                )
            '''
        ),
    )


def patch_action_dependencies(root: Path) -> None:
    path = "app/api/action_dependencies.py"
    replace_exact(
        root,
        path,
        "    MockOrganizationApiDep,\n    SessionDep,\n",
        "    MockOrganizationApiDep,\n    NucleusOrganizationGatewayDep,\n    SessionDep,\n",
    )
    replace_exact(
        root,
        path,
        "from app.repositories.nucleus_organization_repository import NucleusOrganizationRepository\n",
        "",
    )
    replace_exact(
        root,
        path,
        clean_block(
            '''
            def get_agent_action_handlers(
                api: MockOrganizationApiDep,
                session: SessionDep,
            ) -> dict[str, AgentActionHandler]:
                resources = OperationalResourceService(session)
                nucleus = NucleusOrganizationRepository(session)
            '''
        ),
        clean_block(
            '''
            def get_agent_action_handlers(
                api: MockOrganizationApiDep,
                session: SessionDep,
                nucleus: NucleusOrganizationGatewayDep,
            ) -> dict[str, AgentActionHandler]:
                resources = OperationalResourceService(session)
            '''
        ),
    )


def patch_documentation(root: Path) -> None:
    replace_exact(
        root,
        "docs/ARCHITECTURE.md",
        "→ NucleusOrganizationRepository\n→ exact PascalCase SQLite tables\n",
        "→ NucleusOrganizationGateway port\n"
        "→ NucleusOrganizationRepository SQLite adapter\n"
        "→ exact PascalCase SQLite tables\n",
    )
    replace_exact(
        root,
        "docs/ARCHITECTURE.md",
        "Current: NucleusOrganizationRepository → SQLite exact-schema mock\n"
        "Future:  NucleusOrganizationApiAdapter → real Nucleus API/database mapping\n",
        "Current: NucleusOrganizationGateway → NucleusOrganizationRepository → SQLite exact-schema mock\n"
        "Future:  NucleusOrganizationGateway → NucleusOrganizationApiAdapter → real Nucleus API/database mapping\n",
    )

    replace_exact(
        root,
        "README.md",
        "Natural-language requests may select allowlisted read tools or create dry-run\n"
        "action proposals. They cannot approve, execute, choose organization scope, or\n"
        "supply authorization state.\n\n"
        "## Exact SQLite tables\n",
        "Natural-language requests may select allowlisted read tools or create dry-run\n"
        "action proposals. They cannot approve, execute, choose organization scope, or\n"
        "supply authorization state.\n\n"
        "## Nucleus adapter boundary\n\n"
        "Nucleus reads and mutations consume the framework-neutral\n"
        "`NucleusOrganizationGateway` protocol. The current SQLite repository satisfies\n"
        "that port structurally. A future real Nucleus adapter can replace the dependency\n"
        "without changing routes, services, action handlers, approval policy, or model\n"
        "tool contracts. No production endpoint or credential behavior is invented here.\n\n"
        "## Exact SQLite tables\n",
    )


MODIFIED_PATHS = (
    "README.md",
    "app/agent/nucleus_action_handlers.py",
    "app/api/action_dependencies.py",
    "app/api/dependencies.py",
    "app/repositories/nucleus_organization_repository.py",
    "app/services/nucleus_organization_service.py",
    "docs/ARCHITECTURE.md",
)

NEW_PATHS = (
    "app/adapters/nucleus/__init__.py",
    "app/adapters/nucleus/contract.py",
    "app/domain/nucleus_policy.py",
    "tests/test_nucleus_gateway_boundary.py",
)


def _restore_after_failure(
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
    for relative_path in sorted(NEW_PATHS, key=lambda value: value.count("/"), reverse=True):
        parent = (root / relative_path).parent
        while parent != root and parent.exists():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def apply_patch(root: Path, allow_nonbaseline: bool) -> None:
    validate_repository(root, allow_nonbaseline)
    backups = {path: read_text(root, path) for path in MODIFIED_PATHS}
    new_path_existed = {path: (root / path).exists() for path in NEW_PATHS}

    try:
        add_new_files(root)
        patch_service(root)
        patch_handlers(root)
        patch_repository(root)
        patch_dependencies(root)
        patch_action_dependencies(root)
        patch_documentation(root)
    except Exception:
        _restore_after_failure(root, backups, new_path_existed)
        raise

    print("Applied Nucleus gateway-boundary vertical slice.")
    print("No files were staged, committed, or pushed.")
    print("Untracked ZIP/download files were not touched.")
    print()
    print("Validate with:")
    print("  python -m compileall -q app tests alembic")
    print("  git diff --check")
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
    parser.add_argument(
        "--allow-nonbaseline",
        action="store_true",
        help="Apply after manual compatibility review when HEAD is not the baseline",
    )
    args = parser.parse_args()

    try:
        apply_patch(args.repo.resolve(), args.allow_nonbaseline)
    except PatchError as exception:
        print(f"PATCH FAILED: {exception}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
