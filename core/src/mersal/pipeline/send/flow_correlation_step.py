from collections.abc import Callable
from typing import Any, cast

from mersal.messages import LogicalMessage
from mersal.messages.message_headers import MessageHeaders
from mersal.messages.transport_message import TransportMessage
from mersal.pipeline.incoming_step_context import IncomingStepContext
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.transport.transaction_context import TransactionContext

__all__ = ("FlowCorrelationStep",)


class FlowCorrelationStep:
    """A send step to inject correlation headers."""

    async def __call__(self, context: OutgoingStepContext, next_step: Callable) -> None:
        logical_message: LogicalMessage = context.load(LogicalMessage)
        headers = logical_message.headers

        transaction_context = context.load(TransactionContext)  # type: ignore[type-abstract]
        incoming_step_context = cast(
            "IncomingStepContext | None",
            transaction_context.items.get(IncomingStepContext.step_context_key),
        )
        if not headers.get(MessageHeaders.correlation_id_key):
            (
                correlation_id,
                correlation_sequence,
            ) = self._get_correlation_id_and_sequence(incoming_step_context, headers)
            headers[MessageHeaders.correlation_id_key] = correlation_id
            headers[MessageHeaders.correlation_sequence_key] = correlation_sequence

        await next_step()

    def _get_correlation_id_and_sequence(
        self,
        incoming_step_context: IncomingStepContext | None,
        sent_message_headers: MessageHeaders,
    ) -> tuple[Any, int]:
        if incoming_step_context:
            incoming_message_headers = incoming_step_context.load(TransportMessage).headers
            correlation_id = (
                incoming_message_headers.correlation_id
                if incoming_message_headers.correlation_id is not None
                else incoming_message_headers.message_id
            )
            try:
                correlation_sequence = int(
                    incoming_message_headers.correlation_sequence
                    if incoming_message_headers.correlation_sequence is not None
                    else 0
                )
            except:  # noqa: E722
                correlation_sequence = 0

            return (correlation_id, correlation_sequence + 1)

        return (sent_message_headers.message_id, 0)
