from typing import Protocol

from mersal.types.callable_types import AsyncAnyCallable

from .outgoing_step_context import OutgoingStepContext

__all__ = ("OutgoingStep",)


class OutgoingStep(Protocol):
    async def __call__(self, context: OutgoingStepContext, next_step: AsyncAnyCallable) -> None: ...
