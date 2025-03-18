import uuid
from dataclasses import dataclass
from typing import Any

import anyio
import pytest

from mersal.activation import (
    BuiltinHandlerActivator,
)
from mersal.app import Mersal
from mersal.lifespan.autosubscribe import AutosubscribeConfig
from mersal.messages import MessageCompletedEvent
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.pipeline import MessageContext
from mersal.serialization.serializers import Serializer
from mersal.transport.in_memory import InMemoryNetwork, InMemoryTransport
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_polling import (
    DefaultPoller,
    PollerWithTimeout,
    PollingConfig,
    PollingTimeoutError,
)
from mersal_polling.config import (
    FailedCompletionCorrelation,
    SuccessfulCompletionCorrelation,
)
from mersal_testing.app_runner_helper import AppRunnerHelper

__all__ = (
    "DummyMessage",
    "DummyMessageHandler",
    "Message1",
    "Message1CompletedSuccessfully",
    "Message1FailedToComplete",
    "MessageCompletedEventHandler",
    "MessageHandler",
    "MessageHandlerThatPublishes",
    "SlowHandler",
    "TestPollingPlugin",
    "ThrowingMessageHandler",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    def __init__(self):
        self.internal = []


class DummyMessageHandler:
    def __init__(self, delay: int | None = None) -> None:
        self.delay = delay
        self.call_count = 0

    async def __call__(self, message: DummyMessage):
        if self.delay is not None:
            await anyio.sleep(self.delay)
        message.internal.append(1)
        self.call_count += 1


class MessageCompletedEventHandler:
    def __init__(self) -> None:
        self.call_count = 0

    async def __call__(self, event: MessageCompletedEvent):
        self.call_count += 1
        self.event = event


class Message1:
    pass


class Message2:
    pass


@dataclass
class Message1CompletedSuccessfully:
    pass


@dataclass
class Message2CompletedSuccessfully:
    pass


@dataclass
class Message1FailedToComplete:
    pass


@dataclass
class Message2FailedToComplete:
    pass


class MessageHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, message: Any):
        self.calls += 1


class SlowHandler:
    def __init__(self, delay: int) -> None:
        self.calls = 0
        self.delay = delay

    async def __call__(self, message: Any):
        self.calls += 1
        await anyio.sleep(self.delay)


class ThrowingMessageHandler:
    async def __call__(self, message: Any):
        raise Exception()


class MessageHandlerThatPublishes:
    def __init__(self, message_context: MessageContext, app: Mersal, published_message: Any) -> None:
        self.calls = 0
        self.app = app
        self.message_context = message_context
        self.published_message = published_message

    async def __call__(self, message: Any):
        self.calls += 1
        await self.app.publish(self.published_message)


class TestPollingPlugin:
    async def test_polling(
        self,
        in_memory_transport: InMemoryTransport,
        in_memory_subscription_storage: InMemorySubscriptionStorage,
        serializer: Serializer,
    ):
        activator = BuiltinHandlerActivator()
        poller = DefaultPoller()
        app = Mersal(
            "m1",
            activator,
            transport=in_memory_transport,
            serializer=serializer,
            subscription_storage=in_memory_subscription_storage,
            autosubscribe=AutosubscribeConfig(set()),
            plugins=[PollingConfig(poller).plugin],
        )
        handler = MessageHandler()
        activator.register(Message1, lambda __, _: handler)
        message_id = uuid.uuid4()
        await app.start()

        await app.send_local(Message1(), headers={"message_id": message_id})
        # Make sure the message is processed before polling
        await anyio.sleep(0.1)
        result = await poller.poll(message_id)
        assert result
        assert not result.exception

        await app.stop()

    async def test_polling_with_custom_success_completion_event(
        self,
        in_memory_transport: InMemoryTransport,
        in_memory_subscription_storage: InMemorySubscriptionStorage,
        serializer: Serializer,
    ):
        activator = BuiltinHandlerActivator()
        poller = DefaultPoller()
        app = Mersal(
            "m1",
            activator,
            transport=in_memory_transport,
            serializer=serializer,
            subscription_storage=in_memory_subscription_storage,
            autosubscribe=AutosubscribeConfig(set()),
            plugins=[
                PollingConfig(
                    poller,
                    successful_completion_events_map={
                        Message1CompletedSuccessfully: SuccessfulCompletionCorrelation(),
                        Message2CompletedSuccessfully: SuccessfulCompletionCorrelation(),
                    },
                    exclude_from_completion_events={
                        Message1,
                        Message2,
                    },
                ).plugin
            ],
        )
        activator.register(
            Message1,
            lambda m, b: MessageHandlerThatPublishes(m, b, Message1CompletedSuccessfully()),
        )
        activator.register(
            Message2,
            lambda m, b: MessageHandlerThatPublishes(m, b, Message2CompletedSuccessfully()),
        )
        message1_id = uuid.uuid4()
        message2_id = uuid.uuid4()
        await app.start()

        await app.send_local(Message1(), headers={"message_id": message1_id})
        await app.send_local(Message2(), headers={"message_id": message2_id})
        await anyio.sleep(0.5)
        result1 = await poller.poll(message1_id)
        result2 = await poller.poll(message2_id)
        assert result1
        assert not result1.exception
        assert result2
        assert not result2.exception

        await app.stop()

    async def test_polling_with_custom_failure_completion_event(
        self,
        in_memory_transport: InMemoryTransport,
        in_memory_subscription_storage: InMemorySubscriptionStorage,
        serializer: Serializer,
    ):
        activator = BuiltinHandlerActivator()
        poller = DefaultPoller()
        app = Mersal(
            "m1",
            activator,
            transport=in_memory_transport,
            serializer=serializer,
            subscription_storage=in_memory_subscription_storage,
            autosubscribe=AutosubscribeConfig(set()),
            plugins=[
                PollingConfig(
                    poller,
                    failed_completion_events_map={
                        Message1FailedToComplete: FailedCompletionCorrelation(
                            exception_builder=lambda event: ValueError("hi")
                        ),
                        Message2FailedToComplete: FailedCompletionCorrelation(
                            exception_builder=lambda event: ValueError("hi-bye")
                        ),
                    },
                    exclude_from_completion_events={
                        Message1,
                        Message2,
                    },
                ).plugin
            ],
        )
        activator.register(
            Message1,
            lambda m, b: MessageHandlerThatPublishes(m, b, Message1FailedToComplete()),
        )
        activator.register(
            Message2,
            lambda m, b: MessageHandlerThatPublishes(m, b, Message2FailedToComplete()),
        )
        message1_id = uuid.uuid4()
        message2_id = uuid.uuid4()
        await app.start()

        await app.send_local(Message1(), headers={"message_id": message1_id})
        await app.send_local(Message2(), headers={"message_id": message2_id})
        await anyio.sleep(0.5)

        result1 = await poller.poll(message1_id)
        result2 = await poller.poll(message2_id)

        assert result1
        assert result1.exception
        assert type(result1.exception) is ValueError
        assert result2
        assert result2.exception
        assert type(result2.exception) is ValueError

        await app.stop()

    async def test_polling_with_exception(
        self,
        in_memory_transport: InMemoryTransport,
        in_memory_subscription_storage: InMemorySubscriptionStorage,
        serializer: Serializer,
    ):
        activator = BuiltinHandlerActivator()
        poller = DefaultPoller()
        app = Mersal(
            "m1",
            activator,
            transport=in_memory_transport,
            serializer=serializer,
            subscription_storage=in_memory_subscription_storage,
            autosubscribe=AutosubscribeConfig(set()),
            plugins=[PollingConfig(poller).plugin],
        )

        handler = ThrowingMessageHandler()
        activator.register(Message1, lambda __, _: handler)
        message_id = uuid.uuid4()
        await app.start()

        await app.send_local(Message1(), headers={"message_id": message_id})
        await anyio.sleep(0.1)
        result = await poller.poll(message_id)
        assert result
        assert result.exception

        await app.stop()

    async def test_polling_with_timeout(
        self,
        in_memory_transport: InMemoryTransport,
        in_memory_subscription_storage: InMemorySubscriptionStorage,
        serializer: Serializer,
    ):
        activator = BuiltinHandlerActivator()
        _poller = DefaultPoller()
        poller = PollerWithTimeout(_poller)
        app = Mersal(
            "m1",
            activator,
            transport=in_memory_transport,
            serializer=serializer,
            subscription_storage=in_memory_subscription_storage,
            autosubscribe=AutosubscribeConfig(set()),
            plugins=[PollingConfig(_poller).plugin],
        )

        handler = SlowHandler(1)
        activator.register(Message1, lambda __, _: handler)
        message_id = uuid.uuid4()
        await app.start()

        await app.send_local(Message1(), headers={"message_id": message_id})
        with pytest.raises(PollingTimeoutError):
            await poller.poll(message_id, timeout=0.5)

        await app.stop()

    # Tests copied from test_using_activator_with_auto_completion_sending.py
    # but using regular BuiltinHandlerActivator with PollingPlugin instead
    async def test_auto_completion_event_with_polling_plugin(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        message = DummyMessage()

        # Use regular BuiltinHandlerActivator instead of auto-completion one
        activator = BuiltinHandlerActivator()

        event_handler = MessageCompletedEventHandler()
        activator.register(MessageCompletedEvent, lambda _, __: event_handler)

        handler = DummyMessageHandler()
        activator.register(DummyMessage, lambda m, b: handler)

        subscription_store = InMemorySubscriptionStore()
        poller = DefaultPoller()

        # Configure the polling plugin with auto_publish_completion_events=True
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            PollingConfig(poller, auto_publish_completion_events=True).plugin,
        ]

        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        app_runner = AppRunnerHelper(app)
        await app.subscribe(MessageCompletedEvent)
        await app_runner.run()

        message_id = uuid.uuid4()
        await app.send_local(message, headers={"message_id": message_id})

        await anyio.sleep(0.1)
        await app_runner.stop()

        assert handler.call_count == 1
        assert event_handler.call_count == 1
        assert event_handler.event.completed_message_id == message_id

        # Also verify we can poll for the message
        result = await poller.poll(message_id)
        assert result
        assert not result.exception

    async def test_auto_completion_event_with_polling_plugin_multiple_handlers(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"

        # Use regular BuiltinHandlerActivator instead of auto-completion one
        activator = BuiltinHandlerActivator()
        message = DummyMessage()

        event_handler = MessageCompletedEventHandler()
        activator.register(MessageCompletedEvent, lambda _, __: event_handler)

        handler = DummyMessageHandler()
        activator.register(DummyMessage, lambda m, b: handler)
        activator.register(DummyMessage, lambda m, b: handler)

        subscription_store = InMemorySubscriptionStore()
        poller = DefaultPoller()

        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            PollingConfig(poller, auto_publish_completion_events=True).plugin,
        ]

        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        app_runner = AppRunnerHelper(app)
        await app.subscribe(MessageCompletedEvent)
        await app_runner.run()

        message_id = uuid.uuid4()
        await app.send_local(message, headers={"message_id": message_id})

        await anyio.sleep(0.1)
        await app_runner.stop()

        assert handler.call_count == 2
        assert event_handler.call_count == 1
        assert event_handler.event.completed_message_id == message_id

    async def test_auto_completion_event_with_polling_plugin_excluded(self):
        network = InMemoryNetwork()
        queue_address = "test-queue"

        # Use regular BuiltinHandlerActivator
        activator = BuiltinHandlerActivator()
        message = DummyMessage()

        event_handler = MessageCompletedEventHandler()
        activator.register(MessageCompletedEvent, lambda _, __: event_handler)

        handler = DummyMessageHandler()
        activator.register(DummyMessage, lambda m, b: handler)

        subscription_store = InMemorySubscriptionStore()
        poller = DefaultPoller()

        # Configure the polling plugin with DummyMessage excluded
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            PollingConfig(
                poller, auto_publish_completion_events=True, exclude_from_completion_events={DummyMessage}
            ).plugin,
        ]

        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
        )

        app_runner = AppRunnerHelper(app)
        await app.subscribe(MessageCompletedEvent)
        await app_runner.run()

        message_id = uuid.uuid4()
        await app.send_local(message, headers={"message_id": message_id})

        await anyio.sleep(0.1)
        await app_runner.stop()

        assert handler.call_count == 1
        # No completion event should be sent since DummyMessage is excluded
        assert event_handler.call_count == 0

        # Verify we can't poll for the message (no result)
        _poller = PollerWithTimeout(poller)
        with pytest.raises(PollingTimeoutError):
            _ = await _poller.poll(message_id, 1)
