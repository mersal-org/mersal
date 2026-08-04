from typing import Protocol

from mersal.types import AsyncAnyCallable

from .periodic_async_task import PeriodicAsyncTask

__all__ = ("PeriodicAsyncTaskFactory",)


class PeriodicAsyncTaskFactory(Protocol):
    def __call__(self, description: str, task: AsyncAnyCallable, period: float) -> PeriodicAsyncTask: ...
