from contextlib import contextmanager

import pytest

from mersal.logging.standard_plugin import _LoggingIncomingStep, _LoggingPipelineInvoker
from mersal.messages import MessageHeaders, TransportMessage
from mersal.pipeline import IncomingStepContext
from mersal.pipeline.step_context import RETRY_ATTEMPTS_KEY
from mersal.transport import DefaultTransactionContext

__all__ = ("TestLoggingPipelineInvoker",)


pytestmark = pytest.mark.anyio


@contextmanager
def _noop_pipeline_context(**_):
    yield


class _LoggerSpy:
    def __init__(self, calls: list[tuple[str, str, dict]] | None = None) -> None:
        self.calls = calls if calls is not None else []
        self._bound: dict = {}

    def _record(self, level: str, event: str, kwargs: dict) -> None:
        self.calls.append((level, event, {**self._bound, **kwargs}))

    def debug(self, event: str, **kwargs) -> None:
        self._record("debug", event, kwargs)

    def info(self, event: str, **kwargs) -> None:
        self._record("info", event, kwargs)

    def warning(self, event: str, **kwargs) -> None:
        self._record("warning", event, kwargs)

    def error(self, event: str, **kwargs) -> None:
        self._record("error", event, kwargs)

    def exception(self, event: str, **kwargs) -> None:
        self._record("exception", event, kwargs)

    def warn(self, event: str, **kwargs) -> None:
        self._record("warning", event, kwargs)

    def fatal(self, event: str, **kwargs) -> None:
        self._record("fatal", event, kwargs)

    def critical(self, event: str, **kwargs) -> None:
        self._record("critical", event, kwargs)

    def set_level(self, level: int) -> None:
        return None

    def bind(self, **kwargs) -> "_LoggerSpy":
        bound = _LoggerSpy(self.calls)
        bound._bound = {**self._bound, **kwargs}
        return bound

    def unbind(self, *keys: str) -> "_LoggerSpy":
        bound = _LoggerSpy(self.calls)
        bound._bound = {k: v for k, v in self._bound.items() if k not in keys}
        return bound

    def new(self, **kwargs) -> "_LoggerSpy":
        bound = _LoggerSpy(self.calls)
        bound._bound = dict(kwargs)
        return bound


def _make_context() -> IncomingStepContext:
    message = TransportMessage(body=b"payload", headers=MessageHeaders({"message_id": "m1"}))
    return IncomingStepContext(message=message, transaction_context=DefaultTransactionContext())


class TestLoggingPipelineInvoker:
    async def test_emits_a_single_canonical_line_on_success(self):
        logger = _LoggerSpy()
        context = _make_context()

        async def invoker(context) -> None:
            return None

        subject = _LoggingPipelineInvoker(invoker, logger, _noop_pipeline_context)

        await subject(context)

        assert [level for level, _, _ in logger.calls] == ["debug", "info"]

        _, event, fields = logger.calls[1]
        assert event == "pipeline.invoke"
        assert fields["canonical"] is True
        assert fields["log_type"] == "canonical-log-line"
        assert fields["outcome"] == "success"
        assert "elapsed_ms" in fields
        assert fields["step_count"] == 0

    async def test_emits_a_single_error_level_canonical_line_on_failure(self):
        logger = _LoggerSpy()
        context = _make_context()

        async def invoker(context) -> None:
            raise ValueError("boom")

        subject = _LoggingPipelineInvoker(invoker, logger, _noop_pipeline_context)

        with pytest.raises(ValueError):
            await subject(context)

        assert [level for level, _, _ in logger.calls] == ["debug", "error"]

        _, event, fields = logger.calls[1]
        assert event == "pipeline.invoke"
        assert fields["canonical"] is True
        assert fields["outcome"] == "error"

    async def test_step_count_reflects_steps_actually_executed(self):
        logger = _LoggerSpy()
        context = _make_context()

        async def step(context, next_step) -> None:
            await next_step()

        async def final_next_step() -> None:
            return None

        decorated_first = _LoggingIncomingStep(step, logger)
        decorated_second = _LoggingIncomingStep(step, logger)

        async def run_pipeline(context) -> None:
            await decorated_first(context, lambda: decorated_second(context, final_next_step))

        subject = _LoggingPipelineInvoker(run_pipeline, logger, _noop_pipeline_context)

        await subject(context)

        _, _, fields = next(c for c in logger.calls if c[0] == "info" and c[1] == "pipeline.invoke")
        assert fields["step_count"] == 2

    async def test_retry_attempts_included_when_present(self):
        logger = _LoggerSpy()
        context = _make_context()
        context.save_keys(RETRY_ATTEMPTS_KEY, 3)

        async def invoker(context) -> None:
            return None

        subject = _LoggingPipelineInvoker(invoker, logger, _noop_pipeline_context)

        await subject(context)

        _, _, fields = next(c for c in logger.calls if c[0] == "info" and c[1] == "pipeline.invoke")
        assert fields["retry_attempts"] == 3
