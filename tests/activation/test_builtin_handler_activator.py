import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.pipeline import IncomingStepContext
from mersal.transport import TransactionContext
from mersal.transport.transaction_scope import TransactionScope
from mersal_testing.test_doubles import TransportMessageBuilder

__all__ = (
    "ChildDummyMessage",
    "DummyMessage",
    "DummyMessageHandler",
    "TestBuiltinHandlerActivator",
)


pytestmark = pytest.mark.anyio


class DummyMessage:
    pass


class ChildDummyMessage(DummyMessage):
    pass


class DummyMessageHandler:
    def __init__(self, order: int, calls: list[int]) -> None:
        self.count = calls
        self.calls = order

    async def __call__(self, message: DummyMessage):
        self.count.append(self.calls)


class TestBuiltinHandlerActivator:
    def set_up_dummy_incoming_step_context(self, transaction_context: TransactionContext):
        _ = IncomingStepContext(TransportMessageBuilder.build(), transaction_context)

    async def test_register(self):
        """Test that registering multiple handlers for the same message will invoke both handlers."""
        subject = BuiltinHandlerActivator()
        calls = []
        message = DummyMessage()
        subject.register(DummyMessage, lambda message_context, app: DummyMessageHandler(1, calls))
        subject.register(DummyMessage, lambda message_context, app: DummyMessageHandler(2, calls))
        async with TransactionScope() as scope:
            self.set_up_dummy_incoming_step_context(scope.transaction_context)
            handlers = await subject.get_handlers(message, scope.transaction_context)

            for handler in handlers:
                await handler(DummyMessage())

            assert calls == [1, 2]

    async def test_get_handlers_resolves_parent_handlers_for_child_message(self):
        """Test that registering a handler for a super class will invoke this handler for a child class."""
        subject = BuiltinHandlerActivator()
        calls: list[int] = []
        child_message = ChildDummyMessage()
        subject.register(DummyMessage, lambda message_context, app: DummyMessageHandler(1, calls))
        async with TransactionScope() as scope:
            self.set_up_dummy_incoming_step_context(scope.transaction_context)
            handlers = await subject.get_handlers(child_message, scope.transaction_context)

            for handler in handlers:
                await handler(child_message)

            assert calls == [1]

    async def test_get_handlers_resolves_both_child_and_parent_handlers(self):
        """Test that registering a handler for a super class will invoke this handler for a
        child class and any any other handlers registered explicitly for the child class.
        """
        subject = BuiltinHandlerActivator()
        calls: list[int] = []
        child_message = ChildDummyMessage()
        subject.register(ChildDummyMessage, lambda message_context, app: DummyMessageHandler(1, calls))
        subject.register(DummyMessage, lambda message_context, app: DummyMessageHandler(2, calls))
        async with TransactionScope() as scope:
            self.set_up_dummy_incoming_step_context(scope.transaction_context)
            handlers = await subject.get_handlers(child_message, scope.transaction_context)

            for handler in handlers:
                await handler(child_message)

            assert calls == [1, 2]
