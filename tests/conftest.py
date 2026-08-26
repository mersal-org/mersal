# pyright: reportWildcardImportFromLibrary=false
import gc
import os
import tracemalloc

import pytest

from mersal.testing.core._internal.conftest import *

__all__ = (
    "pytest_addoption",
    "pytest_collection_modifyitems",
    "pytest_configure",
)

# Opt-in leak detector, following
# https://pythonspeed.com/articles/identifying-resource-leaks-with-pytest/ :
# run any subset of the suite with CHECK_LEAKS=1 to fail tests whose traced
# memory usage doesn't return to (roughly) baseline afterwards. Off by
# default since it slows every test down and a positive result still needs a
# human to look at a tracemalloc snapshot to find the actual allocation site
# - this only tells you *that* something leaked, in *which test*.
_LEAK_THRESHOLD_BYTES = 10 * 1024


@pytest.fixture(autouse=True)
def _check_for_leaks():
    if not os.environ.get("CHECK_LEAKS"):
        yield
        return

    gc.collect()
    tracemalloc.start()
    try:
        before, _ = tracemalloc.get_traced_memory()
        yield
    finally:
        gc.collect()
        after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        leaked = after - before  # type: ignore
        assert leaked < _LEAK_THRESHOLD_BYTES, (
            f"test leaked {leaked} bytes of traced memory (threshold {_LEAK_THRESHOLD_BYTES}); "
            "rerun just this test under a tracemalloc snapshot diff to find the allocation site"
        )


def pytest_addoption(parser):
    """NOT WORKING"""
    """I think it is working now, can't be bothered to try it"""
    parser.addoption("--runslow", action="store_true", default=False, help="run slow tests")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: mark test as slow to run")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        # --runslow given in cli: do not skip slow tests
        return
    skip_slow = pytest.mark.skip(reason="need --runslow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)
