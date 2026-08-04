from typing import Any, Protocol, TypeAlias

__all__ = ("Serializer",)


class Serializer(Protocol):
    def serialize(self, obj: Any) -> Any: ...

    def deserialize(self, data: Any) -> Any: ...


MessageBodySerializer: TypeAlias = Serializer
MessageHeadersSerializer: TypeAlias = Serializer
