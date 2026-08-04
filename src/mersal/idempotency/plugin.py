from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.idempotency.idempotency_checker_step import IdempotencyCheckerStep
from mersal.pipeline import PipelineInjectionPosition, PipelineInjector
from mersal.pipeline.pipeline import IncomingPipeline, Pipeline
from mersal.pipeline.receive.dispatch_incoming_message_step import (
    DispatchIncomingMessageStep,
)
from mersal.plugins import Plugin

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator
    from mersal.idempotency.config import IdempotencyConfig

__all__ = ("IdempotencyPlugin",)


class IdempotencyPlugin(Plugin):
    def __init__(self, config: IdempotencyConfig):
        self._config = config

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_pipeline(configurator: StandardConfigurator) -> Pipeline:
            step = IdempotencyCheckerStep(
                message_tracker=self._config.tracker,
                stop_invocation=self._config.should_stop_invocation,
            )

            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(step, PipelineInjectionPosition.BEFORE, DispatchIncomingMessageStep)
            return pipeline

        configurator.decorate(IncomingPipeline, decorate_pipeline)
