from collections.abc import Callable
from functools import partial

import pytest

from mersal.transport import DefaultTransactionContext, TransactionContext
from mersal.transport.default_transaction_context import (
    InvalidTransactioContextStateError,
)

__all__ = (
    "OnErrorExceptionCallback",
    "TestDefaultTransactionContext",
    "action_maker_with_failure",
    "default_subject_actions",
    "dummy_action_maker",
)


pytestmark = pytest.mark.anyio


class OnErrorExceptionCallback:
    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self, exception: Exception):
        self.call_count += 1


@pytest.fixture
def default_subject_actions():
    def maker(subject: DefaultTransactionContext, events: list[str]):
        def action_maker(event: str):
            async def action(_: TransactionContext):
                events.append(event)

            return action

        subject.on_commit(action_maker("commit"))
        subject.on_ack(action_maker("ack"))
        subject.on_rollback(action_maker("rollback"))
        subject.on_nack(action_maker("nack"))
        subject.on_close(action_maker("close"))

    return maker


def action_maker_with_failure(events: list[str], event: str, should_raise: bool = False):
    async def action(_: TransactionContext):
        if should_raise:
            raise Exception(f"Failed for {event}")

        events.append(event)

    return action


def dummy_action_maker():
    async def action(_: TransactionContext):
        pass

    return action


class TestDefaultTransactionContext:
    async def test_happy_path(self, default_subject_actions):
        subject = DefaultTransactionContext()
        events: list[str] = []

        default_subject_actions(subject, events)
        subject.set_result(commit=True, ack=True)

        async with subject:
            await subject.complete()

        assert events == ["commit", "ack", "close"]

    async def test_abort_and_retry(self, default_subject_actions):
        subject = DefaultTransactionContext()
        events: list[str] = []
        default_subject_actions(subject, events)
        subject.set_result(commit=False, ack=False)

        async with subject:
            await subject.complete()

        assert events == ["rollback", "nack", "close"]

    async def test_abort_and_forward_to_deadletter_queue(self, default_subject_actions):
        subject = DefaultTransactionContext()
        events: list[str] = []
        default_subject_actions(subject, events)
        subject.set_result(commit=False, ack=True)

        async with subject:
            await subject.complete()

        assert events == ["rollback", "ack", "close"]

    async def test_raise_exception_when_set_result_not_called(self):
        subject = DefaultTransactionContext()
        with pytest.raises(InvalidTransactioContextStateError):
            await subject.complete()

    async def test_failure_on_commit(self):
        subject = DefaultTransactionContext()
        events: list[str] = []

        action_maker = partial(action_maker_with_failure, events)
        subject.on_commit(action_maker("commit", True))
        subject.on_ack(action_maker("ack"))
        subject.on_rollback(action_maker("rollback"))
        subject.on_nack(action_maker("nack"))
        subject.on_close(action_maker("close"))

        subject.set_result(commit=True, ack=True)

        async with subject:
            with pytest.raises(Exception):
                await subject.complete()

        assert events == ["nack", "close"]

    async def test_failure_on_rollback(self):
        subject = DefaultTransactionContext()
        events: list[str] = []

        action_maker = partial(action_maker_with_failure, events)

        subject.on_commit(action_maker("commit"))
        subject.on_ack(action_maker("ack"))
        subject.on_rollback(action_maker("rollback", True))
        subject.on_nack(action_maker("nack"))
        subject.on_close(action_maker("close"))

        subject.set_result(commit=False, ack=True)

        async with subject:
            with pytest.raises(Exception):
                await subject.complete()

        assert events == ["nack", "close"]

    @pytest.mark.parametrize("should_commit_and_fail", [True, False])
    async def test_on_error_callback_after_rollback_or_commit_failure_followed_by_nack_failure(
        self,
        should_commit_and_fail: bool,
    ):
        subject = DefaultTransactionContext()
        events: list[str] = []

        _partial_action_maker = partial(action_maker_with_failure, events)

        on_error_callback = OnErrorExceptionCallback()

        subject.on_commit(_partial_action_maker("commit", should_commit_and_fail))
        subject.on_ack(_partial_action_maker("ack"))
        subject.on_rollback(_partial_action_maker("rollback", not should_commit_and_fail))
        subject.on_nack(_partial_action_maker("nack", True))
        subject.on_close(_partial_action_maker("close"))

        subject.set_result(commit=should_commit_and_fail, ack=True)

        subject.on_error(on_error_callback)
        async with subject:
            with pytest.raises(Exception):
                await subject.complete()
        assert events == ["close"]
        assert on_error_callback.call_count == 1

    @pytest.mark.parametrize("should_ack_and_fail", [True, False])
    async def test_work_normally_when_ack_or_nack_failure(self, should_ack_and_fail: bool):
        """Ideally the transport should not fail the ack/nack and should retry"""
        subject = DefaultTransactionContext()
        events: list[str] = []

        _partial_action_maker = partial(action_maker_with_failure, events)

        on_error_callback = OnErrorExceptionCallback()

        subject.on_commit(_partial_action_maker("commit"))
        subject.on_ack(_partial_action_maker("ack", should_ack_and_fail))
        subject.on_rollback(_partial_action_maker("rollback"))
        subject.on_nack(_partial_action_maker("nack", not should_ack_and_fail))
        subject.on_close(_partial_action_maker("close"))

        subject.set_result(commit=True, ack=should_ack_and_fail)

        subject.on_error(on_error_callback)
        async with subject:
            with pytest.raises(Exception):
                await subject.complete()
        assert events == ["commit", "close"]

        assert on_error_callback.call_count == 0

    @pytest.mark.parametrize(
        "action",
        [
            lambda x: x.on_commit(dummy_action_maker()),
            lambda x: x.on_rollback(dummy_action_maker()),
            lambda x: x.on_ack(dummy_action_maker()),
            lambda x: x.on_nack(dummy_action_maker()),
            lambda x: x.on_close(dummy_action_maker()),
        ],
    )
    async def test_raises_exceptions_when_adding_actions_after_completion(
        self, action: Callable[[DefaultTransactionContext], None]
    ):
        subject = DefaultTransactionContext()

        subject.set_result(commit=True, ack=True)

        async with subject:
            await subject.complete()
            with pytest.raises(InvalidTransactioContextStateError):
                action(subject)

    async def test_rollback_and_nack_on_close_if_not_must_commit_and_not_musc_ack(
        self,
    ):
        subject = DefaultTransactionContext()
        events: list[str] = []

        _partial_action_maker = partial(action_maker_with_failure, events)

        subject.on_commit(_partial_action_maker("commit"))
        subject.on_ack(
            _partial_action_maker(
                "ack",
            )
        )
        subject.on_rollback(_partial_action_maker("rollback"))
        subject.on_nack(
            _partial_action_maker(
                "nack",
            )
        )
        subject.on_close(_partial_action_maker("close"))

        subject.set_result(commit=False, ack=False)

        async with subject:
            pass
        assert events == ["rollback", "nack", "close"]

    async def test_calling_on_error_actions_if_rollback_or_nack_fail_on_close(
        self,
    ):
        subject = DefaultTransactionContext()
        events: list[str] = []

        _partial_action_maker = partial(action_maker_with_failure, events)

        on_error_callback = OnErrorExceptionCallback()

        subject.on_commit(_partial_action_maker("commit"))
        subject.on_ack(
            _partial_action_maker(
                "ack",
            )
        )
        subject.on_rollback(_partial_action_maker("rollback", True))
        subject.on_nack(_partial_action_maker("nack", True))
        subject.on_close(_partial_action_maker("close"))

        subject.set_result(commit=False, ack=False)

        subject.on_error(on_error_callback)
        async with subject:
            pass
        assert events == ["close"]
        assert on_error_callback.call_count == 2

    async def test_calling_on_error_actions_if_on_close_actions_fail(
        self,
    ):
        subject = DefaultTransactionContext()
        events: list[str] = []

        _partial_action_maker = partial(action_maker_with_failure, events)
        on_error_callback = OnErrorExceptionCallback()

        subject.on_commit(_partial_action_maker("commit"))
        subject.on_ack(
            _partial_action_maker(
                "ack",
            )
        )
        subject.on_rollback(_partial_action_maker("rollback"))
        subject.on_nack(_partial_action_maker("nack"))
        subject.on_close(_partial_action_maker("close", True))

        subject.set_result(commit=True, ack=True)

        subject.on_error(on_error_callback)
        async with subject:
            pass
        assert not events
        assert on_error_callback.call_count == 1

    async def test_calling_idempotent_behaviour_on_multiple_close(
        self,
    ):
        subject = DefaultTransactionContext()
        events: list[str] = []
        _partial_action_maker = partial(action_maker_with_failure, events)

        on_error_callback = OnErrorExceptionCallback()

        subject.on_close(_partial_action_maker("close", True))
        subject.on_error(on_error_callback)
        async with subject:
            pass
        # imaginary
        subject.on_close(_partial_action_maker("close", True))

        await subject.close()
        assert on_error_callback.call_count == 1
