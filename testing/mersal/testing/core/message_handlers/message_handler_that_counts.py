from typing import Any

__all__ = ("MessageHandlerThatCounts",)


class MessageHandlerThatCounts:
    """A message handler that counts. Used for testing."""

    def __init__(self) -> None:
        self.count = 0

    async def __call__(self, message: Any) -> None:
        self.count += 1
        self.message = message
