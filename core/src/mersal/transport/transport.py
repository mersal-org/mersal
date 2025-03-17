from typing import Protocol

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext

__all__ = ("Transport",)


class Transport(Protocol):
    address: str

    def create_queue(self, address: str) -> None: ...

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None: ...

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None: ...
