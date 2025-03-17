from dataclasses import dataclass
from typing import Any, Protocol

__all__ = (
    "Poller",
    "PollingResult",
)


@dataclass
class PollingResult:
    message_id: Any
    exception: Exception | None


class Poller(Protocol):
    async def poll(self, message_id: Any) -> PollingResult: ...

    async def push(
        self,
        message_id: Any,
        exception: Exception | None = None,
    ) -> None: ...
