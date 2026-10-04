from mersal.tracing import TraceContext, parse_traceparent

__all__ = ("TestTraceContext",)


TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN_ID = "00f067aa0ba902b7"


class TestTraceContext:
    def test_parse_traceparent(self):
        assert parse_traceparent(f"00-{TRACE_ID}-{SPAN_ID}-01") == TraceContext(
            trace_id=TRACE_ID, span_id=SPAN_ID, sampled=True
        )

    def test_parse_traceparent_is_case_insensitive(self):
        assert parse_traceparent(f"00-{TRACE_ID.upper()}-{SPAN_ID}-00") == TraceContext(
            trace_id=TRACE_ID, span_id=SPAN_ID, sampled=False
        )

    def test_parse_traceparent_rejects_invalid_values(self):
        assert parse_traceparent(None) is None
        assert parse_traceparent("") is None
        assert parse_traceparent("garbage") is None
        assert parse_traceparent(f"ff-{TRACE_ID}-{SPAN_ID}-01") is None
        assert parse_traceparent(f"00-{'0' * 32}-{SPAN_ID}-01") is None
        assert parse_traceparent(f"00-{TRACE_ID}-{'0' * 16}-01") is None
        assert parse_traceparent(f"00-{TRACE_ID}-{SPAN_ID}-01-extra") is None

    def test_parse_traceparent_accepts_extra_fields_from_future_versions(self):
        assert parse_traceparent(f"01-{TRACE_ID}-{SPAN_ID}-01-extra") == TraceContext(
            trace_id=TRACE_ID, span_id=SPAN_ID, sampled=True
        )

    def test_traceparent_round_trip(self):
        trace_context = TraceContext.new_root()

        assert parse_traceparent(trace_context.to_traceparent()) == trace_context

    def test_child_keeps_the_trace_with_a_new_span(self):
        parent = TraceContext(trace_id=TRACE_ID, span_id=SPAN_ID, sampled=True)

        child = parent.child()

        assert child.trace_id == TRACE_ID
        assert child.span_id != SPAN_ID
        assert child.sampled
