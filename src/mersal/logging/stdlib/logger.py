from __future__ import annotations

import logging
from typing import Any

__all__ = ("StdlibLogger",)


class StdlibLogger:
    """A :class:`Logger` implementation that wraps :class:`logging.Logger`.

    Structured context from ``bind()`` / ``new()`` is prepended to every log
    message as a ``[key=value ...]`` prefix.
    """

    def __init__(
        self,
        name: str = "mersal",
        _context: dict[str, Any] | None = None,
    ) -> None:
        self._logger = logging.getLogger(name)
        self._context: dict[str, Any] = _context or {}

    _LOGGING_KWARGS = frozenset({"exc_info", "stack_info", "stacklevel"})

    def _format(self, event: str, extra: dict[str, Any]) -> str:
        merged = {**self._context, **extra}
        if merged:
            value_strings = [f"{k}={v}" for k, v in merged.items()]
            return f"{event}: {', '.join(value_strings)}"
        return event

    def _split_kwargs(self, kwargs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        logging_kwargs = {k: v for k, v in kwargs.items() if k in self._LOGGING_KWARGS}
        extra = {k: v for k, v in kwargs.items() if k not in self._LOGGING_KWARGS}
        return logging_kwargs, extra

    def debug(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.debug(self._format(event, extra), **logging_kwargs)

    def info(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.info(self._format(event, extra), **logging_kwargs)

    def warning(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.warning(self._format(event, extra), **logging_kwargs)

    def warn(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.warning(self._format(event, extra), **logging_kwargs)

    def error(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.error(self._format(event, extra), **logging_kwargs)

    def fatal(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.fatal(self._format(event, extra), **logging_kwargs)

    def exception(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.exception(self._format(event, extra), **logging_kwargs)

    def critical(self, event: str, **kwargs: Any) -> Any:
        logging_kwargs, extra = self._split_kwargs(kwargs)
        return self._logger.critical(self._format(event, extra), **logging_kwargs)

    def set_level(self, level: int) -> None:
        self._logger.setLevel(level)

    def bind(self, **kwargs: Any) -> StdlibLogger:
        new_context = {**self._context, **kwargs}
        return StdlibLogger(
            name=self._logger.name,
            _context=new_context,
        )

    def unbind(self, *keys: str) -> StdlibLogger:
        new_context = {k: v for k, v in self._context.items() if k not in keys}
        return StdlibLogger(
            name=self._logger.name,
            _context=new_context,
        )

    def new(self, **kwargs: Any) -> StdlibLogger:
        return StdlibLogger(
            name=self._logger.name,
            _context=dict(kwargs),
        )
