from collections.abc import Sequence
from typing import Protocol

from .incoming_step import IncomingStep
from .outgoing_step import OutgoingStep

__all__ = (
    "IncomingPipeline",
    "OutgoingPipeline",
    "Pipeline",
)


class Pipeline(Protocol):
    def __call__(self) -> Sequence[IncomingStep | OutgoingStep]: ...


class IncomingPipeline(Protocol):
    def __call__(self) -> Sequence[IncomingStep]: ...


class OutgoingPipeline(Protocol):
    def __call__(self) -> Sequence[OutgoingStep]: ...
