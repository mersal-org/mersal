from collections.abc import Sequence
from typing import Protocol

from mersal.outbox.outbox_message_batch import OutboxMessageBatch
from mersal.serialization import MessageHeadersSerializer
from mersal.transport import OutgoingMessage, TransactionContext

__all__ = ("OutboxStorage",)


class OutboxStorage(Protocol):
    """A protocol that any Outbox storage must implement."""

    headers_serializer: MessageHeadersSerializer

    async def save(
        self,
        outgoing_messages: Sequence[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        """Save outbox messages.

        The `TransactionContext` can be used to obtain objects related to the current
        message being handled. For example, to obtain the database transaction/session.

        Args:
            outgoing_messages: A list of messages to be stored in the outbox.
            transaction_context: The :class:`TransactionContext <.transport.TransactionContext>` for
                                the message that is currently being handled.
        """
        ...

    async def get_next_message_batch(self) -> OutboxMessageBatch:
        """Provide messages stored in the outbox."""
        ...

    async def __call__(self) -> None:
        """Called upon setting up the outbox feature.

        Can be used to run any initialization required by the storage.
        For example, creating the outbox database table or making sure
        it already exists.
        """
        ...
