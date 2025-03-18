import pytest
from anyio import sleep
from mersal_docs.outbox.outbox_sqlalchemy_example import (
    PROMOTED_USERS,
    AddUser,
    app_factory,
)

__all__ = ("test_outbox_using_sqlalchemy",)


pytestmark = pytest.mark.anyio


async def test_outbox_using_sqlalchemy():
    app1 = await app_factory()
    await app1.start()
    message = AddUser(username="J")
    await app1.send_local(message)
    await sleep(2)
    await app1.stop()
    assert PROMOTED_USERS.users == ["J"]
