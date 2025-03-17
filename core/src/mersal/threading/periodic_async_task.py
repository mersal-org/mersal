from typing import Protocol

__all__ = ("PeriodicAsyncTask",)


class PeriodicAsyncTask(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...
