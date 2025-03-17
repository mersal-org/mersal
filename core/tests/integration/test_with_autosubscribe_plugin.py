import uuid

import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.lifespan.autosubscribe import (
    AutosubscribeConfig,
)
from mersal.messages import MessageCompletedEvent
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.app_runner_helper import AppRunnerHelper
from mersal_testing.test_doubles import DummyMessage

__all__ = (
    "PublishedMessage1",
    "PublishedMessage2",
    "PublishedMessageHandler",
    "TestAutosubcribePlugin",
)


pytestmark = pytest.mark.anyio


class PublishedMessage1:
    pass


class PublishedMessage2:
    pass


class PublishedMessageHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, message: DummyMessage | PublishedMessage1 | PublishedMessage2 | MessageCompletedEvent):
        self.calls += 1


class TestAutosubcribePlugin:
    async def test_pub_sub_with_autosubscribe_plugin(self):
        network = InMemoryNetwork()
        subscription_store = InMemorySubscriptionStore()
        queue_address = "test-queue"
        queue_address2 = "test-queue2"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        plugins2 = [
            InMemoryTransportPluginConfig(network, queue_address2).plugin,
            AutosubscribeConfig({PublishedMessage1, PublishedMessage2}).plugin,
        ]

        activator2 = BuiltinHandlerActivator()
        app2 = Mersal(
            "m2",
            activator2,
            plugins=plugins2,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )
        handler = PublishedMessageHandler()
        messaage_completed_event_handler = PublishedMessageHandler()
        activator2.register(PublishedMessage1, lambda _, __: handler)
        activator2.register(PublishedMessage2, lambda _, __: handler)
        activator2.register(MessageCompletedEvent, lambda _, __: messaage_completed_event_handler)
        app_runner = AppRunnerHelper(app2)
        await app_runner.run()
        await app.publish(PublishedMessage1(), {})
        await app.publish(PublishedMessage2(), {})
        await app.publish(
            MessageCompletedEvent(completed_message_id=uuid.uuid4()),
            {},
        )

        await app_runner.stop(0.1)

        assert handler.calls == 2

    async def test_pub_sub_with_autosubscribe_plugin_using_mersal_construct(self):
        network = InMemoryNetwork()
        subscription_store = InMemorySubscriptionStore()
        queue_address = "test-queue"
        queue_address2 = "test-queue2"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        plugins2 = [
            InMemoryTransportPluginConfig(network, queue_address2).plugin,
        ]

        activator2 = BuiltinHandlerActivator()
        app2 = Mersal(
            "m2",
            activator2,
            plugins=plugins2,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
            autosubscribe=AutosubscribeConfig(events={PublishedMessage1, PublishedMessage2}),
        )
        handler = PublishedMessageHandler()
        messaage_completed_event_handler = PublishedMessageHandler()
        activator2.register(PublishedMessage1, lambda _, __: handler)
        activator2.register(PublishedMessage2, lambda _, __: handler)
        activator2.register(MessageCompletedEvent, lambda _, __: messaage_completed_event_handler)
        app_runner = AppRunnerHelper(app2)
        await app_runner.run()
        await app.publish(PublishedMessage1(), {})
        await app.publish(PublishedMessage2(), {})
        await app.publish(
            MessageCompletedEvent(completed_message_id=uuid.uuid4()),
            {},
        )

        await app_runner.stop(0.1)

        assert handler.calls == 2
