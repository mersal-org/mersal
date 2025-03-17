from typing import Any

from mersal.serialization.serializers import Serializer

__all__ = ("IdentitySerializer",)


class IdentitySerializer(Serializer):
    def serialize(self, obj: Any) -> Any:
        return obj

    def deserialize(self, data: Any) -> Any:
        return data
