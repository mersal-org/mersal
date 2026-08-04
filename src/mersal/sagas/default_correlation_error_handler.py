from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.sagas.correlation_error_handler import CorrelationErrorHandler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal.logging import Logger
    from mersal.messages import LogicalMessage
    from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
    from mersal.sagas.correlation_property import CorrelationProperty

__all__ = ("DefaultCorrelationErrorHandler",)


class DefaultCorrelationErrorHandler(CorrelationErrorHandler):
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    async def __call__(
        self,
        correlation_properties: Sequence[CorrelationProperty],
        saga_invoker: SagaHandlerInvoker,
        message: LogicalMessage,
    ) -> None:
        self.logger.debug("saga.correlation.failed", message_type=message.headers.message_type)
        saga_invoker.should_invoke = False
