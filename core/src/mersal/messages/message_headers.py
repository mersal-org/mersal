from collections import UserDict
from collections.abc import Mapping
from typing import Any

__all__ = ("MessageHeaders",)


class MessageHeaders(UserDict, Mapping[str, Any]):
    message_id_key = "message_id"
    correlation_id_key = "correlation_id"
    correlation_sequence_key = "correlation_sequence"

    @property
    def message_id(self) -> Any | None:
        return self.get(self.message_id_key)

    @property
    def message_type(self) -> str | None:
        return self.get("message_type")

    @property
    def correlation_id(self) -> Any | None:
        return self.get(self.correlation_id_key)

    @property
    def correlation_sequence(self) -> int | None:
        return self.get(self.correlation_sequence_key)
