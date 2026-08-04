from typing import Protocol

from .retry_step import RetryStep

__all__ = ("RetryStrategy",)


class RetryStrategy(Protocol):
    def get_retry_step(self) -> RetryStep: ...
