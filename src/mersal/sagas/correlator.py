from collections.abc import Callable, Sequence
from typing import Any

from mersal.pipeline import MessageContext
from mersal.sagas.correlation_property import CorrelationProperty

__all__ = ("Correlator",)


class Correlator:
    def __init__(self, saga_data_type: type) -> None:
        self._correlation_properties: list[CorrelationProperty] = []
        self._saga_data_type = saga_data_type

    def correlate(
        self,
        message_type: type,
        value_extractor: Callable[[MessageContext], Any],
        property_name: str,
    ) -> None:
        self._correlation_properties.append(
            CorrelationProperty(
                message_type=message_type,
                saga_data_type=self._saga_data_type,
                property_name=property_name,
                value_extractor=value_extractor,
            )
        )

    @property
    def correlation_properties(self) -> Sequence[CorrelationProperty]:
        return self._correlation_properties
