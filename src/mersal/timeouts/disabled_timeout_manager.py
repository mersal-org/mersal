from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime

from mersal.exceptions import DeferralNotSupportedError
from mersal.messages import TransportMessage

from .timeout_manager import DueMessage, TimeoutManager

__all__ = ("DisabledTimeoutManager",)


class DisabledTimeoutManager(TimeoutManager):
    """Used when no timeout manager is configured.

    Receiving a deferred message then fails loudly instead of handling the message
    right away.
    """

    async def __call__(self) -> None: ...

    async def defer(self, due_time: datetime, message: TransportMessage) -> None:
        raise self._error()

    def get_due_messages(self) -> AbstractAsyncContextManager[Sequence[DueMessage]]:
        raise self._error()

    @staticmethod
    def _error() -> DeferralNotSupportedError:
        return DeferralNotSupportedError(
            detail=(
                "Received a deferred message but no timeout manager is configured. "
                "Configure one with `Mersal(..., timeouts=TimeoutsConfig(storage=...))`, "
                "or point senders to an app that hosts one with "
                "`TimeoutsConfig(external_timeout_manager_address=...)`."
            )
        )
