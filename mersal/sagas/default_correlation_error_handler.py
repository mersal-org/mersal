from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from mersal.sagas.correlation_error_handler import CorrelationErrorHandler

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal.messages import LogicalMessage
    from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
    from mersal.sagas.correlation_property import CorrelationProperty

__all__ = ("DefaultCorrelationErrorHandler",)


class DefaultCorrelationErrorHandler(CorrelationErrorHandler):
    def __init__(self) -> None:
        self.logger = logging.getLogger("mersal.sagas.DefaultCorrelationErrorHandler")

    async def __call__(
        self,
        correlation_properties: Sequence[CorrelationProperty],
        saga_invoker: SagaHandlerInvoker,
        message: LogicalMessage,
    ) -> None:
        self.logger.debug("Could not correlate for message %r", message.headers.message_type)
        saga_invoker.should_invoke = False
