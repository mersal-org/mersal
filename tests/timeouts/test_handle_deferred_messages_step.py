from datetime import UTC, datetime, timedelta

import pytest

from mersal.exceptions import DeferralNotSupportedError, MersalExceptionError
from mersal.messages import MessageHeaders, TransportMessage
from mersal.persistence.in_memory import InMemoryTimeoutManager
from mersal.pipeline import IncomingStepContext
from mersal.testing.core.counter import Counter
from mersal.testing.core.test_doubles import TransportMessageBuilder
from mersal.timeouts import DisabledTimeoutManager, HandleDeferredMessagesStep
from mersal.transport import DefaultTransactionContext, TransactionContext
from mersal.transport.base_transport import BaseTransport

__all__ = ("TestHandleDeferredMessagesStep",)


pytestmark = pytest.mark.anyio


class RecordingTransport(BaseTransport):
    def __init__(self) -> None:
        super().__init__("recording")
        self.sent: list[tuple[str, TransportMessage]] = []

    async def send(
        self, destination_address: str, message: TransportMessage, transaction_context: TransactionContext
    ) -> None:
        self.sent.append((destination_address, message))


def _deferred_message(recipient: str | None = "recipient") -> TransportMessage:
    message = TransportMessageBuilder.build()
    message.headers[MessageHeaders.deferred_until_key] = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    if recipient is not None:
        message.headers[MessageHeaders.deferred_recipient_key] = recipient
    return message


def _context(message: TransportMessage) -> IncomingStepContext:
    return IncomingStepContext(message=message, transaction_context=DefaultTransactionContext())


class TestHandleDeferredMessagesStep:
    async def test_passes_non_deferred_messages_down_the_pipeline(self):
        timeout_manager = InMemoryTimeoutManager()
        subject = HandleDeferredMessagesStep(timeout_manager, RecordingTransport())
        counter = Counter()

        await subject(_context(TransportMessageBuilder.build()), counter.task)

        assert counter.total == 1
        assert len(timeout_manager) == 0

    async def test_stores_deferred_messages_instead_of_handling_them(self):
        timeout_manager = InMemoryTimeoutManager()
        subject = HandleDeferredMessagesStep(timeout_manager, RecordingTransport())
        counter = Counter()

        await subject(_context(_deferred_message()), counter.task)

        assert counter.total == 0
        assert len(timeout_manager) == 1

    async def test_forwards_deferred_messages_to_the_external_timeout_manager(self):
        timeout_manager = InMemoryTimeoutManager()
        transport = RecordingTransport()
        subject = HandleDeferredMessagesStep(timeout_manager, transport, external_timeout_manager_address="timeouts")
        counter = Counter()
        message = _deferred_message()

        await subject(_context(message), counter.task)

        assert counter.total == 0
        assert len(timeout_manager) == 0
        assert transport.sent == [("timeouts", message)]

    async def test_raises_when_the_deferred_recipient_is_missing(self):
        subject = HandleDeferredMessagesStep(InMemoryTimeoutManager(), RecordingTransport())

        with pytest.raises(MersalExceptionError):
            await subject(_context(_deferred_message(recipient=None)), Counter().task)

    async def test_raises_without_a_configured_timeout_manager(self):
        subject = HandleDeferredMessagesStep(DisabledTimeoutManager(), RecordingTransport())
        counter = Counter()

        with pytest.raises(DeferralNotSupportedError):
            await subject(_context(_deferred_message()), counter.task)
        assert counter.total == 0
