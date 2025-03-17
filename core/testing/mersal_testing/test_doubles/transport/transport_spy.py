from mersal.messages import TransportMessage
from mersal.transport import TransactionContext, Transport
from mersal.transport.base_transport import BaseTransport

__all__ = ("TransportSpy",)


class TransportSpy(BaseTransport, Transport):
    def __init__(self, address: str | None) -> None:
        self.address = address if address else "transport-spy"
        self.sent_messages: list[TransportMessage] = []
        self.received_messages: list[TransportMessage] = []

    def create_queue(self, address: str) -> None:
        pass

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        self.sent_messages.append(message)

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        return None
