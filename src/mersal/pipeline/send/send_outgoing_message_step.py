from collections.abc import Callable

from mersal.messages import TransportMessage
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.transport import TransactionContext, Transport

__all__ = ("SendOutgoingMessageStep",)


class SendOutgoingMessageStep:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport

    async def __call__(self, context: OutgoingStepContext, next_step: Callable) -> None:
        transport_message = context.load(TransportMessage)
        destination_addresses = context.load(DestinationAddresses)

        transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
        for address in destination_addresses:
            await self._transport.send(address, transport_message, transaction_context)

        await next_step()
