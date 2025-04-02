from collections.abc import Sequence
from typing import TypeAlias

from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.outgoing_step import OutgoingStep
from mersal.types.callable_types import AsyncAnyCallable

from .incoming_step_context import IncomingStepContext
from .outgoing_step_context import OutgoingStepContext
from .pipeline import IncomingPipeline, OutgoingPipeline
from .pipeline_invoker import PipelineInvoker

Step: TypeAlias = IncomingStep | OutgoingStep

__all__ = ("IterativePipelineInvoker",)


async def _none() -> None:
    return


class IterativePipelineInvoker(PipelineInvoker):
    def __init__(self, incoming_pipeline: IncomingPipeline, outgoing_pipeline: OutgoingPipeline) -> None:
        self.incoming_steps = incoming_pipeline()
        self.outgoing_steps = outgoing_pipeline()

    async def __call__(self, context: IncomingStepContext | OutgoingStepContext) -> None:
        if isinstance(context, IncomingStepContext):
            await self._invoke_pipeline(self.incoming_steps, context)
        elif isinstance(context, OutgoingStepContext):
            await self._invoke_pipeline(self.outgoing_steps, context)

    async def _invoke_pipeline(self, steps: Sequence[Step], context: IncomingStepContext | OutgoingStepContext) -> None:
        step = _none
        for i in range(len(steps) - 1, -1, -1):
            next_step: AsyncAnyCallable = step

            async def _next(i: int = i, next_step: AsyncAnyCallable = next_step) -> None:
                step_to_invoke = steps[i]
                await step_to_invoke(context, next_step)  # type: ignore[arg-type]

            step = _next

        await step()
