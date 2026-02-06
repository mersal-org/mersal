from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mersal.idempotency import MessageTracker

if TYPE_CHECKING:
    from mersal.transport import TransactionContext

__all__ = ("FileSystemMessageTracker",)


class FileSystemMessageTracker(MessageTracker):
    def __init__(self, base_directory: str | Path) -> None:
        self._base_directory = Path(base_directory) / "tracked_messages"
        self._base_directory.mkdir(parents=True, exist_ok=True)

    async def track_message(self, message_id: Any, transaction_context: TransactionContext) -> None:
        marker = self._base_directory / str(message_id)
        marker.touch()

    async def is_message_tracked(self, message_id: Any, transaction_context: TransactionContext) -> bool:
        marker = self._base_directory / str(message_id)
        return marker.exists()
