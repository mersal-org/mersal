import pytest

from mersal.messages import LogicalMessage
from mersal.outbox.outbox_incoming_step import OutboxIncomingStep
from mersal.pipeline import IncomingStepContext
from mersal.transport import (
    DefaultTransactionContext,
)
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = ("TestOutboxStep",)


class TestOutboxStep:
    @pytest.fixture
    def subject(self) -> OutboxIncomingStep:
        return OutboxIncomingStep()

    async def test_sets_use_outbox_and_call_next_step(self, subject: OutboxIncomingStep):
        transaction_context = DefaultTransactionContext()
        message = LogicalMessageBuilder.build(use_dummy_message=True)
        transport_message = TransportMessageBuilder.build()

        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )

        context.save(message, LogicalMessage)
        counter = Counter()
        await subject(context, counter.task)
        use_outbox = transaction_context.items.get(OutboxIncomingStep.use_outbox_key)
        assert use_outbox
        assert counter.total == 1
