from datetime import UTC, datetime, timedelta

import pytest

from mersal.logging import NullLogger
from mersal.messages import MessageHeaders, TransportMessage
from mersal.persistence.in_memory import InMemoryTimeoutManager
from mersal.testing.core.test_doubles import TransportMessageBuilder
from mersal.threading.anyio.anyio_periodic_async_task_factory import AnyIOPeriodicTaskFactory
from mersal.timeouts import DueMessagesSender
from mersal.transport import TransactionContext
from mersal.transport.base_transport import BaseTransport

__all__ = ("TestDueMessagesSender",)


pytestmark = pytest.mark.anyio


class RecordingTransport(BaseTransport):
    def __init__(self, fail_for: set[str] | None = None) -> None:
        super().__init__("recording")
        self.sent: list[tuple[str, TransportMessage]] = []
        self._fail_for = fail_for or set()

    async def send(
        self, destination_address: str, message: TransportMessage, transaction_context: TransactionContext
    ) -> None:
        if destination_address in self._fail_for:
            raise RuntimeError("send failed")
        self.sent.append((destination_address, message))


def _deferred_message(recipient: str, delay: timedelta) -> TransportMessage:
    message = TransportMessageBuilder.build()
    message.headers[MessageHeaders.deferred_until_key] = (datetime.now(UTC) + delay).isoformat()
    message.headers[MessageHeaders.deferred_recipient_key] = recipient
    return message


async def _store(timeout_manager: InMemoryTimeoutManager, message: TransportMessage) -> None:
    deferred_until = message.headers.deferred_until
    if deferred_until is None:
        raise AssertionError("message isn't deferred")
    await timeout_manager.defer(deferred_until, message)


def _subject(transport: RecordingTransport, timeout_manager: InMemoryTimeoutManager) -> DueMessagesSender:
    logger = NullLogger()
    return DueMessagesSender(AnyIOPeriodicTaskFactory(logger=logger), transport, timeout_manager, logger)


class TestDueMessagesSender:
    async def test_sends_due_messages_to_their_recipient_without_defer_headers(self):
        timeout_manager = InMemoryTimeoutManager()
        transport = RecordingTransport()
        message = _deferred_message("recipient", timedelta(seconds=-1))
        await _store(timeout_manager, message)

        await _subject(transport, timeout_manager).send_due_messages()

        assert len(transport.sent) == 1
        address, sent = transport.sent[0]
        assert address == "recipient"
        assert sent.body == message.body
        assert sent.headers.message_id == message.headers.message_id
        assert MessageHeaders.deferred_until_key not in sent.headers
        assert MessageHeaders.deferred_recipient_key not in sent.headers
        assert len(timeout_manager) == 0

    async def test_leaves_messages_that_are_not_due(self):
        timeout_manager = InMemoryTimeoutManager()
        transport = RecordingTransport()
        await _store(timeout_manager, _deferred_message("recipient", timedelta(minutes=1)))

        await _subject(transport, timeout_manager).send_due_messages()

        assert transport.sent == []
        assert len(timeout_manager) == 1

    async def test_keeps_messages_that_failed_to_send_and_sends_the_rest(self):
        timeout_manager = InMemoryTimeoutManager()
        transport = RecordingTransport(fail_for={"broken"})
        await _store(timeout_manager, _deferred_message("broken", timedelta(seconds=-2)))
        await _store(timeout_manager, _deferred_message("recipient", timedelta(seconds=-1)))

        await _subject(transport, timeout_manager).send_due_messages()

        assert [address for address, _ in transport.sent] == ["recipient"]
        assert len(timeout_manager) == 1
