from __future__ import annotations

from typing import TYPE_CHECKING, cast

from .anyio_worker import AnyioWorker

if TYPE_CHECKING:
    from mersal.core.app import Mersal
    from mersal.logging import Logger
    from mersal.pipeline import PipelineInvoker
    from mersal.transport import Transport
    from mersal.workers.backoff import WorkerBackoffStrategy

__all__ = ("AnyioWorkerFactory",)


class AnyioWorkerFactory:
    def __init__(
        self,
        transport: Transport,
        pipeline_invoker: PipelineInvoker,
        logger: Logger,
        max_parallelism: int = 1,
        backoff_strategy: WorkerBackoffStrategy | None = None,
        stop_grace_period: float | None = None,
    ) -> None:
        self.transport = transport
        self.pipeline_invoker = pipeline_invoker
        self.logger = logger
        self.max_parallelism = max_parallelism
        self.backoff_strategy = backoff_strategy
        self.stop_grace_period = stop_grace_period
        # Populated by Mersal.__init__ right after this factory is constructed.
        self.app: Mersal = cast("Mersal", None)

    def create_worker(
        self,
        name: str,
    ) -> AnyioWorker:
        return AnyioWorker(
            name=name,
            transport=self.transport,
            app=self.app,
            pipeline_invoker=self.pipeline_invoker,
            max_parallelism=self.max_parallelism,
            logger=self.logger,
            backoff_strategy=self.backoff_strategy,
            stop_grace_period=self.stop_grace_period,
        )
