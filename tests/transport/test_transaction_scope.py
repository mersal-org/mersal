# pyright: reportArgumentType=false
import pytest

from mersal.transport import AmbientContext, TransactionScope
from mersal_testing.test_doubles import TransactionContextTestDouble

__all__ = ("TestTransactionScope",)


pytestmark = pytest.mark.anyio


class TestTransactionScope:
    async def test_it_creates_new_transaction_context(self):
        context1 = TransactionContextTestDouble()
        AmbientContext().current = context1
        async with TransactionScope() as scope:
            assert AmbientContext().current is not context1
            assert scope.transaction_context is AmbientContext().current

    async def test_it_restores_ambient_transaction_context(self):
        context1 = TransactionContextTestDouble()
        AmbientContext().current = context1
        async with TransactionScope():
            pass

        assert AmbientContext().current is context1

    async def test_it_closes_scope_transaction_context(self):
        async with TransactionScope(transaction_context_factory=lambda: TransactionContextTestDouble()) as scope:
            scope_context: TransactionContextTestDouble = scope.transaction_context  # type: ignore

        assert scope_context._close_calls == 1

    async def test_it_ignores_exception_when_closing_scope_transaction_context(self):
        context = TransactionContextTestDouble()
        context.raise_exception_on_close_calls([1])
        async with TransactionScope(transaction_context_factory=lambda: context):
            pass

    async def test_it_completes_transaction_context(self):
        context = None  # type: ignore
        async with TransactionScope(transaction_context_factory=lambda: TransactionContextTestDouble()) as scope:
            context: TransactionContextTestDouble = scope.transaction_context  # type: ignore

        await scope.complete()
        assert context._set_result_commit == [True]
        assert context._set_result_ack == [True]
        assert context._completion_calls == 1
