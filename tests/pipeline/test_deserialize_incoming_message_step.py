import pytest

from mersal.messages import LogicalMessage
from mersal.pipeline import DeserializeIncomingMessageStep, IncomingStepContext
from mersal.transport import DefaultTransactionContext
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    SerializerTestDouble,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = ("TestDeserializeIncomingMessageStep",)


class TestDeserializeIncomingMessageStep:
    async def test_deserializtion_and_calling_next_step(self):
        serializer = SerializerTestDouble()
        logical_message = LogicalMessageBuilder.build()
        serializer.deserialize_stub = logical_message

        subject = DeserializeIncomingMessageStep(serializer)

        message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        context = IncomingStepContext(
            message=message,
            transaction_context=transaction_context,
        )
        context.save_keys("do-not-serialize", True)
        counter = Counter()
        await subject(context, counter.task)

        assert logical_message is context.load(LogicalMessage)
        assert counter.total == 1
