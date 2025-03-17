from collections.abc import Sequence
from typing import TypeAlias, cast

from typing_extensions import Self

from .incoming_step import IncomingStep
from .outgoing_step import OutgoingStep
from .pipeline import IncomingPipeline, OutgoingPipeline

Step: TypeAlias = IncomingStep | OutgoingStep

__all__ = (
    "DefaultIncomingPipeline",
    "DefaultOutgoingPipeline",
    "DefaultPipeline",
)


class DefaultPipeline:
    def __init__(self) -> None:
        self._steps: list[Step] = []

    def __call__(self) -> Sequence[Step]:
        return self._steps

    def append(self, step: Step) -> Self:
        self.append_step(step)
        return self

    def append_step(self, step: Step) -> None:
        self._steps.append(step)


class DefaultIncomingPipeline(DefaultPipeline, IncomingPipeline):
    def __call__(self) -> Sequence[IncomingStep]:
        return cast("Sequence[IncomingStep]", self._steps)


class DefaultOutgoingPipeline(DefaultPipeline, OutgoingPipeline):
    def __call__(self) -> Sequence[OutgoingStep]:
        return cast("Sequence[OutgoingStep]", self._steps)
