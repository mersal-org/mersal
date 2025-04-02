from mersal.messages import LogicalMessage
from mersal.transport import TransactionContext

from .send.destination_addresses import DestinationAddresses
from .step_context import StepContext

__all__ = ("OutgoingStepContext",)


class OutgoingStepContext(StepContext):
    def __init__(
        self,
        message: LogicalMessage,
        transaction_context: TransactionContext,
        destination_addresses: DestinationAddresses,
    ) -> None:
        super().__init__()
        self.save(message)
        self.save(transaction_context, TransactionContext)
        self.save(destination_addresses)
