import uuid
from typing import Protocol

__all__ = ("FailFastChecker",)


class FailFastChecker(Protocol):
    def should_fail_fast(self, message_id: uuid.UUID, exception: Exception) -> bool: ...
