from mersal.messages import TransportMessage
from mersal.transport import TransactionContext

from .step_context import StepContext

__all__ = ("IncomingStepContext",)


class IncomingStepContext(StepContext):
    step_context_key = "incoming_step_context"

    def __init__(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        super().__init__()
        self.save(message)
        self.save(transaction_context, TransactionContext)
        transaction_context.items[self.step_context_key] = self
