from collections.abc import Iterable, Iterator, Sequence

from mersal.messages import LogicalMessage

from .handler_invoker import HandlerInvoker
from .saga_handler_invoker import SagaHandlerInvoker

__all__ = ("HandlerInvokers",)


class HandlerInvokers(Iterable):
    def __init__(
        self,
        message: LogicalMessage,
        handler_invokers: Sequence[HandlerInvoker | SagaHandlerInvoker],
    ) -> None:
        self.message = message
        self.handler_invokers = handler_invokers

    def __len__(self) -> int:
        return len(self.handler_invokers)

    def __iter__(self) -> Iterator[HandlerInvoker | SagaHandlerInvoker]:
        return iter(self.handler_invokers)
