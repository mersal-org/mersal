from __future__ import annotations

from typing import TYPE_CHECKING

from .default_transaction_context import DefaultTransactionContext

if TYPE_CHECKING:
    from mersal.app import Mersal

__all__ = ("DefaultTransactionContextWithOwningApp",)


class DefaultTransactionContextWithOwningApp(DefaultTransactionContext):
    def __init__(self, app: Mersal) -> None:
        super().__init__()
        self.app = app
