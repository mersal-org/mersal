import pytest

from mersal.transport.in_memory import InMemoryNetwork
from mersal_testing.test_doubles import TransportMessageBuilder

__all__ = ("TestInMemoryNetwork",)


pytestmark = pytest.mark.anyio


class TestInMemoryNetwork:
    async def test_send_and_receive(self):
        subject = InMemoryNetwork()
        transport_message = TransportMessageBuilder.build()
        destination_address = "saturn"
        subject.deliver(destination_address, transport_message)

        next_message = subject.get_next(destination_address)
        assert next_message
        assert next_message.headers.message_id == transport_message.headers.message_id

    async def test_receive_empty_queue(self):
        subject = InMemoryNetwork()
        transport_message = TransportMessageBuilder.build()
        destination_address = "saturn"
        subject.deliver(destination_address, transport_message)

        subject.get_next(destination_address)
        assert not subject.get_next(destination_address)
        assert not subject.get_next("random-queue")
