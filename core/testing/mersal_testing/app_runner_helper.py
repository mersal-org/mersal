from __future__ import annotations

from typing import TYPE_CHECKING

from anyio import sleep

if TYPE_CHECKING:
    from mersal.app import Mersal

__all__ = ("AppRunnerHelper",)


class AppRunnerHelper:
    def __init__(self, app: Mersal) -> None:
        self.app = app

    async def run(self) -> None:
        await self.app.start()

    async def stop(self, delay: float = 0) -> None:
        await sleep(delay)
        await self.app.stop()
