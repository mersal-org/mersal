import pytest

from mersal.pipeline.receive.handler_invoker import HandlerInvoker
from mersal.pipeline.receive.saga_handler_invoker import SagaHandlerInvoker
from mersal.transport.default_transaction_context import DefaultTransactionContext

__all__ = (
    "test_stop_invocation_for_handler_invoker",
    "test_stop_invocation_for_saga_handler_invoker",
)


pytestmark = pytest.mark.anyio


async def test_stop_invocation_for_handler_invoker():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1

    subject = HandlerInvoker(action, (), DefaultTransactionContext())

    await subject()
    subject.should_invoke = False
    await subject()

    assert call_count == 1


async def test_stop_invocation_for_saga_handler_invoker():
    call_count = 0

    async def action():
        nonlocal call_count
        call_count += 1

    invoker = HandlerInvoker(action, (), DefaultTransactionContext())
    subject = SagaHandlerInvoker((), invoker)  # type: ignore

    await subject()
    subject.should_invoke = False
    await subject()

    assert call_count == 1
