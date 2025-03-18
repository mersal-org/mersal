from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from litestar import Litestar, post
from litestar.testing import AsyncTestClient

from mersal.activation import (
    BuiltinHandlerActivator,
)
from mersal.app import Mersal
from mersal.lifespan.autosubscribe import AutosubscribeConfig
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_litestar import LitestarMersalPluginConfig
from mersal_polling import (
    DefaultPoller,
    PollingConfig,
)

if TYPE_CHECKING:
    from mersal.pipeline import MessageContext

__all__ = (
    "Message1",
    "Message1Completed",
    "MessageHandler",
    "MessageHandlerThatPublishesCompletedEvent",
    "TestLitestarPlugin",
    "ThrowingMessageHandler",
)


pytestmark = pytest.mark.anyio


@dataclass
class Message1:
    pass


@dataclass
class Message1Completed:
    message_id: Any


class MessageHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, message: Any):
        self.calls += 1


class ThrowingMessageHandler:
    async def __call__(self, message: Any):
        raise Exception()


class MessageHandlerThatPublishesCompletedEvent:
    def __init__(self, message_context: MessageContext, app) -> None:
        self.calls = 0
        self.app = app
        self.message_context = message_context

    async def __call__(self, message: Any):
        self.calls += 1
        await self.app.publish(Message1Completed(self.message_context.headers.message_id))


class TestLitestarPlugin:
    async def test_happy_path(self):
        network = InMemoryNetwork()
        subscription_store = InMemorySubscriptionStore()
        queue_address1 = "test-queue1"
        queue_address2 = "test-queue2"
        activator1 = BuiltinHandlerActivator()
        activator2 = BuiltinHandlerActivator()
        _poller = DefaultPoller()
        plugins = [
            AutosubscribeConfig(set()).plugin,
            PollingConfig(_poller).plugin,
        ]
        app1 = Mersal(
            "m1",
            activator1,
            plugins=[
                *plugins,
                InMemoryTransportPluginConfig(network, queue_address1).plugin,
            ],
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )
        app2 = Mersal(
            "m2",
            activator2,
            plugins=[
                *plugins,
                InMemoryTransportPluginConfig(network, queue_address2).plugin,
            ],
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        handler = MessageHandler()
        activator1.register(Message1, lambda __, _: handler)
        activator2.register(Message1, lambda __, _: handler)

        @post(
            path="/request1",
        )
        async def handle_request1(data: Message1, app1: Mersal) -> None:
            await app1.send_local(data)

        @post(
            path="/request2",
        )
        async def handle_request2(data: Message1, app2: Mersal) -> None:
            await app2.send_local(data)

        litestar_plugin_config = LitestarMersalPluginConfig({"app1": app1, "app2": app2})
        app = Litestar(
            route_handlers=[handle_request1, handle_request2],
            plugins=[litestar_plugin_config.plugin],
        )
        async with AsyncTestClient(app=app) as client:
            _ = await client.post("/request1", json={})
            _ = await client.post("/request2", json={})

        assert handler.calls == 2
