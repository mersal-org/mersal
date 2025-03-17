import logging

from mersal.threading.periodic_async_task import PeriodicAsyncTask
from mersal.threading.periodic_async_task_factory import PeriodicAsyncTaskFactory
from mersal.types import AsyncAnyCallable

from .anyio_periodic_async_task import AnyIOPeriodicTask

__all__ = ("AnyIOPeriodicTaskFactory",)


class AnyIOPeriodicTaskFactory(PeriodicAsyncTaskFactory):
    def __init__(self) -> None:
        self.logger = logging.getLogger("mersal.anyIOPeriodicTaskFactory")

    def __call__(self, description: str, task: AsyncAnyCallable, period: float) -> PeriodicAsyncTask:
        return AnyIOPeriodicTask(
            description=description,
            task=task,
            period=period,
            logger=self.logger,
        )
