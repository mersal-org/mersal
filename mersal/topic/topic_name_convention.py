from typing import Protocol

__all__ = ("TopicNameConvention",)


class TopicNameConvention(Protocol):
    def get_topic_name(self, event_type: type) -> str:
        """Get the name of the topic for the given event type."""
        ...
