#
from typing import Any

import pytest
from anyio import sleep

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.configuration.standard_configurator import (
    InvalidConfigurationError,
    StandardConfigurator,
)
from mersal.pipeline import (
    IncomingStepContext,
    PipelineInjector,
)
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.pipeline import IncomingPipeline
from mersal.transport.in_memory.in_memory_network import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)
from mersal.types import AsyncAnyCallable

__all__ = (
    "AnotherDummyStep",
    "DummyMessage",
    "DummyMessageHandler",
    "DummyStep",
    "TestDefaultConfigurator",
)


class DummyStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable):
        pass


class AnotherDummyStep(DummyStep):
    pass


class DummyMessage:
    pass


class DummyMessageHandler:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, message: DummyMessage):
        pass


pytestmark = pytest.mark.anyio


class TestDefaultConfigurator:
    async def test_raises_error_if_transport_is_not_set(self):
        with pytest.raises(InvalidConfigurationError):
            _ = Mersal(
                "m1",
                BuiltinHandlerActivator(),
                plugins=[],
            )

    async def test_it_decorates_pipeline(self):
        class PipelineDecorator:
            def __call__(self, configurator: StandardConfigurator):
                def decorator(_) -> Any:
                    pipeline_injector = PipelineInjector(configurator.get(IncomingPipeline))
                    pipeline_injector.append_step(AnotherDummyStep())
                    return pipeline_injector

                configurator.decorate(IncomingPipeline, decorator)

        subject = Mersal(
            "m1",
            BuiltinHandlerActivator(),
            plugins=[
                InMemoryTransportPluginConfig(InMemoryNetwork(), "moon").plugin,
                PipelineDecorator(),
            ],
        )

        steps = subject.configurator._dependecy_resolver[IncomingPipeline]()
        assert steps
        assert isinstance(steps[-1], AnotherDummyStep)

    async def test_activator_injects_app_in_handler(self):
        activator = BuiltinHandlerActivator()
        subject = Mersal(
            "m1",
            activator,
            plugins=[
                InMemoryTransportPluginConfig(InMemoryNetwork(), "moon").plugin,
            ],
        )
        passed_app = None

        def handler_factory(_app):
            nonlocal passed_app
            passed_app = _app
            return DummyMessageHandler(passed_app)

        activator.register(DummyMessage, lambda message_context, app: handler_factory(app))
        await subject.send_local(DummyMessage(), {})
        await subject.start()
        await sleep(0.1)
        assert passed_app == subject
