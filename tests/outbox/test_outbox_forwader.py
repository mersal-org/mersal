import anyio
import pytest

from mersal.outbox.outbox_forwarder import OutboxForwarder
from mersal.threading.anyio.anyio_periodic_async_task_factory import (
    AnyIOPeriodicTaskFactory,
)
from mersal.transport.default_transaction_context import DefaultTransactionContext
from mersal_testing.test_doubles import (
    OutboxStorageTestDouble,
    OutgoingMessageBuilder,
    TransportMessageBuilder,
    TransportTestDouble,
)

__all__ = ("TestOutboxForwader",)


pytestmark = pytest.mark.anyio


class TestOutboxForwader:
    async def test_it_forwards_stored_outbox_messages_to_transport(self):
        transport = TransportTestDouble()

        outbox_storage = OutboxStorageTestDouble()
        destination_address = "sun"
        _messages = [
            OutgoingMessageBuilder.build(
                destination_address=destination_address,
                transport_message=TransportMessageBuilder.build(),
            ),
            OutgoingMessageBuilder.build(
                destination_address=destination_address,
                transport_message=TransportMessageBuilder.build(),
            ),
        ]
        await outbox_storage.save(_messages, DefaultTransactionContext())
        subject = OutboxForwarder(
            periodic_task_factory=AnyIOPeriodicTaskFactory(),
            transport=transport,
            outbox_storage=outbox_storage,
            forwarding_period=0.1,
        )
        await subject.start()
        await anyio.sleep(0.5)
        await subject.stop()

        assert transport.sent_messages
        sent_messages = transport.sent_messages[0]
        assert len(sent_messages) == 2
        assert (
            sent_messages[0][0].transport_message.headers.message_id
            == _messages[0].transport_message.headers.message_id
        )
        assert (
            sent_messages[0][1].transport_message.headers.message_id
            == _messages[1].transport_message.headers.message_id
        )

    async def test_completes_and_closes_batch(self):
        transport = TransportTestDouble()
        outbox_batch_completion_called = False
        outbox_batch_close_called = False

        def outbox_batch_completion_action():
            nonlocal outbox_batch_completion_called
            outbox_batch_completion_called = True

        def outbox_batch_close_action():
            nonlocal outbox_batch_close_called
            outbox_batch_close_called = True

        outbox_storage = OutboxStorageTestDouble()
        outbox_storage._complete_action = outbox_batch_completion_action
        outbox_storage._close_action = outbox_batch_close_action
        _messages = [
            OutgoingMessageBuilder.build(
                transport_message=TransportMessageBuilder.build(),
            ),
        ]
        await outbox_storage.save(_messages, DefaultTransactionContext())
        subject = OutboxForwarder(
            periodic_task_factory=AnyIOPeriodicTaskFactory(),
            transport=transport,
            outbox_storage=outbox_storage,
            forwarding_period=0.1,
        )
        await subject.start()
        await anyio.sleep(0.5)
        await subject.stop()

        assert outbox_batch_completion_called
        assert outbox_batch_close_called

    async def test_empty_batch(self):
        transport = TransportTestDouble()
        outbox_batch_completion_called = False
        outbox_batch_close_called = False

        def outbox_batch_completion_action():
            nonlocal outbox_batch_completion_called
            outbox_batch_completion_called = True

        def outbox_batch_close_action():
            nonlocal outbox_batch_close_called
            outbox_batch_close_called = True

        outbox_storage = OutboxStorageTestDouble()
        outbox_storage._complete_action = outbox_batch_completion_action
        outbox_storage._close_action = outbox_batch_close_action
        _messages = []
        await outbox_storage.save(_messages, DefaultTransactionContext())
        subject = OutboxForwarder(
            periodic_task_factory=AnyIOPeriodicTaskFactory(),
            transport=transport,
            outbox_storage=outbox_storage,
            forwarding_period=0.1,
        )
        await subject.start()
        await anyio.sleep(0.5)
        await subject.stop()

        assert not transport.sent_messages
        assert not outbox_batch_completion_called
        assert outbox_batch_close_called
