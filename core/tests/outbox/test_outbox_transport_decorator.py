import pytest

from mersal.outbox.outbox_incoming_step import OutboxIncomingStep
from mersal.outbox.outbox_transport_decorator import OutboxTransportDecorator
from mersal.transport.default_transaction_context import DefaultTransactionContext
from mersal.transport.outgoing_message import OutgoingMessage
from mersal_testing.test_doubles import (
    OutboxStorageTestDouble,
    TransportMessageBuilder,
    TransportTestDouble,
)

__all__ = ("TestOutboxTransportDecorator",)


pytestmark = pytest.mark.anyio


class TestOutboxTransportDecorator:
    async def test_invokes_send_normally_with_no_use_outbox_is_not_set(self):
        transport = TransportTestDouble()
        outbox_storage = OutboxStorageTestDouble()
        transaction_context = DefaultTransactionContext()
        message = TransportMessageBuilder.build()

        subject = OutboxTransportDecorator(transport=transport, outbox_storage=outbox_storage)

        destination_address = "moon"
        assert not transport.sent_messages

        await subject.send(destination_address, message, transaction_context)
        transaction_context.set_result(True, True)
        await transaction_context.complete()
        assert transport.sent_messages
        sent_messages = transport.sent_messages[0]

        assert sent_messages[0][0].transport_message is message
        assert not transaction_context.items.get("outgoing-messages")

    async def test_stores_message_when_use_outbox_is_set(self):
        transport = TransportTestDouble()
        outbox_storage = OutboxStorageTestDouble()
        transaction_context = DefaultTransactionContext()
        transaction_context.items[OutboxIncomingStep.use_outbox_key] = True

        message = TransportMessageBuilder.build()

        subject = OutboxTransportDecorator(transport=transport, outbox_storage=outbox_storage)

        destination_address = "moon"
        assert not transport.sent_messages
        await subject.send(destination_address, message, transaction_context)
        transaction_context.set_result(True, True)
        await transaction_context.complete()
        assert not transport.sent_messages

    async def test_transaction_commit(self):
        transport = TransportTestDouble()
        outbox_storage = OutboxStorageTestDouble()
        transaction_context = DefaultTransactionContext()
        transaction_context.items[OutboxIncomingStep.use_outbox_key] = True

        message = TransportMessageBuilder.build()

        subject = OutboxTransportDecorator(transport=transport, outbox_storage=outbox_storage)

        destination_address = "moon"
        await subject.send(destination_address, message, transaction_context)

        transaction_context.set_result(True, True)
        await transaction_context.complete()

        assert outbox_storage.saved_outgoing_messages
        assert outbox_storage.saved_outgoing_messages[0][1] is transaction_context
        assert outbox_storage.saved_outgoing_messages[0][0][0] == OutgoingMessage(destination_address, message)

    async def test_transaction_commit_multiple_sends(self):
        transport = TransportTestDouble()
        outbox_storage = OutboxStorageTestDouble()
        transaction_context = DefaultTransactionContext()
        transaction_context.items[OutboxIncomingStep.use_outbox_key] = True

        message = TransportMessageBuilder.build()
        message2 = TransportMessageBuilder.build()

        subject = OutboxTransportDecorator(transport=transport, outbox_storage=outbox_storage)

        destination_address = "moon"
        await subject.send(destination_address, message, transaction_context)
        await subject.send(destination_address, message2, transaction_context)

        transaction_context.set_result(True, True)
        await transaction_context.complete()

        assert len(outbox_storage.saved_outgoing_messages) == 1
        assert len(outbox_storage.saved_outgoing_messages[0][0]) == 2
        assert outbox_storage.saved_outgoing_messages[0][0][0] == OutgoingMessage(destination_address, message)
        assert outbox_storage.saved_outgoing_messages[0][0][1] == OutgoingMessage(destination_address, message2)

    async def test_transaction_commit_without_outbox_connection(self):
        transport = TransportTestDouble()
        outbox_storage = OutboxStorageTestDouble()
        transaction_context = DefaultTransactionContext()
        transaction_context.items[OutboxIncomingStep.use_outbox_key] = True

        message = TransportMessageBuilder.build()

        subject = OutboxTransportDecorator(transport=transport, outbox_storage=outbox_storage)

        destination_address = "moon"
        await subject.send(destination_address, message, transaction_context)

        transaction_context.set_result(True, True)
        await transaction_context.complete()

        assert outbox_storage.saved_outgoing_messages
        assert outbox_storage.saved_outgoing_messages[0][1] is transaction_context
        assert outbox_storage.saved_outgoing_messages[0][0][0] == OutgoingMessage(destination_address, message)
