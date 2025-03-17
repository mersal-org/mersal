from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.pipeline import (
    DeserializeIncomingMessageStep,
    PipelineInjectionPosition,
    PipelineInjector,
)
from mersal.pipeline.pipeline import IncomingPipeline, Pipeline
from mersal.plugins import Plugin
from mersal.unit_of_work.unit_of_work_step import UnitOfWorkStep

if TYPE_CHECKING:
    from mersal.configuration import StandardConfigurator
    from mersal.unit_of_work.config import (
        UnitOfWorkConfig,
    )

__all__ = ("UnitOfWorkPlugin",)


class UnitOfWorkPlugin(Plugin):
    def __init__(
        self,
        config: UnitOfWorkConfig,
    ) -> None:
        self._config = config

    def __call__(self, configurator: StandardConfigurator) -> None:
        def decorate_pipeline(configurator: StandardConfigurator) -> Pipeline:
            step = UnitOfWorkStep(self._config)
            pipeline = PipelineInjector(configurator.get(IncomingPipeline))  # type: ignore[type-abstract]
            pipeline.inject_step(step, PipelineInjectionPosition.AFTER, DeserializeIncomingMessageStep)
            return pipeline

        configurator.decorate(IncomingPipeline, decorate_pipeline)
