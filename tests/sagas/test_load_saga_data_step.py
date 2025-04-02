# pyright: reportOptionalMemberAccess=false
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import pytest
from typing_extensions import Self, override

from mersal.messages import LogicalMessage
from mersal.persistence.in_memory import (
    InMemorySagaStorage,
)
from mersal.pipeline import (
    IncomingStepContext,
)
from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
from mersal.sagas import CorrelationProperty, SagaBase, SagaData
from mersal.sagas.correlator import Correlator
from mersal.sagas.load_saga_data_step import LoadSagaDataStep
from mersal.transport import DefaultTransactionContext
from mersal_testing.counter import Counter, CounterWithAction
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = (
    "CorrelationTestHandlerTestDouble",
    "Message1",
    "Message2",
    "MySaga",
    "MySagaData",
    "TestLoadSagaDataStep",
)


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

    # Implement abstract property for basedpyright
    @property
    def data_type(self) -> type[MySagaData]:  # type: ignore[override]
        return MySagaData

    def __init__(
        self,
        message1_custom_call: Callable[[Self], None] | None = None,
        message2_custom_call: Callable[[Self], None] | None = None,
    ) -> None:
        super().__init__()
        self.message1_handling_count = 0
        self.message2_handling_count = 0
        self.new_saga_data: SagaData[MySagaData] | None = None  # Fix type annotation
        self.resolved_conflict_call_count = 0
        self.message1_custom_call = message1_custom_call
        self.message2_custom_call = message2_custom_call

    @override
    def correlate_messages(self, correlator: Correlator) -> None:
        correlator.correlate(Message1, lambda mc: mc.message.body.user_id, "user_id")

    @override
    def generate_new_data(self) -> SagaData[MySagaData]:
        self.new_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData())
        return self.new_saga_data

    async def __call__(self, message: Message1 | Message2):
        if isinstance(message, Message1):
            if self.message1_custom_call:
                self.message1_custom_call(self)
            self.message1_handling_count += 1
        if isinstance(message, Message2):
            if self.message2_custom_call:
                self.message2_custom_call(self)
            self.message2_handling_count += 1

    @override
    async def resolve_conflict(self, fresh_data: SagaData[MySagaData]) -> None:
        self.resolved_conflict_call_count += 1


class CorrelationTestHandlerTestDouble:
    def __init__(self) -> None:
        self.count = 0
        self.correlation_properties_calls = []
        self.saga_invokers_calls = []
        self.messages_calls = []

    async def __call__(
        self,
        correlation_properties: Sequence[CorrelationProperty],
        saga_invoker: SagaHandlerInvoker,
        message: LogicalMessage,
    ):
        self.correlation_properties_calls.append(correlation_properties)
        self.saga_invokers_calls.append(saga_invoker)
        self.messages_calls.append(message)
        self.count += 1


class TestLoadSagaDataStep:
    @pytest.fixture
    async def storage(self) -> InMemorySagaStorage:
        _storage = InMemorySagaStorage()
        # Calling the storage instance is likely async, but we're ignoring it in tests
        # pyright: ignore[reportUnusedCoroutine]
        await _storage()
        return _storage

    @pytest.fixture
    def correlation_error_handler(self) -> CorrelationTestHandlerTestDouble:
        return CorrelationTestHandlerTestDouble()

    @pytest.fixture
    def subject(
        self,
        correlation_error_handler: CorrelationTestHandlerTestDouble,
        storage: InMemorySagaStorage,
    ) -> LoadSagaDataStep:
        return LoadSagaDataStep(storage, correlation_error_handler)

    async def test_calls_next_step_normally_when_no_sagas(self, subject: LoadSagaDataStep):
        message = LogicalMessageBuilder.build()
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)
        counter = Counter()
        await subject(context, counter.task)

        assert counter.total == 1

    async def test_sets_saga_data_on_new_saga_and_initiating_message(
        self, subject: LoadSagaDataStep, storage: InMemorySagaStorage
    ):
        message = LogicalMessageBuilder.build(_bytes=Message1())
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        saga = MySaga()
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        def action():
            saga.data.data.age = 50

        counter = CounterWithAction(action)
        await subject(context, counter.task)

        assert counter.total == 1
        assert saga.new_saga_data
        assert saga.new_saga_data is saga.data

        inserted_data = storage._store.get(saga.data.id)
        assert inserted_data.data.age == 50

    async def test_new_saga_and_non_initiating_message(
        self,
        subject: LoadSagaDataStep,
        correlation_error_handler: CorrelationTestHandlerTestDouble,
    ):
        message = LogicalMessageBuilder.build(_bytes=Message2())
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        saga = MySaga()
        saga_invoker = SagaHandlerInvoker(
            saga=saga,
            invoker=HandlerInvoker(
                action=saga,
                handler=saga,
                transaction_context=transaction_context,
            ),
        )
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[saga_invoker],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)
        counter = Counter()
        await subject(context, counter.task)

        assert counter.total == 1
        assert not saga.new_saga_data
        assert not saga.data
        assert correlation_error_handler.count == 1
        assert correlation_error_handler.saga_invokers_calls[0] is saga_invoker
        assert correlation_error_handler.messages_calls[0] is message

    async def test_finds_existing_sagas(self, subject: LoadSagaDataStep, storage: InMemorySagaStorage):
        message = LogicalMessageBuilder.build(_bytes=Message1(user_id=10))
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        existing_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData(user_id=10))
        await storage.insert(
            existing_saga_data,
            correlation_properties=[],
            transaction_context=transaction_context,
        )
        saga = MySaga()
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        def action():
            saga.data.data.age = 50

        counter = CounterWithAction(action)
        await subject(context, counter.task)

        assert counter.total == 1
        assert not saga.new_saga_data
        assert existing_saga_data.id == saga.data.id

        updated_data = storage._store.get(saga.data.id)
        assert updated_data.data.age == 50

    async def test_finds_existing_sagas_with_stale_data(self, subject: LoadSagaDataStep, storage: InMemorySagaStorage):
        message = LogicalMessageBuilder.build(_bytes=Message1(user_id=10))
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        existing_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData(user_id=10))
        await storage.insert(
            existing_saga_data,
            correlation_properties=[],
            transaction_context=transaction_context,
        )
        saga = MySaga()
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        async def action():
            existing_saga_data.data.age = 49
            await storage.update(existing_saga_data, [], transaction_context)
            saga.data.data.age = 50

        counter = CounterWithAction(action)
        await subject(context, counter.task)

        assert counter.total == 1
        assert not saga.new_saga_data
        assert existing_saga_data.id == saga.data.id
        updated_data = storage._store.get(saga.data.id)
        assert updated_data.data.age == 50
        assert saga.resolved_conflict_call_count == 1

    async def test_not_inserting_newly_created_sagas_marked_as_completed(
        self, subject: LoadSagaDataStep, storage: InMemorySagaStorage
    ):
        message = LogicalMessageBuilder.build(_bytes=Message1())
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()

        def call(s):
            saga.is_completed = True

        saga = MySaga(message1_custom_call=call)
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        async def action():
            await saga(message.body)

        counter = CounterWithAction(action)
        await subject(context, counter.task)

        assert counter.total == 1

        assert not storage._store.get(saga.data.id)

    async def test_deleting_existings_sagas_marked_as_completed(
        self, subject: LoadSagaDataStep, storage: InMemorySagaStorage
    ):
        message = LogicalMessageBuilder.build(_bytes=Message1(user_id=10))
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        existing_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData(user_id=10))
        await storage.insert(
            existing_saga_data,
            correlation_properties=[],
            transaction_context=transaction_context,
        )

        def call(s):
            saga.is_completed = True

        saga = MySaga(message1_custom_call=call)
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        async def action():
            await saga(message.body)

        counter = CounterWithAction(action)
        await subject(context, counter.task)
        assert counter.total == 1

        assert not storage._store.get(saga.data.id)

    async def test_not_updating_existings_sagas_marked_as_unchanged(
        self, subject: LoadSagaDataStep, storage: InMemorySagaStorage
    ):
        message = LogicalMessageBuilder.build(_bytes=Message1(user_id=10))
        transport_message = TransportMessageBuilder.build()
        transaction_context = DefaultTransactionContext()
        existing_saga_data = SagaData(uuid.uuid4(), revision=0, data=MySagaData(user_id=10))
        await storage.insert(
            existing_saga_data,
            correlation_properties=[],
            transaction_context=transaction_context,
        )

        def call(s):
            saga.is_unchanged = True

        saga = MySaga(message1_custom_call=call)
        invokers = HandlerInvokers(
            message=message,
            handler_invokers=[
                SagaHandlerInvoker(
                    saga=saga,
                    invoker=HandlerInvoker(
                        action=saga,
                        handler=saga,
                        transaction_context=transaction_context,
                    ),
                )
            ],
        )
        context = IncomingStepContext(
            message=transport_message,
            transaction_context=transaction_context,
        )
        context.save(message)
        context.save(invokers)

        async def action():
            saga.data.data.age = 100
            await saga(message.body)

        counter = CounterWithAction(action)
        await subject(context, counter.task)
        assert counter.total == 1

        stored_data = storage._store.get(saga.data.id)
        assert stored_data
        assert stored_data.data.age != 100
