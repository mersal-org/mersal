import logging

from mersal.messages import TransportMessage
from mersal.transport import TransactionContext, Transport

__all__ = ("DeadletterQueueErrorHandler",)


class DeadletterQueueErrorHandler:
    def __init__(self, transport: Transport, error_queue_name: str) -> None:
        self.logger = logging.getLogger("mersal.receive.errorHandler")
        self.error_queue_name = error_queue_name
        self.transport = transport

    async def handle_poison_message(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
        exception: Exception,
    ) -> None:
        headers = message.headers
        headers["error_details"] = str(exception)
        try:
            await self.transport.send(self.error_queue_name, message, transaction_context)
        except Exception:
            self.logger.exception(
                "Exception while trying to send message %r to error queue",
                message.message_label,
            )
