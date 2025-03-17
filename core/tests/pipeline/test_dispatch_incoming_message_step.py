import pytest

from mersal.pipeline import (
    DispatchIncomingMessageStep,
    IncomingStepContext,
)
from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.transport import DefaultTransactionContext, TransactionContext
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = (
    "InvokerTestHelper",
    "TestDispatchIncomingMessageStep",
)


class InvokerTestHelper:
    def __init__(self, transaction_context: TransactionContext) -> None:
        self.transaction_context = transaction_context
        self.count = 0

    async def action(self):
        self.count += 1

    def invoker(self) -> HandlerInvoker:
        return HandlerInvoker(self.action, handler=None, transaction_context=self.transaction_context)


class TestDispatchIncomingMessageStep:
    async def test_raises_error_when__no_handlers(self):
        subject = DispatchIncomingMessageStep()

        message = LogicalMessageBuilder.build()
        transport_message = TransportMessageBuilder.build()
        invokers = HandlerInvokers(message=message, handler_invokers=[])
        transaction_context = DefaultTransactionContext()
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(invokers)
        counter = Counter()
        with pytest.raises(Exception):
            await subject(context, counter.task)

        assert counter.total == 0

    async def test_calls_all_invokers_and_next_step(self):
        subject = DispatchIncomingMessageStep()

        message = LogicalMessageBuilder.build()
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        invoker1 = InvokerTestHelper(transaction_context)
        invoker2 = InvokerTestHelper(transaction_context)
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[x.invoker() for x in [invoker1, invoker2]],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(invokers)
        counter = Counter()
        await subject(context, counter.task)

        for invoker in [invoker1, invoker2]:
            assert invoker.count == 1
        assert counter.total == 1
