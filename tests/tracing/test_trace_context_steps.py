from collections.abc import Iterator

import pytest

from mersal.logging import LogContext
from mersal.messages import LogicalMessage, TransportMessage
from mersal.messages.message_headers import MessageHeaders
from mersal.pipeline import IncomingStepContext
from mersal.pipeline.outgoing_step_context import OutgoingStepContext
from mersal.pipeline.send.destination_addresses import DestinationAddresses
from mersal.testing.core.counter import Counter
from mersal.tracing import (
    TraceContext,
    TraceContextIncomingStep,
    TraceContextOutgoingStep,
    current_trace_context,
    reset_current_trace_context,
    set_current_trace_context,
)
from mersal.transport import DefaultTransactionContext

__all__ = ("TestTraceContextSteps",)


pytestmark = pytest.mark.anyio

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN_ID = "00f067aa0ba902b7"


@pytest.fixture(autouse=True)
def isolated_trace_context() -> Iterator[None]:
    token = set_current_trace_context(None)
    yield
    reset_current_trace_context(token)


def _incoming_context(headers: dict[str, str]) -> IncomingStepContext:
    return IncomingStepContext(
        message=TransportMessage(body=b"hi", headers=MessageHeaders({MessageHeaders.message_id_key: "M1", **headers})),
        transaction_context=DefaultTransactionContext(),
    )


def _outgoing_context(headers: dict[str, str]) -> tuple[OutgoingStepContext, LogicalMessage]:
    message = LogicalMessage(body={}, headers=MessageHeaders({MessageHeaders.message_id_key: "M2", **headers}))
    context = OutgoingStepContext(
        message=message,
        transaction_context=DefaultTransactionContext(),
        destination_addresses=DestinationAddresses({"moon"}),
    )
    return context, message


class _TraceCapture:
    def __init__(self) -> None:
        self.trace_context: TraceContext | None = None
        self.calls = 0

    async def task(self) -> None:
        self.calls += 1
        self.trace_context = current_trace_context()


class TestTraceContextSteps:
    async def test_incoming_message_continues_the_senders_trace_in_a_new_span(self):
        capture = _TraceCapture()

        await TraceContextIncomingStep()(
            _incoming_context({MessageHeaders.traceparent_key: f"00-{TRACE_ID}-{SPAN_ID}-01"}),
            capture.task,
        )

        trace_context = capture.trace_context
        assert trace_context is not None
        assert trace_context.trace_id == TRACE_ID
        assert trace_context.span_id != SPAN_ID
        assert trace_context.sampled
        assert capture.calls == 1

    @pytest.mark.parametrize("headers", [{}, {MessageHeaders.traceparent_key: "garbage"}])
    async def test_incoming_message_without_a_valid_trace_starts_a_new_one(self, headers: dict[str, str]):
        capture = _TraceCapture()

        await TraceContextIncomingStep()(_incoming_context(headers), capture.task)

        assert capture.trace_context is not None
        assert capture.trace_context.trace_id != TRACE_ID

    async def test_incoming_message_restores_the_previous_trace_context_afterwards(self):
        previous = TraceContext.new_root()
        set_current_trace_context(previous)
        capture = _TraceCapture()

        await TraceContextIncomingStep()(
            _incoming_context({MessageHeaders.traceparent_key: f"00-{TRACE_ID}-{SPAN_ID}-00"}),
            capture.task,
        )

        assert capture.trace_context is not None
        assert capture.trace_context.trace_id == TRACE_ID
        assert current_trace_context() == previous

    async def test_incoming_message_binds_the_trace_onto_the_log_context(self):
        context = _incoming_context({MessageHeaders.traceparent_key: f"00-{TRACE_ID}-{SPAN_ID}-01"})
        log_context = LogContext()
        context.save(log_context)
        capture = _TraceCapture()

        await TraceContextIncomingStep()(context, capture.task)

        assert capture.trace_context is not None
        assert log_context.fields == {
            "trace_id": TRACE_ID,
            "span_id": capture.trace_context.span_id,
            "trace_sampled": True,
        }

    async def test_outgoing_message_carries_the_current_trace_context(self):
        trace_context = TraceContext(trace_id=TRACE_ID, span_id=SPAN_ID, sampled=True)
        set_current_trace_context(trace_context)
        context, message = _outgoing_context({})
        counter = Counter()

        await TraceContextOutgoingStep()(context, counter.task)

        assert message.headers.traceparent == trace_context.to_traceparent()
        assert counter.total == 1

    async def test_outgoing_message_keeps_an_explicitly_set_traceparent(self):
        set_current_trace_context(TraceContext.new_root())
        explicit = f"00-{TRACE_ID}-{SPAN_ID}-00"
        context, message = _outgoing_context({MessageHeaders.traceparent_key: explicit})

        await TraceContextOutgoingStep()(context, Counter().task)

        assert message.headers.traceparent == explicit

    async def test_outgoing_message_without_a_current_trace_context_has_no_traceparent(self):
        context, message = _outgoing_context({})

        await TraceContextOutgoingStep()(context, Counter().task)

        assert message.headers.traceparent is None
