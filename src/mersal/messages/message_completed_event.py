from dataclasses import dataclass

__all__ = ("MessageCompletedEvent",)


@dataclass
class MessageCompletedEvent:
    completed_message_id: str
