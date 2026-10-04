from collections import UserDict
from collections.abc import Mapping
from datetime import datetime

__all__ = ("MessageHeaders",)


class MessageHeaders(UserDict, Mapping[str, str]):
    """Message headers, always string-keyed and string-valued.

    Every real transport (RabbitMQ's AMQP field tables for non-native types, GCP
    Pub/Sub's string-only attributes) round-trips header values as strings, so
    values are coerced to `str` on write here rather than only at the transport
    boundary - keeping the in-memory transport's behavior consistent with every
    other transport instead of silently preserving richer types that then break
    on a real broker.
    """

    message_id_key = "message_id"
    message_type_key = "message_type"
    correlation_id_key = "correlation_id"
    correlation_sequence_key = "correlation_sequence"
    causation_id_key = "causation_id"
    deferred_until_key = "deferred_until"
    deferred_recipient_key = "deferred_recipient"
    traceparent_key = "traceparent"
    """W3C Trace Context header (https://www.w3.org/TR/trace-context/). See `mersal.tracing`."""

    def __setitem__(self, key: str, item: object) -> None:
        super().__setitem__(str(key), str(item))

    @property
    def message_id(self) -> str | None:
        return self.get(self.message_id_key)

    @property
    def message_type(self) -> str | None:
        return self.get(self.message_type_key)

    @property
    def correlation_id(self) -> str | None:
        return self.get(self.correlation_id_key)

    @property
    def correlation_sequence(self) -> int | None:
        value = self.get(self.correlation_sequence_key)
        return int(value) if value is not None else None

    @property
    def causation_id(self) -> str | None:
        return self.get(self.causation_id_key)

    @property
    def traceparent(self) -> str | None:
        return self.get(self.traceparent_key)

    @property
    def deferred_until(self) -> datetime | None:
        """Time (timezone-aware, ISO 8601) before which the message must not be delivered."""
        value = self.get(self.deferred_until_key)
        return datetime.fromisoformat(value) if value is not None else None

    @property
    def deferred_recipient(self) -> str | None:
        """Address the deferred message must be delivered to once it is due."""
        return self.get(self.deferred_recipient_key)
