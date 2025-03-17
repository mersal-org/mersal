from mersal.configuration import StandardConfigurator
from mersal.lifespan.lifespan_hooks_registration_plugin import (
    LifespanHooksRegistrationPluginConfig,
)
from mersal.outbox.config import OutboxConfig
from mersal.outbox.outbox_forwarder import OutboxForwarder
from mersal.outbox.outbox_incoming_step import (
    OutboxIncomingStep,
)
from mersal.outbox.outbox_storage import OutboxStorage
from mersal.outbox.outbox_transport_decorator import OutboxTransportDecorator
from mersal.pipeline import (
    PipelineInjectionPosition,
    PipelineInjector,
)
from mersal.pipeline.pipeline import IncomingPipeline, Pipeline
from mersal.plugins import Plugin
from mersal.retry.default_retry_step import DefaultRetryStep
from mersal.serialization import MessageHeadersSerializer
from mersal.threading.anyio.anyio_periodic_async_task_factory import (
    AnyIOPeriodicTaskFactory,
)
from mersal.transport.transport import Transport
from mersal.utils.sync import AsyncCallable

__all__ = ("OutboxPlugin",)


class OutboxPlugin(Plugin):
    def __init__(self, config: OutboxConfig):
        self._outbox_storage = config.storage

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_transport(configurator: StandardConfigurator) -> OutboxTransportDecorator:
            transport = configurator.get(Transport)  # type: ignore[type-abstract]

            return OutboxTransportDecorator(transport=transport, outbox_storage=self._outbox_storage)

        def decorate_pipeline(configurator: StandardConfigurator) -> Pipeline:
            step = OutboxIncomingStep()

            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(step, PipelineInjectionPosition.AFTER, DefaultRetryStep)
            return pipeline

        def register_forwarder(configurator: StandardConfigurator) -> OutboxForwarder:
            return OutboxForwarder(
                AnyIOPeriodicTaskFactory(),
                configurator.get(Transport),  # type: ignore[type-abstract]
                configurator.get(OutboxStorage),  # type: ignore[type-abstract]
            )

        def register_outbox_storage(
            configurator: StandardConfigurator,
        ) -> OutboxStorage:
            headers_serializer = configurator.get(MessageHeadersSerializer)  # type: ignore[type-abstract]
            self._outbox_storage.headers_serializer = headers_serializer
            return self._outbox_storage

        configurator.register(OutboxStorage, register_outbox_storage)
        configurator.register(OutboxForwarder, register_forwarder)
        configurator.decorate(IncomingPipeline, decorate_pipeline)
        configurator.decorate(Transport, decorate_transport)

        startup_hooks = [
            lambda config: AsyncCallable(self._outbox_storage),
            lambda config: AsyncCallable(config.get(OutboxForwarder).start),
        ]
        shutdown_hooks = [
            lambda config: AsyncCallable(config.get(OutboxForwarder).stop),
        ]

        plugin = LifespanHooksRegistrationPluginConfig(
            on_startup_hooks=startup_hooks,  # type: ignore[arg-type]
            on_shutdown_hooks=shutdown_hooks,  # type: ignore[arg-type]
        ).plugin
        plugin(configurator)
