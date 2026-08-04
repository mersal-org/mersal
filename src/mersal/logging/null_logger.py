from __future__ import annotations

from typing import Any

__all__ = ("NullLogger",)


class NullLogger:
    """A no-op logger that silently discards all messages."""

    def debug(self, event: str, **kwargs: Any) -> Any:
        return None

    def info(self, event: str, **kwargs: Any) -> Any:
        return None

    def warning(self, event: str, **kwargs: Any) -> Any:
        return None

    def warn(self, event: str, **kwargs: Any) -> Any:
        return None

    def error(self, event: str, **kwargs: Any) -> Any:
        return None

    def fatal(self, event: str, **kwargs: Any) -> Any:
        return None

    def exception(self, event: str, **kwargs: Any) -> Any:
        return None

    def critical(self, event: str, **kwargs: Any) -> Any:
        return None

    def set_level(self, level: int) -> None:
        return None

    def bind(self, **kwargs: Any) -> NullLogger:
        return self

    def unbind(self, *keys: str) -> NullLogger:
        return self

    def new(self, **kwargs: Any) -> NullLogger:
        return self
