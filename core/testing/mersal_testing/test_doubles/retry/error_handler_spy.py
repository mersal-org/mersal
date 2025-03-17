from collections import defaultdict
from typing import Any

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext

__all__ = ("ErrorHandlerSpy",)


class ErrorHandlerSpy:
    def __init__(self) -> None:
        self.poisonous_messages: dict[Any, list[Exception]] = defaultdict(list)

    async def handle_poison_message(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
        exception: Exception,
    ) -> None:
        self.poisonous_messages[message.headers.message_id].append(exception)
