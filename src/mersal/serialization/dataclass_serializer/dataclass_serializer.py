from dataclasses import asdict
from typing import Any

from mersal.serialization import Serializer

__all__ = ("DataclassSerializer",)


class DataclassSerializer(Serializer):
    def __init__(self, types: set[type]) -> None:
        self._types = {t.__name__: t for t in types}

    def serialize(self, obj: Any) -> Any:
        return {"type": type(obj).__name__, "data": asdict(obj)}

    def deserialize(self, data: Any) -> Any:
        return self._types[data["type"]](**data["data"])
