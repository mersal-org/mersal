from typing import Any

__all__ = ("NullMessageHandler",)


class NullMessageHandler:
    """A message handler that does nothing. Used for testing."""

    async def __call__(self, message: Any) -> None:
        pass
