from mersal.idempotency.const import IDEMPOTENCY_CHECK_KEY
from mersal.idempotency.message_tracker import MessageTracker
from mersal.messages import LogicalMessage
from mersal.pipeline import IncomingStepContext
from mersal.pipeline.incoming_step import IncomingStep
from mersal.pipeline.receive.handler_invokers import HandlerInvokers
from mersal.transport import TransactionContext
from mersal.types.callable_types import AsyncAnyCallable, AsyncTransactionContextCallable

__all__ = ("IdempotencyCheckerStep",)


class IdempotencyCheckerStep(IncomingStep):
    def __init__(self, message_tracker: MessageTracker, stop_invocation: bool) -> None:
        self.message_tracker = message_tracker
        self.stop_invocation = stop_invocation

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
        message = context.load(LogicalMessage)
        message_id = message.headers.message_id

        if await self.message_tracker.is_message_tracked(message_id, transaction_context):
            invokers = context.load(HandlerInvokers)
            if self.stop_invocation:
                for invoker in invokers:
                    invoker.should_invoke = False
            else:
                message.headers[IDEMPOTENCY_CHECK_KEY] = True
        else:
            message.headers[IDEMPOTENCY_CHECK_KEY] = False

            async def action(_: AsyncTransactionContextCallable) -> None:
                await self.message_tracker.track_message(message_id, transaction_context)

            transaction_context.on_commit(action)

        await next_step()
