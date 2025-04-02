import pytest

from mersal.messages.transport_message import TransportMessage
from mersal.pipeline import SerializeOutgoingMessageStep
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.transport import DefaultTransactionContext
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    SerializerTestDouble,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = ("TestSerializeOutgoingMessageStep",)


class TestSerializeOutgoingMessageStep:
    async def test_serialization_and_calling_next_step(self):
        serializer = SerializerTestDouble()
        transport_message = TransportMessageBuilder.build()
        serializer.serialize_stub = transport_message
        subject = SerializeOutgoingMessageStep(serializer)

        message = LogicalMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        destination_addresses = DestinationAddresses({"moon", "sun"})
        context = OutgoingStepContext(
            message=message,
            transaction_context=transaction_context,
            destination_addresses=destination_addresses,
        )
        context.save_keys("do-not-serialize", True)
        counter = Counter()
        await subject(context, counter.task)

        assert transport_message is context.load(TransportMessage)
        assert counter.total == 1
