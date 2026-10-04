from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from mersal.pipeline.step_context import StepContext

__all__ = ("LogContext",)


class LogContext:
    """The fields describing one pipeline invocation, which anything running
    inside it - steps, handlers - can add to.

    Created by the logging plugin for every pipeline invocation and saved on
    its step context. Fields bound here end up on the invocation's canonical
    `pipeline.invoke` log line (read when the invocation finishes), and - for
    backends that support it (e.g. structlog's contextvars) - on every log line
    emitted during the rest of the invocation.

    Absent when logging isn't configured, so look it up with `current()` and
    skip binding when it returns `None`.
    """

    def __init__(
        self,
        fields: Mapping[str, Any] | None = None,
        binder: Callable[..., None] | None = None,
    ) -> None:
        self._fields: dict[str, Any] = dict(fields or {})
        self._binder = binder

    @property
    def fields(self) -> dict[str, Any]:
        return dict(self._fields)

    def bind(self, **fields: Any) -> None:
        self._fields.update(fields)
        if self._binder:
            self._binder(**fields)

    @staticmethod
    def current(context: StepContext) -> LogContext | None:
        """The log context of the invocation `context` belongs to. From a handler,
        pass `message_context.incoming_step_context`."""
        return context.load(LogContext) or None  # type: ignore[type-abstract]
