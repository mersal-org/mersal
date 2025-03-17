from mersal.messages.transport_message import TransportMessage
from mersal.transport.transaction_context import TransactionContext
from mersal.transport.transport import Transport

__all__ = ("TransportBridge",)


class TransportBridge(Transport):
    """A Transport wrapper that allows sending messages to via other transports."""

    def __init__(
        self,
        default_transport: Transport,
        address_transport_mapping: dict[str, Transport],
    ) -> None:
        """Initializes TransportBridge.

        A Transport wrapper that allows sending messages to via other transports.

        Args:
            default_transport: The :class:`Transport <.transport.Transport>` to be wrapped.
            address_transport_mapping: Sets addresses to use specific transports.
        """
        self._transport = default_transport
        self._address_transport_mapping = address_transport_mapping
        self.address = self._transport.address

    def create_queue(self, address: str) -> None:
        self._transport.create_queue(address)

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        transport: Transport
        if _transport := self._address_transport_mapping.get(destination_address):
            transport = _transport
        else:
            transport = self._transport

        await transport.send(destination_address, message, transaction_context)

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        return await self._transport.receive(transaction_context)
