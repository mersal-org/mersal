import uuid

from mersal.idempotency import MessageTracker
from mersal.transport import TransactionContext

__all__ = ("InMemoryMessageTracker",)


class InMemoryMessageTracker(MessageTracker):
    """Tracks handled messages in memory."""

    def __init__(self) -> None:
        self._tracked_messages: set[uuid.UUID] = set()

    async def track_message(self, message_id: uuid.UUID, transaction_context: TransactionContext) -> None:
        self._tracked_messages.add(message_id)

    async def is_message_tracked(self, message_id: uuid.UUID, transaction_context: TransactionContext) -> bool:
        return message_id in self._tracked_messages
