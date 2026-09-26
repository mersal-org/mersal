from mersal.logging import Logger
from mersal.messages import MessageHeaders, TransportMessage
from mersal.threading.periodic_async_task_factory import PeriodicAsyncTaskFactory
from mersal.transport import TransactionScope, Transport

from .timeout_manager import TimeoutManager

__all__ = ("DueMessagesSender",)


class DueMessagesSender:
    """Periodically sends due deferred messages to their recipients."""

    def __init__(
        self,
        periodic_task_factory: PeriodicAsyncTaskFactory,
        transport: Transport,
        timeout_manager: TimeoutManager,
        logger: Logger,
        poll_interval: float = 1,
    ) -> None:
        """Initialize ``DueMessagesSender``.

        Args:
            periodic_task_factory: Creates the :class:`PeriodicAsyncTask <.threading.PeriodicAsyncTask>`
                                  that runs the periodic check & send.
            transport: The relevant :class:`Transport <.transport.Transport>`.
            timeout_manager: Storage of deferred messages.
            logger: Logger instance.
            poll_interval: Period for checking for due messages (in seconds).
        """
        self._transport = transport
        self._timeout_manager = timeout_manager
        self._logger = logger
        self._task = periodic_task_factory("Timeouts-DueMessagesSender", self.send_due_messages, poll_interval)

    async def start(self) -> None:
        await self._task.start()

    async def stop(self) -> None:
        await self._task.stop()

    async def send_due_messages(self) -> None:
        async with self._timeout_manager.get_due_messages() as due_messages:
            for due_message in due_messages:
                try:
                    await self._send(due_message.message)
                except Exception:
                    # Left in the storage; retried on the next run.
                    self._logger.exception(
                        "timeouts.due_message.send.error",
                        message_id=due_message.message.headers.message_id,
                    )
                    continue
                await due_message.mark_as_completed()

    async def _send(self, message: TransportMessage) -> None:
        headers = MessageHeaders(message.headers)
        headers.pop(MessageHeaders.deferred_until_key, None)
        recipient = headers.pop(MessageHeaders.deferred_recipient_key, None)
        if recipient is None:
            raise ValueError(f"Deferred message {headers.message_id} has no recipient")

        self._logger.debug("timeouts.due_message.send", message_id=headers.message_id, recipient=recipient)
        async with TransactionScope() as scope:
            await self._transport.send(recipient, TransportMessage(message.body, headers), scope.transaction_context)
            await scope.complete()
