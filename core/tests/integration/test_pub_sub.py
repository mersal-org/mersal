from asyncio import sleep

import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.test_doubles import DummyMessage, LogicalMessageBuilder

__all__ = (
    "DummyMessageHandler",
    "DummyMessageHandlerWithPublishing",
    "PublishedMessage",
    "TestPubSubIntegration",
)


pytestmark = pytest.mark.anyio


class PublishedMessage:
    pass


class DummyMessageHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, message: DummyMessage):
        self.calls += 1


class DummyMessageHandlerWithPublishing:
    def __init__(self, app) -> None:
        self.app = app
        self.published_message: PublishedMessage

    async def __call__(self, message: DummyMessage):
        self.published_message = PublishedMessage()
        await self.app.publish(self.published_message)


class TestPubSubIntegration:
    async def test_pub_sub_raises_exception_with_default_config(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        message = LogicalMessageBuilder.build()

        with pytest.raises(NotImplementedError):
            await app.publish(message, {})

    async def test_pub_sub_with_decentralized_storage(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.decentralized(),
        )
        with pytest.raises(NotImplementedError):
            await app.subscribe(DummyMessage)

    async def test_pub_sub_happy_path(self):
        network = InMemoryNetwork()
        subscription_store = InMemorySubscriptionStore()
        queue_address = "test-queue"
        queue_address2 = "test-queue2"
        activator = BuiltinHandlerActivator()
        activator.register(DummyMessage, lambda _, __: DummyMessageHandler())
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
        app2 = Mersal(
            "m2",
            activator,
            plugins=plugins2,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )
        message = LogicalMessageBuilder.build(use_dummy_message=True)

        await app2.subscribe(DummyMessage)
        await app.publish(message.body, {})

        received_message_queue1 = network.get_next(queue_address)
        assert not received_message_queue1

        received_message_queue2 = network.get_next(queue_address2)
        assert received_message_queue2

    async def test_pub_sub_integrated_happy_path(self):
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
        await app.start()
        plugins2 = [
            InMemoryTransportPluginConfig(network, queue_address2).plugin,
        ]
        activator2 = BuiltinHandlerActivator()

        app2 = Mersal(
            "m2",
            activator2,
            plugins=plugins2,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )
        message = LogicalMessageBuilder.build(use_dummy_message=True)

        handler = DummyMessageHandler()
        activator2.register(DummyMessage, lambda _, __: handler)
        await app2.subscribe(DummyMessage)
        await app.publish(message.body, {})

        await app2.start()
        await sleep(1)

        assert handler.calls == 1

    async def test_pub_sub_with_handler_publishing_message(self):
        network = InMemoryNetwork()
        subscription_store = InMemorySubscriptionStore()
        queue_address = "test-queue"
        queue_address2 = "test-queue2"
        activator = BuiltinHandlerActivator()
        handler: DummyMessageHandlerWithPublishing | None = None

        def handler_factory(app):
            nonlocal handler
            handler = DummyMessageHandlerWithPublishing(app)
            return handler

        activator.register(DummyMessage, lambda _, b: handler_factory(b))
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
        _message: PublishedMessage | None = None
        published_message_handler_call_count = 0

        async def published_message_handler(message):
            nonlocal _message
            nonlocal published_message_handler_call_count
            _message = message
            published_message_handler_call_count += 1

        activator2 = BuiltinHandlerActivator()
        activator2.register(PublishedMessage, lambda _, __: published_message_handler)

        app2 = Mersal(
            "m2",
            activator2,
            plugins=plugins2,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        await app2.subscribe(PublishedMessage)
        await app.send_local(DummyMessage(), {})
        async with app:
            await sleep(0)
        async with app2:
            await sleep(0)

        assert handler
        assert handler.published_message is _message
        assert published_message_handler_call_count == 1
