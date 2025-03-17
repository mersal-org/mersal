from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, TypeVar, cast

from mersal.pipeline import MessageContext

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal._activation.handler_activator import HandlerFactory
    from mersal.app import Mersal
    from mersal.handlers import MessageHandler
    from mersal.transport import TransactionContext

# Define locally to avoid import cycle with handler_activator.py
MessageT = TypeVar("MessageT")

__all__ = ("BuiltinHandlerActivator",)


class BuiltinHandlerActivator:
    """Default implementation of the handler activator pattern.

    This class manages the registration and activation of message handlers
    based on message types. It stores handler factories indexed by message type
    and instantiates the appropriate handlers when a message needs to be processed.
    """

    def __init__(self) -> None:
        """Initialize a new instance of the BuiltinHandlerActivator."""
        self._handler_factories: dict[type, list[HandlerFactory]] = defaultdict(list)
        self._app: Mersal | None = None

    async def get_handlers(
        self,
        message: MessageT,
        transaction_context: TransactionContext,
    ) -> Sequence[MessageHandler[MessageT]]:
        """Get handlers for the specified message.

        Args:
            message: The message to get handlers for
            transaction_context: The current transaction context

        Returns:
            A sequence of message handlers that can process the message

        Raises:
            Exception: If called outside of a message context
        """
        message_context = MessageContext.current()
        if not message_context:
            raise Exception(
                "BuiltinHandlerActivator get_handlers called outside of a transaction.",
            )

        return [x(message_context, self.app) for x in self._handler_factories.get(type(message), [])]

    def register(
        self,
        message_type: type[MessageT],
        factory: HandlerFactory[MessageT],
    ) -> BuiltinHandlerActivator:
        """Register a handler factory for a specific message type.

        Args:
            message_type: The type of message to register a handler for
            factory: A factory function that creates a message handler

        Returns:
            The handler activator instance for method chaining
        """
        self._handler_factories[message_type].append(factory)
        return self

    @property
    def registered_message_types(self) -> set[type]:
        """Get the set of message types that have registered handlers.

        Returns:
            A set containing all registered message types
        """
        return set(self._handler_factories.keys())

    @property
    def app(self) -> Mersal:
        """Get the associated application instance.

        Returns:
            The Mersal application instance
        """
        return cast("Mersal", self._app)

    @app.setter
    def app(self, value: Mersal) -> None:
        """Set the associated application instance.

        Args:
            value: The Mersal application instance
        """
        self._app = value
