from __future__ import annotations

from app.adapters.user.contract import CreateUserCommand
from app.adapters.user.sandbox_adapter import SandboxUserDirectory
from app.domain.enums import UserStatus
from app.domain.models import User


async def test_sandbox_directory_replaces_local_user_persistence() -> None:
    directory = SandboxUserDirectory()
    directory.reset(
        (
            User(
                id="1001",
                display_name="Existing User",
                email="existing@example.test",
                status=UserStatus.ACTIVE,
            ),
        )
    )

    assert (await directory.get_by_id("1001")).email == "existing@example.test"
    assert (await directory.get_by_email("EXISTING@example.test")).id == "1001"
    assert set(await directory.get_many_by_ids(("1001", "missing"))) == {"1001"}


async def test_sandbox_creation_is_idempotent_by_normalized_email() -> None:
    directory = SandboxUserDirectory()
    command = CreateUserCommand(
        display_name="Created User",
        email="Created@Example.Test",
        actor_user_id="1001",
    )
    first = await directory.create_user(command)
    second = await directory.create_user(command)

    assert first.id == second.id
    assert first.email == "created@example.test"
    assert first.status == UserStatus.ACTIVE
