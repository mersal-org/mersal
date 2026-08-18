import types
from typing import Protocol

__all__ = ("Worker",)


class Worker(Protocol):
    name: str
    running: bool

    @property
    def heartbeat_age(self) -> float | None:
        """Seconds since the receive loop last made progress, or None before the first beat."""
        ...

    async def __call__(self) -> None: ...

    async def stop(self) -> None: ...

    # `Self` here breaks ty's matching against `AbstractAsyncContextManager[Worker, ...]`
    # in AsyncExitStack.enter_async_context (mersal/app.py), so this stays `Worker`.
    async def __aenter__(self) -> "Worker": ...  # noqa: PYI034

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...
