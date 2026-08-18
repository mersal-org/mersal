import signal
from collections.abc import Callable, Sequence
from typing import Any

import anyio

from mersal.core.app import Mersal
from mersal.utils.sync import AsyncCallable

__all__ = ("run_apps",)


async def run_apps(
    apps: Sequence[Mersal],
    *,
    stop: anyio.Event | None = None,
    ready: anyio.Event | None = None,
    handle_signals: bool = True,
    restart_on_crash: bool = True,
    restart_backoff: float = 1.0,
    liveness_timeout: float | None = None,
    liveness_check_interval: float | None = None,
    on_unresponsive: Callable[[Mersal, float], Any] | None = None,
) -> None:
    """Run multiple Mersal apps concurrently until stopped.

    Each app is started and stopped within a single owning task, satisfying
    anyio's requirement that a cancel scope is exited in the task that
    entered it. Apps run until the stop event is set, then all of them are
    drained concurrently before this function returns.

    A crash inside an app (e.g. a failing startup hook) tears down only that
    app; it is re-entered after a backoff while the others keep running.

    With a liveness timeout set, a watcher checks each running app's worker
    heartbeat, which the receive loop updates once per iteration. An app
    whose heartbeat goes stale (wedged parallelism limiter, transport stuck
    past its bounded-receive contract, handler pool deadlocked) is reported
    via an "app.unresponsive" warning log and the optional callback; an
    "app.responsive" log follows if it recovers. Both fire on the transition,
    not on every check.

    Args:
        apps: the Mersal apps to run.
        stop: event that triggers a graceful shutdown when set. Provide one
            to control shutdown externally (e.g. from tests); if omitted an
            internal event is created and shutdown is driven by signals.
        ready: event set once every app has completed its first successful
            start. Provide one to block a caller (e.g. a surrounding
            lifespan) until all apps are actually up; set immediately if
            ``apps`` is empty. Not re-set on a later restart.
        handle_signals: trap SIGTERM/SIGINT and set the stop event on the
            first signal; a second signal cancels the remaining shutdown.
            Requires running in the main thread of a platform with signal
            support (not Windows). Set to False when the surrounding
            application owns signal handling.
        restart_on_crash: re-enter an app after it exits with an exception.
            When False the first crash cancels the remaining apps and the
            exception propagates to the caller.
        restart_backoff: seconds to wait before re-entering a crashed app.
        liveness_timeout: heartbeat age in seconds beyond which an app is
            reported unresponsive; None disables the watcher. Must exceed
            the transport's receive bound plus the backoff strategy's
            longest delay, or idle apps will be falsely reported.
        liveness_check_interval: seconds between liveness checks; defaults
            to a quarter of the timeout.
        on_unresponsive: sync or async callable invoked with (app,
            heartbeat_age) when an app becomes unresponsive. Exceptions it
            raises are logged, not propagated.
    """
    stop_event = stop if stop is not None else anyio.Event()
    started = 0

    if ready is not None and not apps:
        ready.set()

    async def run_one(app: Mersal) -> None:
        nonlocal started
        first_start = True
        while True:
            try:
                async with app:
                    if first_start:
                        first_start = False
                        started += 1
                        if ready is not None and started == len(apps):
                            ready.set()
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

    async def watch_liveness(timeout: float) -> None:
        interval = liveness_check_interval if liveness_check_interval is not None else timeout / 4
        callback = AsyncCallable(on_unresponsive) if on_unresponsive is not None else None
        unresponsive: set[int] = set()
        while True:
            await anyio.sleep(interval)
            for app in apps:
                worker = app.worker
                if worker is None or not worker.running:
                    unresponsive.discard(id(app))
                    continue
                age = worker.heartbeat_age
                if age is None:
                    continue
                if age > timeout:
                    if id(app) not in unresponsive:
                        unresponsive.add(id(app))
                        app.logger.warning("app.unresponsive", app=app.name, heartbeat_age=age)
                        if callback is not None:
                            try:
                                await callback(app, age)
                            except Exception:
                                app.logger.exception("app.unresponsive.callback.error", app=app.name)
                elif id(app) in unresponsive:
                    unresponsive.discard(id(app))
                    app.logger.info("app.responsive", app=app.name, heartbeat_age=age)

    async with anyio.create_task_group() as task_group:
        if handle_signals:
            _ = task_group.start_soon(watch_signals, task_group.cancel_scope)
        if liveness_timeout is not None:
            _ = task_group.start_soon(watch_liveness, liveness_timeout)
        try:
            async with anyio.create_task_group() as apps_task_group:
                for app in apps:
                    _ = apps_task_group.start_soon(run_one, app)
        finally:
            task_group.cancel_scope.cancel()
