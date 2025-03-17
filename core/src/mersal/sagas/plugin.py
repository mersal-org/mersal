from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.lifespan.lifespan_hooks_registration_plugin import (
    LifespanHooksRegistrationPluginConfig,
)
from mersal.pipeline import (
    PipelineInjectionPosition,
    PipelineInjector,
)
from mersal.pipeline.pipeline import IncomingPipeline, Pipeline
from mersal.plugins import Plugin
from mersal.sagas.default_correlation_error_handler import (
    DefaultCorrelationErrorHandler,
)
from mersal.sagas.load_saga_data_step import LoadSagaDataStep
from mersal.utils.sync import AsyncCallable

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator
    from mersal.sagas.config import SagaConfig

__all__ = ("SagaPlugin",)


class SagaPlugin(Plugin):
    def __init__(self, config: SagaConfig):
        self._storage = config.storage
        self._corelation_error_handler = config.correlation_error_handler

    def __call__(self, configurator: StandardConfigurator) -> None:
        from mersal.pipeline import ActivateHandlersStep

        def decorate_pipeline(configurator: StandardConfigurator) -> Pipeline:
            correlation_error_handler = (
                self._corelation_error_handler
                if self._corelation_error_handler is not None
                else DefaultCorrelationErrorHandler()
            )
            step = LoadSagaDataStep(
                saga_storage=self._storage,
                correlation_error_handler=correlation_error_handler,
            )

            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(step, PipelineInjectionPosition.AFTER, ActivateHandlersStep)
            return pipeline

        configurator.decorate(IncomingPipeline, decorate_pipeline)

        hooks = [lambda _: AsyncCallable(self._storage)]

        plugin = LifespanHooksRegistrationPluginConfig(on_startup_hooks=hooks).plugin  # type: ignore[arg-type]
        plugin(configurator)
