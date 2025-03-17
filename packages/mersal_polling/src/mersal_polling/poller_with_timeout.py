import uuid

from anyio import fail_after

from mersal.exceptions import MersalExceptionError

from .poller import Poller, PollingResult

__all__ = (
    "PollerWithTimeout",
    "PollingTimeoutError",
)


class PollingTimeoutError(MersalExceptionError):
    pass


class PollerWithTimeout:
    def __init__(self, poller: Poller) -> None:
        self._poller = poller

    async def poll(self, message_id: uuid.UUID, timeout: float = 30) -> PollingResult:
        try:
            with fail_after(timeout):
                return await self._poller.poll(message_id)
        except TimeoutError as e:
            raise PollingTimeoutError() from e
