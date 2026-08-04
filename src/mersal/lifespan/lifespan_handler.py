from collections.abc import Sequence
from typing import Protocol

from mersal.types import LifespanHook

__all__ = ("LifespanHandler",)


class LifespanHandler(Protocol):
    on_startup_hooks: Sequence[LifespanHook]
    on_shutdown_hooks: Sequence[LifespanHook]

    def register_on_startup_hook(self, hook: LifespanHook) -> None: ...

    def register_on_shutdown_hook(self, hook: LifespanHook) -> None: ...
