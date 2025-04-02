import uuid

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal.unit_of_work import UnitOfWorkConfig
from mersal.unit_of_work.plugin import UnitOfWorkPlugin
from mersal.unit_of_work.unit_of_work_step import UnitOfWorkStep
from mersal_testing.test_doubles import (
    UnitOfWorkTestHelper,
)

__all__ = (
    "DummyMessage",
    "DummyMessageHandler",
    "TestUnitOfWorkIntegration",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    def __init__(self):
        self.internal = []


class DummyMessageHandler:
    def __init__(self, delay: int | None = None, should_throw: bool = False) -> None:
        self.delay = delay
        self.should_throw = should_throw

    async def __call__(self, message: DummyMessage):
        if self.delay is not None:
            await sleep(self.delay)

        if self.should_throw:
            raise Exception()
        message.internal.append(1)


class TestUnitOfWorkIntegration:
    @pytest.fixture
    def subject(self, uow_config: UnitOfWorkConfig) -> UnitOfWorkStep:
        return UnitOfWorkStep(uow_config)

    @pytest.fixture
    def uow_helper(self) -> UnitOfWorkTestHelper:
        return UnitOfWorkTestHelper()

    @pytest.fixture
    def uow_commit_with_transaction(self) -> bool:
        return False

    @pytest.fixture
    def uow_config(self, uow_helper: UnitOfWorkTestHelper, uow_commit_with_transaction: bool) -> UnitOfWorkConfig:
        return UnitOfWorkConfig(
            uow_factory=uow_helper.uow_factory,
            commit_action=uow_helper.commit_action,
            rollback_action=uow_helper.rollback_action,
            close_action=uow_helper.close_action,
            commit_with_transaction=uow_commit_with_transaction,
        )

    @pytest.fixture
    def uow_plugin(
        self,
        uow_config: UnitOfWorkConfig,
    ) -> UnitOfWorkPlugin:
        return UnitOfWorkPlugin(uow_config)

    async def test_rollback_if_handlers_throw(self, uow_plugin: UnitOfWorkPlugin, uow_helper: UnitOfWorkTestHelper):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler(should_throw=True))
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            uow_plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)

        await app.send_local(message, {})
        async with app:
            await sleep(0)

        assert uow_helper.rollbacked == 1
        assert uow_helper.committed == 0
        assert message.internal == []

    async def test_commit(self, uow_plugin: UnitOfWorkPlugin, uow_helper: UnitOfWorkTestHelper):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler(should_throw=False))
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            uow_plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        await app.send_local(message, {})
        async with app:
            await sleep(0)

        assert uow_helper.rollbacked == 0
        assert uow_helper.committed == 1
        assert message.internal == [1]

    async def test_uow_factory_passed_correct_message_context(
        self, uow_plugin: UnitOfWorkPlugin, uow_helper: UnitOfWorkTestHelper
    ):
        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message = DummyMessage()
        activator.register(DummyMessage, lambda m, b: DummyMessageHandler(should_throw=False))
        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
            uow_plugin,
        ]
        app = Mersal("m1", activator, plugins=plugins)
        message_id = uuid.uuid4()
        await app.send_local(message, {"message_id": message_id})
        await app.start()
        await sleep(0.1)
        assert uow_helper.message_context
        assert uow_helper.message_context.headers.message_id == message_id
