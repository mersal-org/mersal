import types
from typing import Protocol

from typing_extensions import Self

__all__ = ("Worker",)


class Worker(Protocol):
    name: str
    running: bool

    async def __call__(self) -> None: ...

    async def stop(self) -> None: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None: ...
