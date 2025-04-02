from typing import ClassVar

from mersal.pipeline import IncomingStepContext
from mersal.pipeline.incoming_step import IncomingStep
from mersal.transport import (
    TransactionContext,
)
from mersal.types import AsyncAnyCallable

__all__ = ("OutboxIncomingStep",)


class OutboxIncomingStep(IncomingStep):
    use_outbox_key: ClassVar[str] = "use-outbox"

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transaction_context: TransactionContext = context.load(TransactionContext)  # type: ignore[type-abstract]
        transaction_context.items[self.use_outbox_key] = True

        await next_step()
