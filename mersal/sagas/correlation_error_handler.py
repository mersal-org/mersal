from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal.messages.logical_message import LogicalMessage
    from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
    from mersal.sagas.correlation_property import CorrelationProperty

__all__ = ("CorrelationErrorHandler",)


class CorrelationErrorHandler(Protocol):
    async def __call__(
        self,
        correlation_properties: Sequence[CorrelationProperty],
        saga_invoker: SagaHandlerInvoker,
        message: LogicalMessage,
    ) -> None: ...
