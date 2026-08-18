import signal
from collections.abc import Sequence

import anyio

from mersal.core.app import Mersal

__all__ = ("run_apps",)


async def run_apps(
    apps: Sequence[Mersal],
    *,
    stop: anyio.Event | None = None,
    handle_signals: bool = True,
    restart_on_crash: bool = True,
    restart_backoff: float = 1.0,
) -> None:
    """Run multiple Mersal apps concurrently until stopped.

    Each app is started and stopped within a single owning task, satisfying
    anyio's requirement that a cancel scope is exited in the task that
    entered it. Apps run until the stop event is set, then all of them are
    drained concurrently before this function returns.

    A crash inside an app (e.g. a failing startup hook) tears down only that
    app; it is re-entered after a backoff while the others keep running.

    Args:
        apps: the Mersal apps to run.
        stop: event that triggers a graceful shutdown when set. Provide one
            to control shutdown externally (e.g. from tests); if omitted an
            internal event is created and shutdown is driven by signals.
        handle_signals: trap SIGTERM/SIGINT and set the stop event on the
            first signal; a second signal cancels the remaining shutdown.
            Requires running in the main thread of a platform with signal
            support (not Windows). Set to False when the surrounding
            application owns signal handling.
        restart_on_crash: re-enter an app after it exits with an exception.
            When False the first crash cancels the remaining apps and the
            exception propagates to the caller.
        restart_backoff: seconds to wait before re-entering a crashed app.
    """
    stop_event = stop if stop is not None else anyio.Event()

    async def run_one(app: Mersal) -> None:
        while True:
            try:
                async with app:
                    await stop_event.wait()
                return
            except Exception:
                app.logger.exception("app.crashed", app=app.name)
                if not restart_on_crash:
                    raise
                await anyio.sleep(restart_backoff)
                if stop_event.is_set():
                    return

    async def watch_signals(scope: anyio.CancelScope) -> None:
        with anyio.open_signal_receiver(signal.SIGTERM, signal.SIGINT) as signals:
            async for _ in signals:
                if stop_event.is_set():
                    scope.cancel()
                else:
                    stop_event.set()

    async with anyio.create_task_group() as task_group:
        if handle_signals:
            _ = task_group.start_soon(watch_signals, task_group.cancel_scope)
        try:
            async with anyio.create_task_group() as apps_task_group:
                for app in apps:
                    _ = apps_task_group.start_soon(run_one, app)
        finally:
            task_group.cancel_scope.cancel()
