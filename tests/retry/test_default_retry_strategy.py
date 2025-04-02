import uuid
from collections.abc import Callable
from typing import Any, Literal

import pytest

from mersal.messages import TransportMessage
from mersal.pipeline.incoming_step_context import IncomingStepContext
from mersal.retry import (
    DeadletterQueueErrorHandler,
    DefaultFailFastChecker,
    DefaultRetryStrategy,
    InMemoryErrorTracker,
)
from mersal.retry.default_retry_step import DefaultRetryStep
from mersal.transport import (
    DefaultTransactionContext,
    TransactionContext,
)
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal.types.callable_types import AsyncAnyCallable
from mersal_testing.test_doubles import (
    ErrorTrackerTestTouble,
    TransportMessageBuilder,
)

__all__ = (
    "TestDefaultRetryStrategy",
    "TransactionContextAssertionHelper",
)


pytestmark = pytest.mark.anyio


class TransactionContextAssertionHelper:
    def __init__(self, transaction_context: TransactionContext) -> None:
        self.transaction_context = transaction_context
        self.ack = False
        self.nack = False
        self.committed = False
        self.rollback = False
        self.transaction_context.on_commit(self.action_generator("committed"))
        self.transaction_context.on_ack(self.action_generator("ack"))
        self.transaction_context.on_nack(self.action_generator("nack"))
        self.transaction_context.on_rollback(self.action_generator("rollback"))

    def action_generator(self, attribute: Literal["ack", "nack", "committed", "rollback"]):
        async def action(_):
            setattr(self, attribute, True)

        return action

    def assert_committed(self, committed: bool):
        assert self.committed == committed
        assert self.rollback != committed

    def assert_ack(self, ack: bool):
        assert self.ack == ack
        assert self.nack != ack


class TestDefaultRetryStrategy:
    @pytest.fixture(scope="function")
    def in_memory_network(self) -> InMemoryNetwork:
        return InMemoryNetwork()

    @pytest.fixture(scope="function")
    def error_queue_name(self) -> str:
        return "error-error"

    @pytest.fixture(scope="function")
    def transport(self, in_memory_network: InMemoryNetwork) -> InMemoryTransport:
        return InMemoryTransport(InMemoryTransportConfig(network=in_memory_network, input_queue_address="moon"))

    @pytest.fixture(scope="function")
    def error_handler(self, transport: InMemoryTransport, error_queue_name: str) -> DeadletterQueueErrorHandler:
        return DeadletterQueueErrorHandler(transport=transport, error_queue_name=error_queue_name)

    @pytest.fixture(scope="function")
    def error_tracker(self) -> ErrorTrackerTestTouble:
        return ErrorTrackerTestTouble(maximum_failure_times=2)

    @pytest.fixture(scope="function")
    def fail_fast_checker(self) -> DefaultFailFastChecker:
        return DefaultFailFastChecker([])

    @pytest.fixture(scope="function")
    def subject(
        self,
        error_handler: DeadletterQueueErrorHandler,
        error_tracker: InMemoryErrorTracker,
        fail_fast_checker: DefaultFailFastChecker,
    ) -> DefaultRetryStep:
        strategy = DefaultRetryStrategy(error_tracker, error_handler, fail_fast_checker)
        return strategy.get_retry_step()

    @pytest.fixture(scope="function")
    def transport_message(self) -> TransportMessage:
        return TransportMessageBuilder.build()

    @pytest.fixture(scope="function")
    def message_id(self, transport_message: TransportMessage) -> Any:
        return transport_message.headers.message_id

    @pytest.fixture(scope="function")
    def transaction_context(self) -> DefaultTransactionContext:
        return DefaultTransactionContext()

    @pytest.fixture(scope="function")
    def incoming_step_context(
        self,
        transport_message: TransportMessage,
        transaction_context: DefaultTransactionContext,
    ) -> IncomingStepContext:
        return IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )

    @pytest.fixture(scope="function")
    def get_error_queue_latest_message(
        self, in_memory_network: InMemoryNetwork, error_queue_name: str
    ) -> Callable[..., TransportMessage | None]:
        def get():
            return in_memory_network.get_next(error_queue_name)

        return get

    @pytest.fixture(scope="function")
    async def assertion_helper(self, transaction_context: DefaultTransactionContext):
        return TransactionContextAssertionHelper(transaction_context)

    @pytest.fixture(scope="function")
    async def run_subject_process(
        self,
        subject: DefaultRetryStep,
        incoming_step_context: IncomingStepContext,
        fail_fast_checker: DefaultFailFastChecker,
        error_tracker: InMemoryErrorTracker,
        transaction_context: DefaultTransactionContext,
    ):
        async def run_subject(
            next_step: AsyncAnyCallable,
            fail_fast_exceptions: list[type[Exception]] | None = None,
            maximum_no_of_failures: int = 2,
        ):
            if fail_fast_exceptions:
                fail_fast_checker.fail_fast_exceptions = fail_fast_exceptions

            error_tracker.maximum_failure_times = maximum_no_of_failures
            await subject(incoming_step_context, next_step)
            await transaction_context.complete()

        return run_subject

    @pytest.fixture(scope="function")
    async def assert_message_in_error_queue(self, in_memory_network: InMemoryNetwork, error_queue_name: str):
        def assertion(in_queue: bool, message_id: uuid.UUID | None = None):
            received_message = in_memory_network.get_next(error_queue_name)
            assert bool(received_message) is in_queue
            if in_queue and message_id:
                assert received_message.headers.message_id == message_id  # type: ignore

        return assertion

    @pytest.fixture(scope="function")
    async def assert_error_tracker(
        self,
        error_tracker: ErrorTrackerTestTouble,
        message_id: uuid.UUID,
    ):
        async def assertion(has_failed_too_many_times: bool, exceptions: list[Exception] | None = None):
            assert await error_tracker.has_failed_too_many_times(message_id) is has_failed_too_many_times
            if exceptions is not None:
                assert [type(x) for x in await error_tracker.get_exceptions(message_id)] == [
                    type(x) for x in exceptions
                ]

        return assertion

    async def test_committing_transaction_when_next_step_does_not_throw(
        self, run_subject_process, assertion_helper: TransactionContextAssertionHelper
    ):
        called = 0

        async def next_step():
            nonlocal called
            called += 1

        await run_subject_process(next_step)

        assert called == 1
        assertion_helper.assert_committed(True)
        assertion_helper.assert_ack(True)

    async def test_fail_fast_exceptions(
        self,
        run_subject_process,
        assert_message_in_error_queue,
        message_id: uuid.UUID,
        assertion_helper: TransactionContextAssertionHelper,
        assert_error_tracker,
        error_tracker: ErrorTrackerTestTouble,
    ):
        exception = ValueError()

        async def next_step():
            raise exception

        await run_subject_process(next_step, fail_fast_exceptions=[ValueError])

        assert [type(x) for x in error_tracker._registered_errors_spy[message_id]] == [type(exception)]
        await assert_error_tracker(True, [exception])

        assert_message_in_error_queue(True, message_id)
        assertion_helper.assert_committed(False)
        assertion_helper.assert_ack(True)

    async def test_exception_with_retry(
        self,
        run_subject_process,
        assert_message_in_error_queue,
        assertion_helper: TransactionContextAssertionHelper,
        assert_error_tracker,
    ):
        exception = ValueError()

        async def next_step():
            raise exception

        await run_subject_process(next_step)

        await assert_error_tracker(False, [exception])
        assert_message_in_error_queue(False)
        assertion_helper.assert_committed(False)
        assertion_helper.assert_ack(False)

    async def test_reached_max_exceptions(
        self,
        run_subject_process,
        assert_message_in_error_queue,
        assertion_helper: TransactionContextAssertionHelper,
        message_id: uuid.UUID,
        assert_error_tracker,
    ):
        exception = ValueError()

        async def next_step():
            raise exception

        await run_subject_process(next_step, maximum_no_of_failures=1)
        await assert_error_tracker(True, [exception])
        assert_message_in_error_queue(True, message_id)
        assertion_helper.assert_committed(False)
        assertion_helper.assert_ack(True)

    async def test_aggregates_exceptions_when_sending_to_deadletter_queue(
        self,
        run_subject_process,
        message_id: uuid.UUID,
        error_tracker: ErrorTrackerTestTouble,
        get_error_queue_latest_message: Callable[..., TransportMessage | None],
    ):
        exception = ValueError()

        async def next_step():
            raise exception

        await error_tracker.register_error(message_id, ValueError())
        await error_tracker.register_error(message_id, ValueError())
        await run_subject_process(next_step, maximum_no_of_failures=3)
        message = get_error_queue_latest_message()
        assert message
        assert "--" in message.headers["error_details"]

    async def test_sending_a_clone_of_transport_message_deadletter_queue(
        self,
        run_subject_process,
        message_id: uuid.UUID,
        transport_message: TransportMessage,
        error_tracker: ErrorTrackerTestTouble,
        get_error_queue_latest_message: Callable[..., TransportMessage | None],
    ):
        exception = ValueError()

        async def next_step():
            raise exception

        await error_tracker.register_error(message_id, ValueError())
        await run_subject_process(next_step, maximum_no_of_failures=2)
        message = get_error_queue_latest_message()
        assert message is not transport_message
