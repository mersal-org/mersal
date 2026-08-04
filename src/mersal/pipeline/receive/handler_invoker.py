from typing import Any

from mersal.transport import TransactionContext
from mersal.types import AsyncAnyCallable

__all__ = ("HandlerInvoker",)


class HandlerInvoker:
    current_handler_invoker_items_key = "current-handler-invoker"

    def __init__(
        self,
        action: AsyncAnyCallable,
        handler: Any,
        transaction_context: TransactionContext,
    ) -> None:
        self._action = action
        self.handler = handler
        self._transaction_context = transaction_context
        self.should_invoke = True

    async def __call__(self) -> None:
        if not self.should_invoke:
            return

        try:
            self._transaction_context.items[self.current_handler_invoker_items_key] = self

            await self._action()
        finally:
            del self._transaction_context.items[self.current_handler_invoker_items_key]
