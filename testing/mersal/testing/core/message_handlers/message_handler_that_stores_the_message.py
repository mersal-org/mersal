from typing import Any

from mersal.pipeline import MessageContext

__all__ = ("MessageHandlerThatStoresTheMessage",)


class MessageHandlerThatStoresTheMessage:
    """A message handler that counts. Used for testing."""

    def __init__(self, message_context: MessageContext) -> None:
        self.headers = message_context.headers

    async def __call__(self, message: Any) -> None:
        self.message = message
