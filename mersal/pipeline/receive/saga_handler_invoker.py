from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mersal.pipeline.receive.handler_invoker import HandlerInvoker
    from mersal.sagas import SagaBase

__all__ = ("SagaHandlerInvoker",)


class SagaHandlerInvoker:
    def __init__(self, saga: SagaBase, invoker: HandlerInvoker) -> None:
        self.saga = saga
        self._invoker = invoker

    async def __call__(self) -> None:
        await self._invoker()

    @property
    def should_invoke(self) -> bool:
        return self._invoker.should_invoke

    @should_invoke.setter
    def should_invoke(self, value: bool) -> None:
        self._invoker.should_invoke = value
