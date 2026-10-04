from __future__ import annotations

import re
import secrets
from contextvars import ContextVar, Token
from dataclasses import dataclass

__all__ = (
    "TraceContext",
    "current_trace_context",
    "parse_traceparent",
    "reset_current_trace_context",
    "set_current_trace_context",
)


_SAMPLED_FLAG = 0x01
_TRACEPARENT_RE = re.compile(r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})(?:-.*)?$")
_TRACEPARENT_V00_LENGTH = 55
_INVALID_TRACE_ID = "0" * 32
_INVALID_SPAN_ID = "0" * 16


def _new_trace_id() -> str:
    return secrets.token_hex(16)


def _new_span_id() -> str:
    return secrets.token_hex(8)


@dataclass(frozen=True, slots=True)
class TraceContext:
    """The ids of a W3C Trace Context (https://www.w3.org/TR/trace-context/)."""

    trace_id: str
    """32 lowercase hex chars - shared by every unit of work in the trace."""
    span_id: str
    """16 lowercase hex chars - this unit of work (e.g. one message's processing)."""
    sampled: bool = False

    @classmethod
    def new_root(cls) -> TraceContext:
        """A fresh trace, for work that arrived without one."""
        return cls(trace_id=_new_trace_id(), span_id=_new_span_id())

    def child(self) -> TraceContext:
        """Same trace, new span - e.g. a message being processed on behalf of its sender."""
        return TraceContext(trace_id=self.trace_id, span_id=_new_span_id(), sampled=self.sampled)

    def to_traceparent(self) -> str:
        flags = _SAMPLED_FLAG if self.sampled else 0
        return f"00-{self.trace_id}-{self.span_id}-{flags:02x}"


def parse_traceparent(value: str | None) -> TraceContext | None:
    """Parses a `traceparent` header value, returning `None` for anything invalid
    per the spec (callers should then start a new trace rather than fail)."""
    if not value:
        return None
    value = value.strip().lower()
    match = _TRACEPARENT_RE.match(value)
    if not match:
        return None
    version, trace_id, span_id, flags = match.groups()
    # Version ff and all-zero ids are invalid. A version-00 header must not
    # carry extra fields; higher (future) versions may.
    if version == "ff" or trace_id == _INVALID_TRACE_ID or span_id == _INVALID_SPAN_ID:
        return None
    if version == "00" and len(value) != _TRACEPARENT_V00_LENGTH:
        return None
    return TraceContext(trace_id=trace_id, span_id=span_id, sampled=bool(int(flags, 16) & _SAMPLED_FLAG))


# A plain ContextVar rather than e.g. structlog's contextvars, so propagation
# works whether or not (and however) logging is configured.
_current_trace_context: ContextVar[TraceContext | None] = ContextVar("mersal_trace_context", default=None)


def current_trace_context() -> TraceContext | None:
    return _current_trace_context.get()


def set_current_trace_context(trace_context: TraceContext | None) -> Token[TraceContext | None]:
    return _current_trace_context.set(trace_context)


def reset_current_trace_context(token: Token[TraceContext | None]) -> None:
    _current_trace_context.reset(token)
