from contextlib import AsyncExitStack
from dataclasses import dataclass
from logging import Logger

import anyio
from anyio import CancelScope, sleep

from mersal.threading.periodic_async_task import PeriodicAsyncTask
from mersal.types import AsyncAnyCallable

__all__ = ("AnyIOPeriodicTask",)


@dataclass
class AnyIOPeriodicTask(PeriodicAsyncTask):
    def __init__(
        self,
        description: str,
        task: AsyncAnyCallable,
        period: float,
        logger: Logger,
    ) -> None:
        self.description = description
        self.task = task
        self.period = period
        self.logger = logger
        self._cancel_scope: CancelScope | None = None
        self._exit_stack: AsyncExitStack | None = None

    async def start(self) -> None:
        self._exit_stack = AsyncExitStack()
        task_group = anyio.create_task_group()
        await self._exit_stack.enter_async_context(task_group)
        self._cancel_scope = task_group.cancel_scope
        task_group.start_soon(self._start)

    async def stop(self) -> None:
        if self._cancel_scope:
            self._cancel_scope.cancel()
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def _start(self) -> None:
        while True:
            await sleep(self.period)
            try:
                await self.task()
            except Exception:
                self.logger.exception("An exception has happened in a periodic task")
