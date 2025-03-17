from typing import Any, cast

from mersal.types import AsyncTransactionContextCallable

__all__ = ("TransactionContextTestDouble",)


class TransactionContextTestDouble:
    def __init__(self) -> None:
        # We need to use a more specific type for items to match base class
        # and use cast to handle the mypy typing issue
        self.items: dict[str | type, Any] = cast("dict[str | type, Any]", {})
        self._completion_calls = 0
        self._close_calls = 0
        self._set_result_commit: list[bool] = []
        self._set_result_ack: list[bool] = []
        self._close_exceptions_on_calls: list[int] = []

    def on_commit(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_rollback(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_ack(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_nack(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_close(self, action: AsyncTransactionContextCallable) -> None: ...

    def on_error(self, action: AsyncTransactionContextCallable) -> None:
        """Handle error callbacks.

        Args:
            action: The callback to execute on error
        """

    def set_result(self, commit: bool, ack: bool) -> None:
        self._set_result_commit.append(commit)
        self._set_result_ack.append(ack)

    async def complete(self) -> None:
        self._completion_calls += 1

    async def close(self) -> None:
        self._close_calls += 1
        if self._close_calls in self._close_exceptions_on_calls:
            raise Exception()

    def raise_exception_on_close_calls(self, calls: list[int]) -> None:
        self._close_exceptions_on_calls = calls
