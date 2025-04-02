from typing import Any

__all__ = ("MessageHandlerThatThrows",)


class MessageHandlerThatThrows:
    """A message handler that throws. Used for testing."""

    def __init__(self, exception: Exception | None = None) -> None:
        self.exception = exception

    async def __call__(self, message: Any) -> None:
        raise (self.exception if self.exception else Exception("I raised an exception"))
