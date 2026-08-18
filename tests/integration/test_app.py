import uuid

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.core.app import Mersal
from mersal.testing.core.message_handlers.message_handler_that_throws import (
    MessageHandlerThatThrows,
)
from mersal.testing.core.messages import BasicMessageA, BasicMessageB
from mersal.testing.core.test_doubles.retry.error_handler_spy import ErrorHandlerSpy
from mersal.testing.core.test_doubles.retry.error_tracker_test_double import (
    ErrorTrackerTestDouble,
)
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = ("TestAppIntegration",)


pytestmark = pytest.mark.anyio


class TestAppIntegration:
    async def test_fail_fast_exceptions(self):
        class SpecialException(Exception):
            pass

        network = InMemoryNetwork()
        queue_address = "test-queue"
        activator = BuiltinHandlerActivator()
        message1 = BasicMessageA()
        message1_id = uuid.uuid4()
        message2 = BasicMessageB()
        message2_id = uuid.uuid4()
        handler1 = MessageHandlerThatThrows(exception=SpecialException("I am failing fast"))
        handler2 = MessageHandlerThatThrows(exception=Exception("Do not fail fast"))
        error_handler = ErrorHandlerSpy()
        error_tracker = ErrorTrackerTestDouble(maximum_failure_times=5)

        activator.register(BasicMessageA, lambda _, __: handler1)
        activator.register(BasicMessageB, lambda _, __: handler2)

        plugins = [
            InMemoryTransportPluginConfig(network, queue_address).plugin,
        ]
        app = Mersal(
            "m1",
            activator,
            error_handler=error_handler,
            error_tracker=error_tracker,
            plugins=plugins,
            fail_fast_exceptions=[SpecialException],
        )
        await app.start()
        await sleep(1)
        await app.send_local(message1, headers={"message_id": message1_id})
        await app.send_local(message2, headers={"message_id": message2_id})
        await sleep(1)
        assert len(error_tracker._registered_errors_spy[str(message1_id)]) == 1
        assert len(error_tracker._registered_errors_spy[str(message2_id)]) == 5

    async def test_stop_runs_shutdown_hooks_when_worker_teardown_raises(self):
        network = InMemoryNetwork()
        activator = BuiltinHandlerActivator()
        shutdown_calls: list[bool] = []

        async def on_shutdown() -> None:
            shutdown_calls.append(True)

        plugins = [
            InMemoryTransportPluginConfig(network, "test-queue").plugin,
        ]
        app = Mersal(
            "m1",
            activator,
            plugins=plugins,
            on_shutdown_hooks=[on_shutdown],
        )
        await app.start()

        async def failing_teardown() -> None:
            raise RuntimeError("teardown failure")

        if app._exit_stack is None:
            raise AssertionError("exit stack should be set after start")
        app._exit_stack.push_async_callback(failing_teardown)

        with pytest.raises(RuntimeError, match="teardown failure"):
            await app.stop()

        assert shutdown_calls == [True]
        assert app._exit_stack is None
