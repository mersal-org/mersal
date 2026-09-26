from mersal.exceptions import MersalExceptionError
from mersal.messages import TransportMessage
from mersal.pipeline import IncomingStepContext
from mersal.pipeline.incoming_step import IncomingStep
from mersal.transport import TransactionContext, Transport
from mersal.types import AsyncAnyCallable

from .timeout_manager import TimeoutManager

__all__ = ("HandleDeferredMessagesStep",)


class HandleDeferredMessagesStep(IncomingStep):
    """Intercepts deferred messages before they're handled.

    A message carrying a `deferred_until` header is stored in the timeout manager
    (or forwarded to the external timeout manager, when configured) instead of
    being passed down the pipeline. `DueMessagesSender` sends it to its
    `deferred_recipient` once due.
    """

    def __init__(
        self,
        timeout_manager: TimeoutManager,
        transport: Transport,
        external_timeout_manager_address: str | None = None,
    ) -> None:
        self._timeout_manager = timeout_manager
        self._transport = transport
        self._external_timeout_manager_address = external_timeout_manager_address

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        message = context.load(TransportMessage)
        deferred_until = message.headers.deferred_until
        if deferred_until is None:
            await next_step()
            return

        if message.headers.deferred_recipient is None:
            raise MersalExceptionError(
                f"Received message {message.headers.message_id} with the "
                f"'{message.headers.deferred_until_key}' header but without the "
                f"'{message.headers.deferred_recipient_key}' header"
            )

        if self._external_timeout_manager_address is not None:
            transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
            await self._transport.send(self._external_timeout_manager_address, message, transaction_context)
        else:
            await self._timeout_manager.defer(deferred_until, message)
