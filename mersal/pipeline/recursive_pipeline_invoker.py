from collections.abc import Sequence
from typing import TypeAlias

from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.outgoing_step import OutgoingStep

from .incoming_step_context import IncomingStepContext
from .outgoing_step_context import OutgoingStepContext
from .pipeline import IncomingPipeline, OutgoingPipeline
from .pipeline_invoker import PipelineInvoker

Step: TypeAlias = IncomingStep | OutgoingStep

__all__ = ("RecursivePipelineInvoker",)


class RecursivePipelineInvoker(PipelineInvoker):
    def __init__(self, incoming_pipeline: IncomingPipeline, outgoing_pipeline: OutgoingPipeline) -> None:
        self.incoming_steps = incoming_pipeline()
        self.outgoing_steps = outgoing_pipeline()

    async def __call__(self, context: IncomingStepContext | OutgoingStepContext) -> None:
        if isinstance(context, IncomingStepContext):
            await self._invoke_pipeline(self.incoming_steps, context)
        elif isinstance(context, OutgoingStepContext):
            await self._invoke_pipeline(self.outgoing_steps, context)

    async def _invoke_pipeline(self, steps: Sequence[Step], context: IncomingStepContext | OutgoingStepContext) -> None:
        async def invoke_step(index: int = 0) -> None:
            if index == len(steps):
                return

            async def action() -> None:
                await invoke_step(index + 1)

            await steps[index](context, action)  # type: ignore[arg-type]

        await invoke_step()
