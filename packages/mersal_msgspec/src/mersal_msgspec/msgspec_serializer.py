from typing import Any, cast

from mersal.exceptions import MissingDependencyExceptionError

try:
    import msgspec
except ImportError as e:
    raise MissingDependencyExceptionError("msgspec") from e
from mersal.messages.message_headers import MessageHeaders
from mersal.serialization import Serializer

__all__ = ("MsgspecSerializer",)


class MsgspecSerializer(Serializer):
    class ObjectWrapper(msgspec.Struct):
        type: str
        object: msgspec.Raw | dict[Any, Any]

    def __init__(self, object_types: set[type]) -> None:
        self._name_to_type: dict[str, type] = {}
        for object_type in object_types:
            name = object_type.__name__
            self._name_to_type[name] = object_type
        self._encoder = msgspec.json.Encoder()
        self._decoder = msgspec.json.Decoder(type=self.ObjectWrapper)

    def serialize(self, obj: Any) -> Any:
        if isinstance(obj, dict | MessageHeaders):
            _type = "dict"
            _object = dict(obj)
        else:
            _type = type(obj).__name__
            _object = obj

        encoded_object = self._encoder.encode(_object)
        return self._encoder.encode(self.ObjectWrapper(type=_type, object=msgspec.Raw(encoded_object)))

    def deserialize(self, data: Any) -> Any:
        unwrapped = self._decoder.decode(data)

        if unwrapped.type == "dict":
            _data = cast("dict", unwrapped.object)
            return msgspec.to_builtins(_data)  # pyright: ignore[reportCallIssue, reportArgumentType]

        object_type = self._name_to_type.get(unwrapped.type)
        return msgspec.convert(unwrapped.object, type=object_type)  # pyright: ignore[reportCallIssue, reportArgumentType]
