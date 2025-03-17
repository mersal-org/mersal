import uuid
from asyncio import sleep
from collections.abc import Callable
from dataclasses import dataclass

import pytest
from typing_extensions import Self

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.idempotency import IdempotencyConfig, MessageTracker
from mersal.persistence.in_memory.in_memory_message_tracker import (
    InMemoryMessageTracker,
)
from mersal.persistence.in_memory.in_memory_saga_storage import InMemorySagaStorage
from mersal.sagas import SagaBase, SagaConfig, SagaData
from mersal.sagas.correlator import Correlator
from mersal.sagas.saga_storage import SagaStorage
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = (
    "Message1",
    "Message2",
    "MySaga",
    "MySagaData",
    "TestSagaIntegration",
)


pytestmark = pytest.mark.anyio


@dataclass
class Message1:
    user_id: int = 100


@dataclass
class Message2:
    age: int = 20


@dataclass
class MySagaData:
    user_id: int | None = None
    age: int | None = None


class MySaga(SagaBase[MySagaData]):
    initiating_message_types = {
        Message1,
    }

    def __init__(
        self,
        message1_custom_call: Callable[[Self], None] | None = None,
        message2_custom_call: Callable[[Self], None] | None = None,
    ) -> None:
        super().__init__()
        self.data_type = SagaData
        self.message1_handling_count = 0
        self.message2_handling_count = 0
        self.new_saga_data: SagaData
        self.resolved_conflict_call_count = 0
        self.message1_custom_call = message1_custom_call
        self.message2_custom_call = message2_custom_call

    def correlate_messages(self, correlator: Correlator):
        correlator.correlate(Message1, lambda mc: mc.message.body.user_id, "user_id")

    def generate_new_data(self) -> SagaData[MySagaData]:
        self.new_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData())
        return self.new_saga_data

    async def __call__(self, message: Message1 | Message2):
        if isinstance(message, Message1):
            if self.message1_custom_call:
                self.message1_custom_call(self)
            self.message1_handling_count += 1
            self.data.data.user_id = message.user_id
        if isinstance(message, Message2):
            if self.message2_custom_call:
                self.message2_custom_call(self)
            self.message2_handling_count += 1

    async def resolve_conflict(self, fresh_data: SagaData[MySagaData]):
        self.resolved_conflict_call_count += 1


class TestSagaIntegration:
    @pytest.fixture
    def saga_storage(self) -> SagaStorage:
        return InMemorySagaStorage()

    @pytest.fixture
    def message_tracker(self) -> MessageTracker:
        return InMemoryMessageTracker()

    @pytest.fixture
    def saga_plugin_config(self, saga_storage: SagaStorage) -> SagaConfig:
        return SagaConfig(
            storage=saga_storage,
            correlation_error_handler=None,
        )

    async def test_initiating_message(self, saga_storage: SagaStorage, saga_plugin_config: SagaConfig):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        saga = MySaga()
        activator.register(Message1, lambda _, __: saga)
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            saga_plugin_config.plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.start()
        message1 = Message1(user_id=200)
        await app.send_local(message1)

        await sleep(0.1)

        assert saga.message1_handling_count == 1
        data = await saga_storage.find(MySagaData, "user_id", 200)
        assert data
        assert data.data.user_id == 200

    async def test_repeated_message_with_idempotency_plugin(
        self,
        saga_storage: SagaStorage,
        saga_plugin_config: SagaConfig,
        message_tracker: MessageTracker,
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        saga = MySaga()
        activator.register(Message1, lambda _, __: saga)
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            IdempotencyConfig(tracker=message_tracker, should_stop_invocation=True).plugin,
            saga_plugin_config.plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        await app.start()
        message1 = Message1(user_id=200)
        message1_id = uuid.uuid4()
        await app.send_local(message1, headers={"message_id": message1_id})
        await app.send_local(message1, headers={"message_id": message1_id})
        await sleep(0.1)

        assert saga.message1_handling_count == 1
