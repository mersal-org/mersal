from typing import Protocol

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext

__all__ = ("ErrorHandler",)


class ErrorHandler(Protocol):
    async def handle_poison_message(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
        exception: Exception,
    ) -> None: ...
