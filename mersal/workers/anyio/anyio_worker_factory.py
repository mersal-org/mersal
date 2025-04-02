from __future__ import annotations

from typing import TYPE_CHECKING

from .anyio_worker import AnyioWorker

if TYPE_CHECKING:
    from mersal.app import Mersal
    from mersal.pipeline import PipelineInvoker
    from mersal.transport import Transport

__all__ = ("AnyioWorkerFactory",)


class AnyioWorkerFactory:
    def __init__(
        self,
        transport: Transport,
        pipeline_invoker: PipelineInvoker,
    ) -> None:
        self.transport = transport
        self.pipeline_invoker = pipeline_invoker
        self.app: Mersal = None  # type: ignore[assignment]

    def create_worker(
        self,
        name: str,
    ) -> AnyioWorker:
        return AnyioWorker(
            name=name,
            transport=self.transport,
            app=self.app,
            pipeline_invoker=self.pipeline_invoker,
        )
