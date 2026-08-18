from importlib.metadata import version

from mersal.core.run import run_apps
from mersal.logging import Logger, LoggingConfig

__all__ = ["Logger", "LoggingConfig", "run_apps"]


def __getattr__(name: str) -> str:
    if name != "__version__":
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    return version("mersal")
