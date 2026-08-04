from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from mersal.app import Mersal

    from .worker import Worker

__all__ = ("WorkerFactory",)


class WorkerFactory(Protocol):
    def create_worker(self, name: str) -> Worker: ...

    app: Mersal
