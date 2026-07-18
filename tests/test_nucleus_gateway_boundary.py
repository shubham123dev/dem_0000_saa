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
