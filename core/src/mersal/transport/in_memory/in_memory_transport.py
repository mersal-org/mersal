from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mersal.transport.base_transport import BaseTransport

if TYPE_CHECKING:
    from mersal.messages import TransportMessage
    from mersal.transport import TransactionContext
    from mersal.transport.outgoing_message import OutgoingMessage

    from .in_memory_network import InMemoryNetwork

__all__ = (
    "InMemoryTransport",
    "InMemoryTransportConfig",
)


@dataclass
class InMemoryTransportConfig:
    network: InMemoryNetwork
    input_queue_address: str

    @property
    def transport(self) -> InMemoryTransport:
        return InMemoryTransport(self)


class InMemoryTransport(BaseTransport):
    def __init__(self, config: InMemoryTransportConfig) -> None:
        super().__init__(address=config.input_queue_address)
        self._network = config.network
        self._input_queue_address = config.input_queue_address
        self.create_queue(config.input_queue_address)

    def create_queue(self, address: str) -> None:
        self._network.create_queue(address)

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        next_message = self._network.get_next(self._input_queue_address)

        if not next_message:
            return None

        async def action(_: TransactionContext) -> None:
            self._network.deliver(self._input_queue_address, next_message)

        transaction_context.on_nack(action)

        return next_message

    async def send_outgoing_messages(
        self,
        outgoing_message: list[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        for message in outgoing_message:
            self._network.deliver(message.destination_address, message.transport_message)
