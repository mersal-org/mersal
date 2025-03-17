import logging
import pdb  # noqa: T100
import sys
from copy import deepcopy
from typing import Any

from mersal.messages import TransportMessage
from mersal.pipeline import IncomingStepContext
from mersal.transport import TransactionContext
from mersal.transport.transaction_scope import TransactionScope
from mersal.types import AsyncAnyCallable

from .error_handling.error_handler import ErrorHandler
from .error_tracking.error_tracker import ErrorTracker
from .fail_fast.fail_fast_checker import FailFastChecker
from .retry_step import RetryStep

__all__ = ("DefaultRetryStep",)


class DefaultRetryStep(RetryStep):
    def __init__(
        self,
        error_tracker: ErrorTracker,
        error_handler: ErrorHandler,
        fail_fast_checker: FailFastChecker,
        pdb_on_exception: bool,
    ) -> None:
        self.logger = logging.getLogger("mersal.receive.simpleRetryStep")
        self.error_tracker = error_tracker
        self.error_handler = error_handler
        self.fail_fast_checker = fail_fast_checker
        self.pdb_on_exception = pdb_on_exception

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transport_message = context.load(TransportMessage)

        transaction_context: TransactionContext = context.load(TransactionContext)  # type: ignore[type-abstract]

        message_id: Any = transport_message.headers.message_id

        try:
            await next_step()
            transaction_context.set_result(commit=True, ack=True)
        except Exception as e:
            if self.pdb_on_exception:
                pdb.post_mortem(sys.exc_info()[2])
                return
            self.logger.exception(
                "Exception raised while handling message %r, will register and error and may retry",
                transport_message.message_label,
            )
            await self.error_tracker.register_error(message_id, e)

            if self.fail_fast_checker.should_fail_fast(message_id, e):
                self.logger.exception(
                    "Handling of message %r raised an unforgivable exception, no retries will be made.",
                    transport_message.message_label,
                )
                await self.error_tracker.mark_as_final(message_id)

            if await self.error_tracker.has_failed_too_many_times(message_id):
                self.logger.exception(
                    "Sending message %r to the deadletter queue.",
                    transport_message.message_label,
                )
                await self._handle_poisonous_message(transport_message, message_id)
                transaction_context.set_result(commit=False, ack=True)
            else:
                transaction_context.set_result(commit=False, ack=False)

    async def _handle_poisonous_message(
        self,
        transport_message: TransportMessage,
        message_id: Any,
    ) -> None:
        exceptions = await self.error_tracker.get_exceptions(message_id)
        if len(exceptions) == 1:
            exception = exceptions[0]
        elif len(exceptions) > 1:
            exception = Exception("--".join(str(e) for e in exceptions))
        else:
            exception = Exception("Message failed too many times")
        message = deepcopy(transport_message)
        await self._pass_to_deadletter_queue(message, exception)
        await self.error_tracker.clean_up(message_id)

    async def _pass_to_deadletter_queue(self, transport_message: TransportMessage, exception: Exception) -> None:
        async with TransactionScope() as scope:
            await self.error_handler.handle_poison_message(transport_message, scope.transaction_context, exception)
            await scope.complete()
