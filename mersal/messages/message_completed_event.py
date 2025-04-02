from dataclasses import dataclass
from typing import Any

__all__ = ("MessageCompletedEvent",)


@dataclass
class MessageCompletedEvent:
    completed_message_id: Any
