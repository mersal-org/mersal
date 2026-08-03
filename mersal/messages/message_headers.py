from collections import UserDict
from collections.abc import Mapping

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
    correlation_id_key = "correlation_id"
    correlation_sequence_key = "correlation_sequence"
    causation_id_key = "causation_id"

    def __setitem__(self, key: str, value: object) -> None:
        super().__setitem__(str(key), str(value))

    @property
    def message_id(self) -> str | None:
        return self.get(self.message_id_key)

    @property
    def message_type(self) -> str | None:
        return self.get("message_type")

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
