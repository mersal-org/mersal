from typing import Protocol

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext

__all__ = ("Transport",)


class Transport(Protocol):
    address: str

    async def create_queue(self, address: str) -> None: ...
    async def __call__(self) -> None: ...

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None: ...

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        """Return the next incoming message, or None if none is available.

        Implementations may wait internally for a message but must return
        (a message or None) within a bounded time rather than blocking
        indefinitely: the worker treats each return as a liveness signal,
        and idle waiting is the job of the worker's backoff strategy, not
        the transport.
        """
        ...
