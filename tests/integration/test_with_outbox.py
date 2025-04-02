from asyncio import sleep

import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.idempotency import MessageTracker
from mersal.outbox.config import OutboxConfig
from mersal.outbox.outbox_storage import OutboxStorage
from mersal.outbox.plugin import OutboxPlugin
from mersal.persistence.in_memory.in_memory_message_tracker import (
    InMemoryMessageTracker,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.message_handlers.message_handler_that_counts import (
    MessageHandlerThatCounts,
)
from mersal_testing.message_handlers.message_handler_that_sends_local_messages import (
    MessageHandlerThatSendsLocalMessages,
    MessageThatSendsMultipleMessages,
)
from mersal_testing.messages import BasicMessageA, BasicMessageB
from mersal_testing.test_doubles.outbox.outbox_storage_test_double import (
    OutboxStorageTestDouble,
)

__all__ = ("TestOutboxIntegration",)


pytestmark = pytest.mark.anyio


class TestOutboxIntegration:
    @pytest.fixture
    def outbox_storage(self) -> OutboxStorageTestDouble:
        return OutboxStorageTestDouble()

    @pytest.fixture
    def outbox_config(self, outbox_storage: OutboxStorage) -> OutboxConfig:
        return OutboxConfig(storage=outbox_storage)

    @pytest.fixture
    def message_tracker(self) -> MessageTracker:
        return InMemoryMessageTracker()

    async def test_message_storage_and_forwarding(
        self, outbox_storage: OutboxStorageTestDouble, outbox_config: OutboxConfig
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        activator.register(
            MessageThatSendsMultipleMessages,
            lambda _, mersal: MessageHandlerThatSendsLocalMessages(mersal=mersal),
        )
        handler_for_message_a = MessageHandlerThatCounts()
        handler_for_message_b = MessageHandlerThatCounts()
        activator.register(BasicMessageA, lambda _, __: handler_for_message_a)
        activator.register(BasicMessageB, lambda _, __: handler_for_message_b)
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            OutboxPlugin(outbox_config),
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.start()
        message = MessageThatSendsMultipleMessages(sent_messages=[BasicMessageA(), BasicMessageB()])
        await app.send_local(message)

        await sleep(0.5)
        assert len(outbox_storage.saved_outgoing_messages) == 1
        assert len(outbox_storage.saved_outgoing_messages[0]) == 2
        await sleep(1.1)
        assert len(outbox_storage.saved_outgoing_messages) == 0
        assert handler_for_message_a.count == 1
        assert handler_for_message_b.count == 1
        await app.stop()
