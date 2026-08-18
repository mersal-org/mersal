from functools import partial

import anyio
import pytest

from mersal.activation import BuiltinHandlerActivator
from mersal.core import run_apps
from mersal.core.app import Mersal
from mersal.testing.core.message_handlers.message_handler_that_counts import (
    MessageHandlerThatCounts,
)
from mersal.testing.core.messages import BasicMessageA, BasicMessageB
from mersal.transport.in_memory import InMemoryNetwork
from mersal.transport.in_memory.in_memory_transport_plugin import (
    InMemoryTransportPluginConfig,
)

__all__ = ("TestRunApps",)


pytestmark = pytest.mark.anyio


class StartupError(Exception):
    pass


class FlakyStartupHook:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
        self.crashed = anyio.Event()
        self.started = anyio.Event()

    async def __call__(self) -> None:
        self.calls += 1
        if self.calls <= self.failures:
            self.crashed.set()
            raise StartupError("startup failed")
        self.started.set()


def _leaf_exceptions(exc: BaseException) -> list[BaseException]:
    if isinstance(exc, BaseExceptionGroup):
        return [leaf for inner in exc.exceptions for leaf in _leaf_exceptions(inner)]
    return [exc]


def _make_app(
    name: str,
    network: InMemoryNetwork,
    handler: MessageHandlerThatCounts,
    message_type: type,
    **kwargs,
) -> Mersal:
    activator = BuiltinHandlerActivator()
    activator.register(message_type, lambda _, __: handler)
    plugins = [InMemoryTransportPluginConfig(network, f"{name}-queue").plugin]
    return Mersal(name, activator, plugins=plugins, **kwargs)


class TestRunApps:
    async def test_runs_apps_until_stop_event_is_set(self):
        network = InMemoryNetwork()
        handler1 = MessageHandlerThatCounts()
        handler2 = MessageHandlerThatCounts()
        app1 = _make_app("m1", network, handler1, BasicMessageA)
        app2 = _make_app("m2", network, handler2, BasicMessageB)
        stop = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(partial(run_apps, [app1, app2], stop=stop, handle_signals=False))
            await anyio.sleep(0.1)
            await app1.send_local(BasicMessageA())
            await app2.send_local(BasicMessageB())
            await anyio.sleep(0.5)
            stop.set()

        assert handler1.count == 1
        assert handler2.count == 1

    async def test_restarts_app_after_startup_crash(self):
        network = InMemoryNetwork()
        handler = MessageHandlerThatCounts()
        hook = FlakyStartupHook(failures=2)
        app = _make_app("m1", network, handler, BasicMessageA, on_startup_hooks=[hook])
        stop = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app],
                    stop=stop,
                    handle_signals=False,
                    restart_backoff=0.01,
                )
            )
            with anyio.fail_after(5):
                await hook.started.wait()
            await app.send_local(BasicMessageA())
            await anyio.sleep(0.5)
            stop.set()

        assert hook.calls == 3
        assert handler.count == 1

    async def test_does_not_restart_when_stopped_during_backoff(self):
        network = InMemoryNetwork()
        handler = MessageHandlerThatCounts()
        hook = FlakyStartupHook(failures=100)
        app = _make_app("m1", network, handler, BasicMessageA, on_startup_hooks=[hook])
        stop = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app],
                    stop=stop,
                    handle_signals=False,
                    restart_backoff=0.5,
                )
            )
            with anyio.fail_after(5):
                await hook.crashed.wait()
            stop.set()

        assert hook.calls == 1

    async def test_crash_propagates_when_restart_disabled(self):
        network = InMemoryNetwork()
        handler = MessageHandlerThatCounts()
        hook = FlakyStartupHook(failures=100)
        app = _make_app("m1", network, handler, BasicMessageA, on_startup_hooks=[hook])
        stop = anyio.Event()

        with pytest.raises((StartupError, BaseExceptionGroup)) as exc_info:
            await run_apps([app], stop=stop, handle_signals=False, restart_on_crash=False)

        assert any(isinstance(leaf, StartupError) for leaf in _leaf_exceptions(exc_info.value))
        assert hook.calls == 1

    async def test_crash_in_one_app_does_not_affect_others(self):
        network = InMemoryNetwork()
        handler1 = MessageHandlerThatCounts()
        handler2 = MessageHandlerThatCounts()
        hook = FlakyStartupHook(failures=100)
        app1 = _make_app("m1", network, handler1, BasicMessageA, on_startup_hooks=[hook])
        app2 = _make_app("m2", network, handler2, BasicMessageB)
        stop = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app1, app2],
                    stop=stop,
                    handle_signals=False,
                    restart_backoff=0.1,
                )
            )
            await anyio.sleep(0.1)
            await app2.send_local(BasicMessageB())
            await anyio.sleep(0.5)
            stop.set()

        assert handler2.count == 1

    async def test_liveness_watcher_reports_unresponsive_app(self):
        network = InMemoryNetwork()
        handler = MessageHandlerThatCounts()
        app = _make_app("m1", network, handler, BasicMessageA)

        async def hanging_receive(_):
            await anyio.sleep(3600)

        # Simulate a wedged worker: the receive loop blocks forever, so the
        # heartbeat stops updating.
        app.transport.receive = hanging_receive  # pyright: ignore[reportAttributeAccessIssue]
        stop = anyio.Event()
        fired = anyio.Event()
        reports = []

        async def on_unresponsive(app_: Mersal, age: float) -> None:
            reports.append((app_, age))
            fired.set()

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app],
                    stop=stop,
                    handle_signals=False,
                    liveness_timeout=0.2,
                    liveness_check_interval=0.05,
                    on_unresponsive=on_unresponsive,
                )
            )
            with anyio.fail_after(5):
                await fired.wait()
            stop.set()

        assert len(reports) == 1
        reported_app, age = reports[0]
        assert reported_app is app
        assert age > 0.2

    async def test_ready_event_set_once_all_apps_started(self):
        network = InMemoryNetwork()
        handler1 = MessageHandlerThatCounts()
        handler2 = MessageHandlerThatCounts()
        app1 = _make_app("m1", network, handler1, BasicMessageA)
        app2 = _make_app("m2", network, handler2, BasicMessageB)
        stop = anyio.Event()
        ready = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(partial(run_apps, [app1, app2], stop=stop, ready=ready, handle_signals=False))
            with anyio.fail_after(5):
                await ready.wait()
            await app1.send_local(BasicMessageA())
            await app2.send_local(BasicMessageB())
            await anyio.sleep(0.5)
            stop.set()

        assert handler1.count == 1
        assert handler2.count == 1

    async def test_ready_event_set_immediately_when_no_apps(self):
        stop = anyio.Event()
        ready = anyio.Event()

        await run_apps([], stop=stop, ready=ready, handle_signals=False)

        assert ready.is_set()

    async def test_ready_event_waits_for_slowest_app_to_start(self):
        network = InMemoryNetwork()
        handler1 = MessageHandlerThatCounts()
        handler2 = MessageHandlerThatCounts()
        hook = FlakyStartupHook(failures=2)
        app1 = _make_app("m1", network, handler1, BasicMessageA, on_startup_hooks=[hook])
        app2 = _make_app("m2", network, handler2, BasicMessageB)
        stop = anyio.Event()
        ready = anyio.Event()

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app1, app2],
                    stop=stop,
                    ready=ready,
                    handle_signals=False,
                    restart_backoff=0.2,
                )
            )
            # app2 starts immediately; app1 keeps failing startup for a
            # couple of retries, so ready must not fire until it succeeds.
            with anyio.fail_after(5):
                await hook.crashed.wait()
            assert not ready.is_set()
            with anyio.fail_after(5):
                await ready.wait()
            stop.set()

        assert hook.calls == 3

    async def test_liveness_watcher_does_not_report_idle_responsive_app(self):
        network = InMemoryNetwork()
        handler = MessageHandlerThatCounts()
        app = _make_app("m1", network, handler, BasicMessageA)
        stop = anyio.Event()
        reports = []

        async def on_unresponsive(app_: Mersal, age: float) -> None:
            reports.append((app_, age))

        async with anyio.create_task_group() as tg:
            tg.start_soon(
                partial(
                    run_apps,
                    [app],
                    stop=stop,
                    handle_signals=False,
                    liveness_timeout=2.0,
                    liveness_check_interval=0.05,
                    on_unresponsive=on_unresponsive,
                )
            )
            await anyio.sleep(0.5)
            stop.set()

        assert reports == []
