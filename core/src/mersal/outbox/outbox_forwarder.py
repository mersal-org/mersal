import logging

from mersal.messages.transport_message import TransportMessage
from mersal.outbox.outbox_message_batch import OutboxMessageBatch
from mersal.outbox.outbox_storage import OutboxStorage
from mersal.threading.periodic_async_task_factory import PeriodicAsyncTaskFactory
from mersal.transport import TransactionContext, TransactionScope, Transport
from mersal.utils import AsyncRetrier

__all__ = ("OutboxForwarder",)


class OutboxForwarder:
    """Send messages stored in the outbox.

    The class checks the outbox at a fixed period, when it finds
    any outbox messages, it sends them with a retry mechanism in the case of failure
    """

    def __init__(
        self,
        periodic_task_factory: PeriodicAsyncTaskFactory,
        transport: Transport,
        outbox_storage: OutboxStorage,
        forwarding_period: float = 1,
    ) -> None:
        """Initialize ``OutboxForwader``.

        Args:
            periodic_task_factory: Creates an instance of :class:`PeriodicAsyncTask <.threading.PeriodicAsyncTask>`.
                                  The instance is responsible for running the periodic query & send.
            transport: The relevant :class:`Transport <.transport.Transport>`.
            outbox_storage: A storage for outbox messages that implements :class:`OutboxStorage <.outbox.OutboxStorage>`.
            forwarding_period: Period for rechecking the outbox storage (in seconds). Default to 1 second.
        """
        self.transport = transport
        self.outbox_storage = outbox_storage
        self.forwader = periodic_task_factory.__call__("Outbox-Forwader", self._run, forwarding_period)
        _delays = [0.1, 0.1, 0.1, 0.1, 0.1, 0.5, 0.5, 0.5, 0.5, 0.5, 1, 1, 1, 1, 1]
        self._retrier = AsyncRetrier(_delays)
        self._logger = logging.getLogger("mersal.outboxForwader")

    async def start(self) -> None:
        await self.forwader.start()

    async def stop(self) -> None:
        await self.forwader.stop()

    async def _run(self) -> None:
        # async with create_task_group() as tg:
        await self._task()

    async def _task(self) -> None:
        batch = await self.outbox_storage.get_next_message_batch()
        if not len(batch):
            self._logger.debug("Empty batch in outbox")
            await batch.close()
            return
        await self._process_batch(batch)
        await batch.complete()
        await batch.close()

    async def _process_batch(self, batch: OutboxMessageBatch) -> None:
        async with TransactionScope() as scope:
            transaction_context = scope.transaction_context
            await self._send_messages(batch, transaction_context)
            await scope.complete()

    async def _send_messages(self, batch: OutboxMessageBatch, transaction_context: TransactionContext) -> None:
        self._logger.debug("Will send %r outbox messages", len(batch))
        for message in batch:
            destination_address = message.destination_address
            transport_message = message.transport_message()

            async def action(
                destination_address: str = destination_address,
                transport_message: TransportMessage = transport_message,
            ) -> None:
                await self.transport.send(
                    destination_address=destination_address,
                    message=transport_message,
                    transaction_context=transaction_context,
                )

            await self._retrier.run(action)
        self._logger.debug("Successfully sent %r outbox messages", len(batch))
