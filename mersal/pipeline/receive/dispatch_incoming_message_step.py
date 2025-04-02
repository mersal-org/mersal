from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.incoming_step_context import IncomingStepContext
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.types import AsyncAnyCallable

__all__ = ("DispatchIncomingMessageStep",)


class DispatchIncomingMessageStep(IncomingStep):
    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        invokers: HandlerInvokers = context.load(HandlerInvokers)

        if not invokers:
            raise Exception("Message was not dispatched to any handlers")

        for invoker in invokers:
            await invoker()

        await next_step()
