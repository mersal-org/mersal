from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mersal.pipeline import MessageContext

__all__ = ("CorrelationProperty",)


@dataclass
class CorrelationProperty:
    message_type: type
    saga_data_type: type
    property_name: str
    value_extractor: Callable[[MessageContext], Any]
