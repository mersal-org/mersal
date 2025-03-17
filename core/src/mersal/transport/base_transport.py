from mersal.messages import TransportMessage
from mersal.transport import TransactionContext
from mersal.transport.outgoing_message import OutgoingMessage

from .transport import Transport

__all__ = ("BaseTransport",)


class BaseTransport(Transport):
    def __init__(self, address: str) -> None:
        self.address = address

    def create_queue(self, address: str) -> None: ...

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        outgoing_messages: list[OutgoingMessage] | None = transaction_context.items.get("outgoing_messages")
        if not outgoing_messages:
            outgoing_messages = []

            async def action(context: TransactionContext) -> None:
                await self.send_outgoing_messages(outgoing_messages, context)

            transaction_context.items["outgoing_messages"] = outgoing_messages
            transaction_context.on_commit(action)

        outgoing_messages.append(OutgoingMessage(destination_address, message))

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None: ...

    async def send_outgoing_messages(
        self,
        outgoing_message: list[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None: ...
