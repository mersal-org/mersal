from typing import Any

import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.messages import LogicalMessage
from mersal.pipeline import ActivateHandlersStep, IncomingStepContext
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.transport import (
    TransactionScope,
)
from mersal_testing.counter import Counter
from mersal_testing.test_doubles import (
    AnotherDummyMessage,
    DummyMessage,
    LogicalMessageBuilder,
    TransportMessageBuilder,
)

pytestmark = pytest.mark.anyio


__all__ = (
    "HandlerFactoryTestHelper",
    "TestActivateHandlersStep",
)


class HandlerFactoryTestHelper:
    def __init__(self) -> None:
        self.count = 0
        self.message: Any | None = None

    def make_factory(self):
        def _factory(message_context, app):
            async def handler(message):
                self.count += 1
                self.message = message

            return handler

        return _factory


class TestActivateHandlersStep:
    async def test_creates_invokers_based_on_defined_handlers(self):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            activator = BuiltinHandlerActivator()
            message = LogicalMessageBuilder.build(use_dummy_message=True)
            transport_message = TransportMessageBuilder.build()

            testing_handler_factory1 = HandlerFactoryTestHelper()
            testing_handler_factory2 = HandlerFactoryTestHelper()
            activator.register(
                DummyMessage,
                testing_handler_factory1.make_factory(),
            )
            activator.register(
                AnotherDummyMessage,
                testing_handler_factory2.make_factory(),
            )

            subject = ActivateHandlersStep(activator)
            context = IncomingStepContext(
                message=transport_message,
                transaction_context=transaction_context,
            )

            context.save(message, LogicalMessage)
            counter = Counter()
            await subject(context, counter.task)

            invokers: HandlerInvokers = context.load(HandlerInvokers)
            for i in invokers:
                await i()

            assert testing_handler_factory1.count == 1
            assert isinstance(testing_handler_factory1.message, DummyMessage)
            assert testing_handler_factory2.count == 0

            assert counter.total == 1

    async def test_creates_invokers_for_a_batch_message(self):
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            activator = BuiltinHandlerActivator()
            message = LogicalMessageBuilder.build_batch_message([DummyMessage(), AnotherDummyMessage()])
            transport_message = TransportMessageBuilder.build()

            testing_handler_factory1 = HandlerFactoryTestHelper()
            testing_handler_factory2 = HandlerFactoryTestHelper()
            activator.register(
                DummyMessage,
                testing_handler_factory1.make_factory(),
            )
            activator.register(
                AnotherDummyMessage,
                testing_handler_factory2.make_factory(),
            )

            subject = ActivateHandlersStep(activator)
            context = IncomingStepContext(
                message=transport_message,
                transaction_context=transaction_context,
            )

            context.save(message, LogicalMessage)
            counter = Counter()
            await subject(context, counter.task)

            invokers: HandlerInvokers = context.load(HandlerInvokers)
            for i in invokers:
                await i()

            assert testing_handler_factory1.count == 1
            assert isinstance(testing_handler_factory1.message, DummyMessage)
            assert isinstance(testing_handler_factory2.message, AnotherDummyMessage)
            assert testing_handler_factory2.count == 1
            assert counter.total == 1
