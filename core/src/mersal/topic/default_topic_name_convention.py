__all__ = ("DefaultTopicNameConvention",)


class DefaultTopicNameConvention:
    def get_topic_name(self, event_type: type) -> str:
        return event_type.__name__
