from typing import Any, Protocol

from mersal.transport import TransactionContext

__all__ = ("MessageTracker",)


class MessageTracker(Protocol):
    """Idempotency tracker."""

    async def track_message(self, message_id: Any, transaction_context: TransactionContext) -> None:
        """Set message identified by `message_id` as handled."""
        ...

    async def is_message_tracked(self, message_id: Any, transaction_context: TransactionContext) -> bool:
        """Check if message identified by `message_id` is handled."""
        ...
