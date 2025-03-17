from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol, TypeAlias, TypeVar

from mersal.handlers import MessageHandler
from mersal.pipeline import MessageContext

# Define a type variable for messages
MessageT = TypeVar("MessageT")

# A factory function that creates message handlers
HandlerFactory: TypeAlias = Callable[
    [MessageContext, "Mersal"],
    MessageHandler[MessageT],
]

if TYPE_CHECKING:
    from mersal.app import Mersal
    from mersal.transport import TransactionContext

__all__ = ("HandlerActivator",)


class HandlerActivator(Protocol):
    """Protocol defining the interface for activating message handlers.

    The HandlerActivator is responsible for registering message handlers
    and returning the appropriate handlers for a given message type during
    message processing.
    """

    async def get_handlers(
        self,
        message: MessageT,
        transaction_context: TransactionContext,
    ) -> Sequence[MessageHandler[MessageT]]:
        """Retrieve handlers for the given message.

        Args:
            message: The message to get handlers for
            transaction_context: The current transaction context

        Returns:
            A sequence of message handlers that can process the message
        """
        ...

    def register(
        self,
        message_type: type[MessageT],
        factory: HandlerFactory[MessageT],
    ) -> HandlerActivator:
        """Register a handler factory for a specific message type.

        Args:
            message_type: The type of message to register a handler for
            factory: A factory function that creates a message handler

        Returns:
            The handler activator instance for method chaining
        """
        ...

    @property
    def registered_message_types(self) -> set[type]:
        """Get the set of message types that have registered handlers.

        Returns:
            A set containing all registered message types
        """
        ...

    @property
    def app(self) -> Mersal: ...

    @app.setter
    def app(self, value: Mersal) -> None: ...
