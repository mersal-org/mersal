from mersal.messages import TransportMessage
from mersal.retry import ErrorHandler
from mersal.transport import TransactionContext
from mersal_polling.poller import Poller

__all__ = ("ErrorHandlerPollerWrapper",)


class ErrorHandlerPollerWrapper(ErrorHandler):
    def __init__(self, poller: Poller, error_handler: ErrorHandler) -> None:
        self.poller = poller
        self.error_handler = error_handler

    async def handle_poison_message(
        self,
        message: TransportMessage,
        transaction_context: TransactionContext,
        exception: Exception,
    ) -> None:
        await self.error_handler.handle_poison_message(message, transaction_context, exception)
        await self.poller.push(message.headers.message_id, exception)
