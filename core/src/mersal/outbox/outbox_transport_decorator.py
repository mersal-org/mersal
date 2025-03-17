from typing import TYPE_CHECKING, Any

from mersal.messages import TransportMessage
from mersal.transport.outgoing_message import OutgoingMessage
from mersal.transport.transaction_context import TransactionContext
from mersal.transport.transport import Transport
from mersal.types.callable_types import AsyncTransactionContextCallable

from .outbox_incoming_step import OutboxIncomingStep
from .outbox_storage import OutboxStorage

if TYPE_CHECKING:
    from collections.abc import MutableSequence

__all__ = ("OutboxTransportDecorator",)


class OutboxTransportDecorator:
    def __init__(self, transport: Transport, outbox_storage: OutboxStorage) -> None:
        self.transport = transport
        self.address = transport.address
        self.outbox_storage = outbox_storage
        self._outgoing_messages_key = "outgoing-messages"

    def create_queue(self, address: str) -> None:
        self.transport.create_queue(address)

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        use_outbox: Any | None = transaction_context.items.get(OutboxIncomingStep.use_outbox_key)
        if not use_outbox:
            await self.transport.send(destination_address, message, transaction_context)
            return

        outgoing_messages: MutableSequence[OutgoingMessage] | None = transaction_context.items.get(
            self._outgoing_messages_key
        )
        if outgoing_messages is None:
            outgoing_messages = []

            async def commit_action(_: AsyncTransactionContextCallable) -> None:
                await self.outbox_storage.save(outgoing_messages, transaction_context)

            transaction_context.items[self._outgoing_messages_key] = outgoing_messages
            transaction_context.on_commit(commit_action)

        outgoing_messages.append(OutgoingMessage(destination_address=destination_address, transport_message=message))

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        return await self.transport.receive(transaction_context)
