from __future__ import annotations

from typing import TYPE_CHECKING

from mersal.logging.log_context import LogContext
from mersal.messages import LogicalMessage, TransportMessage
from mersal.tracing.trace_context import (
    TraceContext,
    current_trace_context,
    parse_traceparent,
    reset_current_trace_context,
    set_current_trace_context,
)

if TYPE_CHECKING:
    from mersal.pipeline import IncomingStepContext, OutgoingStepContext
    from mersal.types import AsyncAnyCallable

__all__ = (
    "TraceContextIncomingStep",
    "TraceContextOutgoingStep",
)


class TraceContextIncomingStep:
    """Makes the received message's trace the current trace context."""

    async def __call__(self, context: IncomingStepContext, next_step: AsyncAnyCallable) -> None:
        transport_message = context.load(TransportMessage)
        parent = parse_traceparent(transport_message.headers.traceparent)
        # Processing this message is a new span within the sender's trace; a
        # message sent without one starts its own.
        trace_context = parent.child() if parent else TraceContext.new_root()

        # The canonical `pipeline.invoke` line is emitted around the whole
        # pipeline, after this step has returned and reset the trace context -
        # it gets the ids from the log context instead.
        if log_context := LogContext.current(context):
            log_context.bind(
                trace_id=trace_context.trace_id,
                span_id=trace_context.span_id,
                trace_sampled=trace_context.sampled,
            )

        token = set_current_trace_context(trace_context)
        try:
            await next_step()
        finally:
            reset_current_trace_context(token)


class TraceContextOutgoingStep:
    """Stamps the current trace context onto an outgoing message as `traceparent`,
    unless the sender already set one explicitly."""

    async def __call__(self, context: OutgoingStepContext, next_step: AsyncAnyCallable) -> None:
        headers = context.load(LogicalMessage).headers
        if not headers.traceparent and (trace_context := current_trace_context()):
            headers[headers.traceparent_key] = trace_context.to_traceparent()
        await next_step()
