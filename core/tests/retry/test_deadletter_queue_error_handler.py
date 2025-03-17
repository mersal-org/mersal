import pytest

from mersal.retry import DeadletterQueueErrorHandler
from mersal.transport import (
    TransactionScope,
)
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal_testing.test_doubles import TransportMessageBuilder

__all__ = ("TestDeadletterQueueErrorHandler",)


pytestmark = pytest.mark.anyio


class TestDeadletterQueueErrorHandler:
    async def test_it_sends_the_poison_message_to_the_deadletter_queue(self):
        network = InMemoryNetwork()
        transport = InMemoryTransport(InMemoryTransportConfig(network, "moon"))
        error_queue_name = "e"
        subject = DeadletterQueueErrorHandler(transport=transport, error_queue_name=error_queue_name)

        transport_message = TransportMessageBuilder.build()
        exception = Exception()
        assert not network.get_next(error_queue_name)
        async with TransactionScope() as scope:
            await subject.handle_poison_message(transport_message, scope.transaction_context, exception)
            await scope.complete()

        received_message = network.get_next(error_queue_name)
        assert received_message
        assert received_message == transport_message
        assert received_message.headers.get("error_details") == str(exception)
