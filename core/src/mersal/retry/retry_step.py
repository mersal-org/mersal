from typing import Protocol

from mersal.pipeline.incoming_step import IncomingStep

__all__ = ("RetryStep",)


class RetryStep(IncomingStep, Protocol): ...
