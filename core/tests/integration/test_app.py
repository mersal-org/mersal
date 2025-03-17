import uuid

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal_testing.message_handlers.message_handler_that_throws import (
    MessageHandlerThatThrows,
)
from mersal_testing.messages import BasicMessageA, BasicMessageB
from mersal_testing.test_doubles.retry.error_handler_spy import ErrorHandlerSpy
from mersal_testing.test_doubles.retry.error_tracker_test_double import (
    ErrorTrackerTestTouble,
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
        error_tracker = ErrorTrackerTestTouble(maximum_failure_times=5)

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
        assert len(error_tracker._registered_errors_spy[message1_id]) == 1
        assert len(error_tracker._registered_errors_spy[message2_id]) == 5
