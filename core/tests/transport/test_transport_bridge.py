import pytest

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext, Transport, TransportBridge
from mersal.transport.default_transaction_context import DefaultTransactionContext

__all__ = (
    "TestTransportBridge",
    "TransportTestDouble",
)


pytestmark = pytest.mark.anyio


class TransportTestDouble(Transport):
    def __init__(self, address: str = "test-double"):
        self.address = address
        self.sent_messages = []

    def create_queue(self, address: str):
        pass

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ):
        self.sent_messages.append((destination_address, message))

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        return None


class TestTransportBridge:
    async def test_passing_messages_to_default_transport(self, transport_message: TransportMessage):
        transport1 = TransportTestDouble()
        subject = TransportBridge(default_transport=transport1, address_transport_mapping={})

        await subject.send("moon", transport_message, DefaultTransactionContext())

        assert len(transport1.sent_messages) == 1

    async def test_sending_via_other_transports_for_mapped_addresses(self, transport_message: TransportMessage):
        transport1 = TransportTestDouble()
        transport2 = TransportTestDouble()
        subject = TransportBridge(
            default_transport=transport1,
            address_transport_mapping={
                "sun": transport2,
            },
        )

        await subject.send("sun", transport_message, DefaultTransactionContext())

        assert len(transport1.sent_messages) == 0
        assert len(transport2.sent_messages) == 1
