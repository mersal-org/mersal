import anyio
import pytest
from anyio import create_task_group

from mersal.transport import (
    AmbientContext,
    DefaultTransactionContext,
)

__all__ = (
    "TestAmbientContext",
    "task1",
    "task2",
)


pytestmark = pytest.mark.anyio


async def task1():
    context = DefaultTransactionContext()
    AmbientContext().current = context
    await anyio.sleep(0.01)
    assert AmbientContext().current is context


async def task2():
    context = DefaultTransactionContext()
    AmbientContext().current = context
    await anyio.sleep(0.01)
    assert AmbientContext().current is context


class TestAmbientContext:
    async def test_set_current_context(self):
        async with create_task_group() as tg:
            tg.start_soon(task1)
            tg.start_soon(task2)
