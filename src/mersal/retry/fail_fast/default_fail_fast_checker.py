import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from .fail_fast_checker import FailFastChecker

__all__ = (
    "DefaultFailFastChecker",
    "DefaultFailFastCheckerExceptionsContainer",
)


@dataclass
class DefaultFailFastCheckerExceptionsContainer:
    exceptions: Sequence[type[Exception]]


class DefaultFailFastChecker(FailFastChecker):
    def __init__(self, fail_fast_exceptions: Sequence[type[Exception]]):
        self.fail_fast_exceptions = fail_fast_exceptions

    def should_fail_fast(self, message_id: uuid.UUID, exception: Exception) -> bool:
        return any(isinstance(exception, x) for x in self.fail_fast_exceptions)
