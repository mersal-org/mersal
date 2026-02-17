import pytest

from mersal.logging.null_logger import NullLogger
from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
from mersal.sagas.default_correlation_error_handler import (
    DefaultCorrelationErrorHandler,
)
from mersal.transport.default_transaction_context import DefaultTransactionContext
from mersal_testing.test_doubles import (
    LogicalMessageBuilder,
)

__all__ = ("test_default_correlation_error_handler",)


pytestmark = pytest.mark.anyio


async def test_default_correlation_error_handler():
    subject = DefaultCorrelationErrorHandler(logger=NullLogger())

    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1

    invoker = HandlerInvoker(action, (), DefaultTransactionContext())
    saga_invoker = SagaHandlerInvoker((), invoker)  # type: ignore

    await subject([], saga_invoker, LogicalMessageBuilder.build())

    await saga_invoker()
    assert call_count == 0
