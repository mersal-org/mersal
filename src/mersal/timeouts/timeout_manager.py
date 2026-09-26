from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from mersal.messages import TransportMessage

__all__ = (
    "DueMessage",
    "TimeoutManager",
)


@dataclass
class DueMessage:
    """A deferred message whose due time has passed."""

    message: TransportMessage
    "The stored message, still carrying its `deferred_until`/`deferred_recipient` headers."
    mark_as_completed: Callable[[], Awaitable[None]]
    "Removes the message from the storage once it has been sent to its recipient."


class TimeoutManager(Protocol):
    """Storage for deferred messages until they are due."""

    async def __call__(self) -> None:
        """Called on app startup.

        Can be used to run any initialization required by the storage, for example
        creating the database table or making sure it already exists.
        """
        ...

    async def defer(self, due_time: datetime, message: TransportMessage) -> None:
        """Store `message` until `due_time`."""
        ...

    def get_due_messages(self) -> AbstractAsyncContextManager[Sequence[DueMessage]]:
        """Provide the messages that are due.

        Only messages marked as completed are removed, the rest are provided again
        on a later call. The context manager lets a storage hold resources (e.g. a
        database transaction/lock on the returned rows) while they're being sent.
        """
        ...
