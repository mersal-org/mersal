from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.lifespan.lifespan_hooks_registration_plugin import (
    LifespanHooksRegistrationPluginConfig,
)
from mersal.logging import Logger
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
    from collections.abc import Callable

    from mersal.configuration import StandardConfigurator
    from mersal.sagas.config import SagaConfig
    from mersal.types import LifespanHook

__all__ = ("SagaPlugin",)


class SagaPlugin(Plugin):
    def __init__(self, config: SagaConfig):
        self._storage = config.storage
        self._correlation_error_handler = config.correlation_error_handler

    def __call__(self, configurator: StandardConfigurator) -> None:
        from mersal.pipeline import ActivateHandlersStep

        def decorate_pipeline(configurator: StandardConfigurator) -> Pipeline:
            correlation_error_handler = (
                self._correlation_error_handler
                if self._correlation_error_handler is not None
                else DefaultCorrelationErrorHandler(logger=configurator.get(Logger))  # type: ignore[type-abstract]
            )
            step = LoadSagaDataStep(
                saga_storage=self._storage,
                correlation_error_handler=correlation_error_handler,
            )

            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(step, PipelineInjectionPosition.AFTER, ActivateHandlersStep)
            return pipeline

        configurator.decorate(IncomingPipeline, decorate_pipeline)

        if configurator.send_only:
            # In send-only mode there's no incoming pipeline, so LoadSagaDataStep
            # is never invoked. Skip starting the saga storage - it'd just hold a
            # connection open for no benefit.
            def log_skip(configurator: StandardConfigurator) -> LifespanHook:
                async def _log() -> None:
                    configurator.get(Logger).info(  # type: ignore[type-abstract]
                        "saga.send_only.skip",
                        reason="app is send_only; saga storage is not started",
                    )

                return _log

            hooks: list[Callable[[StandardConfigurator], LifespanHook]] = [log_skip]
        else:
            hooks = [lambda _: AsyncCallable(self._storage)]

        plugin = LifespanHooksRegistrationPluginConfig(on_startup_hooks=hooks).plugin
        plugin(configurator)
