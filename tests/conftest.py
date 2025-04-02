# pyright: reportWildcardImportFromLibrary=false
import pytest

from mersal_testing._internal.conftest import *

__all__ = (
    "pytest_addoption",
    "pytest_collection_modifyitems",
    "pytest_configure",
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
