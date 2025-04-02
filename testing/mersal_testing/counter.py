from collections.abc import Callable

from mersal.utils.sync import AsyncCallable

__all__ = (
    "Counter",
    "CounterWithAction",
    "FailingCounter",
)


class Counter:
    def __init__(self) -> None:
        self.total = 0

    async def task(self) -> None:
        self.total += 1


class FailingCounter:
    def __init__(self, fail_at_call: list[int]) -> None:
        self.calls = 0
        self.total = 0
        self.fail_at_call = fail_at_call

    async def task(self) -> None:
        self.calls += 1
        if self.calls in self.fail_at_call:
            raise Exception()

        self.total += 1


class CounterWithAction:
    def __init__(self, action: Callable) -> None:
        self.total = 0
        self.action = action

    async def task(self) -> None:
        self.total += 1
        await AsyncCallable(self.action)()
