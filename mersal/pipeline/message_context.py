from __future__ import annotations

from typing import TYPE_CHECKING, cast

from mersal.messages import LogicalMessage, MessageHeaders
from mersal.transport.ambient_context import AmbientContext

from .incoming_step_context import IncomingStepContext

if TYPE_CHECKING:
    from mersal.transport import TransactionContext

__all__ = ("MessageContext",)


class MessageContext:
    def __init__(self, transaction_context: TransactionContext) -> None:
        self.transaction_context = transaction_context

    @property
    def incoming_step_context(self) -> IncomingStepContext:
        step = cast(
            "IncomingStepContext | None", self.transaction_context.items.get(IncomingStepContext.step_context_key)
        )
        if not step:
            raise Exception("IncomingStepContext is not part of the TransactionContext")

        return step

    @property
    def message(self) -> LogicalMessage:
        return self.incoming_step_context.load(LogicalMessage)

    @property
    def headers(self) -> MessageHeaders:
        return self.message.headers

    @staticmethod
    def current() -> MessageContext | None:
        transaction_context = AmbientContext().current
        if not transaction_context:
            return None

        step = transaction_context.items.get(IncomingStepContext.step_context_key)
        if not step:
            raise Exception("IncomingStepContext is not part of the TransactionContext")

        return MessageContext(transaction_context)
