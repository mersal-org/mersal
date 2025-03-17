from collections.abc import Callable

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext, Transport

__all__ = ("TransportDecoratorHelper",)


class TransportDecoratorHelper(Transport):
    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self.address = transport.address
        self._sent: list[tuple[str, TransportMessage, TransactionContext]] = []
        self._receive: list[TransactionContext] = []
        self._before_receive_hooks: list[Callable[[TransactionContext], None]] = []

    def create_queue(self, address: str) -> None:
        self.transport.create_queue(address)

    def append_before_receive_hook(self, hook: Callable[[TransactionContext], None]) -> None:
        self._before_receive_hooks.append(hook)

    async def send(
        self,
        destination_address: str,
        message: TransportMessage,
        transaction_context: TransactionContext,
    ) -> None:
        self._sent.append((destination_address, message, transaction_context))
        await self.transport.send(destination_address, message, transaction_context)

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        self._receive.append(transaction_context)
        for hook in self._before_receive_hooks:
            hook(transaction_context)
        return await self.transport.receive(transaction_context)
