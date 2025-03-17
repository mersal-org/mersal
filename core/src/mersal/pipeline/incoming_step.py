from typing import Protocol

from mersal.types.callable_types import AsyncAnyCallable

from .incoming_step_context import IncomingStepContext

__all__ = ("IncomingStep",)


class IncomingStep(Protocol):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None: ...
