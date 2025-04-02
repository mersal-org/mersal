import pytest

from mersal.pipeline import (
    DestinationAddresses,
    OutgoingStepContext,
    SendOutgoingMessageStep,
)
from mersal.transport import (
    DefaultTransactionContext,
)
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

__all__ = ("TestSendOutgoingMessageStep",)


pytestmark = pytest.mark.anyio


class TestSendOutgoingMessageStep:
    async def test_sends_messages_to_all_addresses(self):
        network = InMemoryNetwork()
        transport = InMemoryTransport(InMemoryTransportConfig(network, "moon"))
        subject = SendOutgoingMessageStep(transport)
        message = LogicalMessageBuilder.build()
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        context.save(destination_addresses)
        context.save(transport_message)

        counter = Counter()
        await subject(context, counter.task)

        transaction_context.set_result(True, True)
        await transaction_context.complete()

        message_to_moon = network.get_next("moon")
        message_to_sun = network.get_next("sun")
        assert message_to_moon
        assert message_to_moon
        assert all(
            x.headers.message_id == transport_message.headers.message_id for x in [message_to_moon, message_to_sun]
        )
        assert counter.total == 1
