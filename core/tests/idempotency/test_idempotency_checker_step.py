import uuid

import pytest

from mersal.idempotency.const import IDEMPOTENCY_CHECK_KEY
from mersal.idempotency.idempotency_checker_step import IdempotencyCheckerStep
from mersal.messages import LogicalMessage, TransportMessage
from mersal.persistence.in_memory.in_memory_message_tracker import (
    InMemoryMessageTracker,
)
from mersal.pipeline import IncomingStepContext
from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.transport import (
    DefaultTransactionContext,
    TransactionContext,
)
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

__all__ = ("TestIdempotencyCheckerStep",)


pytestmark = pytest.mark.anyio


class TestIdempotencyCheckerStep:
    @pytest.fixture
    def tracker(self) -> InMemoryMessageTracker:
        return InMemoryMessageTracker()

    @pytest.fixture
    def subject(self, tracker: InMemoryMessageTracker, request) -> IdempotencyCheckerStep:
        return IdempotencyCheckerStep(tracker, stop_invocation=request.param)

    @pytest.fixture
    def counter(self) -> Counter:
        return Counter()

    @pytest.fixture
    def transport_message(self) -> TransportMessage:
        return TransportMessageBuilder.build()

    @pytest.fixture
    def message(self) -> LogicalMessage:
        return LogicalMessageBuilder.build(use_dummy_message=True)

    @pytest.fixture
    def message_id(self, message: LogicalMessage) -> uuid.UUID:
        # The message_id is not None in tests, and we know it's a UUID
        return message.headers.message_id  # type: ignore[return-value]

    @pytest.fixture
    def transaction_context(self) -> TransactionContext:
        return DefaultTransactionContext()

    @pytest.fixture
    def context(
        self,
        transport_message: TransportMessage,
        transaction_context: TransactionContext,
        message: LogicalMessage,
    ) -> IncomingStepContext:
        _context = IncomingStepContext(message=transport_message, transaction_context=transaction_context)
        _context.save(message, LogicalMessage)
        return _context

    @pytest.mark.parametrize("subject", [True, False], indirect=True)
    async def test_calls_next_step(
        self,
        subject: IdempotencyCheckerStep,
        context: IncomingStepContext,
        counter: Counter,
    ):
        await subject(context, counter.task)
        assert counter.total == 1

    @pytest.mark.parametrize("subject", [True, False], indirect=True)
    async def test_tracking_message_with_no_commit(
        self,
        subject: IdempotencyCheckerStep,
        tracker: InMemoryMessageTracker,
        context: IncomingStepContext,
        counter: Counter,
        message_id: uuid.UUID,
        transaction_context: TransactionContext,
    ):
        await subject(context, counter.task)
        transaction_context.set_result(commit=False, ack=True)
        await transaction_context.complete()
        await transaction_context.close()

        assert not await tracker.is_message_tracked(message_id, transaction_context)

    @pytest.mark.parametrize("subject", [True, False], indirect=True)
    async def test_tracking_message_with_commit(
        self,
        subject: IdempotencyCheckerStep,
        tracker: InMemoryMessageTracker,
        context: IncomingStepContext,
        counter: Counter,
        message_id: uuid.UUID,
        transaction_context: TransactionContext,
    ):
        await subject(context, counter.task)

        transaction_context.set_result(commit=True, ack=True)
        await transaction_context.complete()
        await transaction_context.close()

        assert await tracker.is_message_tracked(message_id, transaction_context)

    @pytest.mark.parametrize("subject", [True], indirect=True)
    async def test_stopping_invokers_for_tracked_messages(
        self,
        subject: IdempotencyCheckerStep,
        tracker: InMemoryMessageTracker,
        context: IncomingStepContext,
        message: LogicalMessage,
        message_id: uuid.UUID,
        transaction_context: TransactionContext,
    ):
        invoker1_called = False

        async def invoker1_action():
            nonlocal invoker1_called
            invoker1_called = True

        invoker2_called = False

        async def invoker2_action():
            nonlocal invoker2_called
            invoker2_called = True

        invoker1 = HandlerInvoker(
            action=invoker1_action,
            handler=(),
            transaction_context=transaction_context,
        )
        invoker2 = HandlerInvoker(
            action=invoker2_action,
            handler=(),
            transaction_context=transaction_context,
        )
        invokers = HandlerInvokers(message=message, handler_invokers=[invoker1, invoker2])
        context.save(invokers)

        async def _next_step():
            for invoker in invokers:
                await invoker()

        # simulate a tracked message
        await tracker.track_message(message_id, transaction_context)

        # simulate another process
        await subject(context, _next_step)

        assert not invoker1_called
        assert not invoker2_called

    @pytest.mark.parametrize("subject", [False], indirect=True)
    async def test_not_stopping_invokers_for_tracked_messages(
        self,
        subject: IdempotencyCheckerStep,
        tracker: InMemoryMessageTracker,
        context: IncomingStepContext,
        message: LogicalMessage,
        message_id: uuid.UUID,
        transaction_context: TransactionContext,
    ):
        class MyFakeHandler:
            pass

        _ = MyFakeHandler()

        invoker1_called = False

        async def invoker1_action():
            nonlocal invoker1_called
            invoker1_called = True

        invoker2_called = False

        async def invoker2_action():
            nonlocal invoker2_called
            invoker2_called = True

        invoker1 = HandlerInvoker(action=invoker1_action, handler=(), transaction_context=transaction_context)
        invoker2 = HandlerInvoker(action=invoker2_action, handler=(), transaction_context=transaction_context)
        invokers = HandlerInvokers(message=message, handler_invokers=[invoker1, invoker2])
        context.save(invokers)

        async def _next_step():
            for invoker in invokers:
                await invoker()

        # simulate a tracked message
        await tracker.track_message(message_id, transaction_context)

        # simulate another process
        await subject(context, _next_step)

        assert invoker1_called
        assert invoker2_called
        assert message.headers[IDEMPOTENCY_CHECK_KEY]
