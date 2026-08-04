from typing import Protocol

from .incoming_step_context import IncomingStepContext
from .outgoing_step_context import OutgoingStepContext

__all__ = ("PipelineInvoker",)


class PipelineInvoker(Protocol):
    async def __call__(self, context: IncomingStepContext | OutgoingStepContext) -> None: ...
