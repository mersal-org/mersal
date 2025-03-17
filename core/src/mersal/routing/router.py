from typing import Protocol

from mersal.messages import LogicalMessage

__all__ = ("Router",)


class Router(Protocol):
    async def get_destination_address(self, message: LogicalMessage) -> str: ...
