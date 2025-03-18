import pytest
from anyio import sleep
from mersal_docs.unit_of_work.unit_of_work_sqlalchemy_example import (
    AddUser,
    User,
    app_factory,
    engine,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

__all__ = ("test_unit_of_work_using_sqlalchemy",)


pytestmark = pytest.mark.anyio


async def test_unit_of_work_using_sqlalchemy():
    app1 = await app_factory()
    await app1.start()
    message = AddUser(username="ABC")
    await app1.send_local(message)
    await sleep(1)
    await app1.stop()
    session_factory = async_sessionmaker(engine)

    async with session_factory() as session:
        stmt = select(User).where(User.username == message.username)
        _ = (await session.scalars(stmt)).one()
