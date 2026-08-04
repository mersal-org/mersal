from mersal.types import LifespanHook

__all__ = ("DefaultLifespanHandler",)


class DefaultLifespanHandler:
    def __init__(self) -> None:
        self.on_startup_hooks: list[LifespanHook] = []
        self.on_shutdown_hooks: list[LifespanHook] = []

    def register_on_startup_hook(self, hook: LifespanHook) -> None:
        self.on_startup_hooks.append(hook)

    def register_on_shutdown_hook(self, hook: LifespanHook) -> None:
        self.on_shutdown_hooks.append(hook)
