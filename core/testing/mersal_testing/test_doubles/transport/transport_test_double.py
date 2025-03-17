from mersal.messages import TransportMessage
from mersal.transport import OutgoingMessage, TransactionContext
from mersal.transport.base_transport import BaseTransport

__all__ = ("TransportTestDouble",)


class TransportTestDouble(BaseTransport):
    def __init__(self) -> None:
        self.address = "transport-test-double"
        self.sent_messages: list[tuple[list[OutgoingMessage], TransactionContext]] = []
        self.received_messages: list[TransportMessage] = []

    def create_queue(self, address: str) -> None:
        pass

    async def send_outgoing_messages(
        self,
        outgoing_message: list[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        self.sent_messages.append((outgoing_message, transaction_context))

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        return None
