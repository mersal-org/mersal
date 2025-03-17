import anyio
import pytest

from mersal.threading import AnyIOPeriodicTaskFactory

__all__ = ("test_it_sleeps_and_runs_action",)


pytestmark = pytest.mark.anyio


async def test_it_sleeps_and_runs_action():
    class Spam:
        def __init__(self) -> None:
            self.total = 0

        async def task(self):
            self.total += 1

    factory = AnyIOPeriodicTaskFactory()
    instance = Spam()
    task = factory("Test", instance.task, 0.1)
    await task.start()
    await anyio.sleep(1.1)
    await task.stop()

    assert instance.total == 10
