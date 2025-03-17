from abc import ABCMeta, abstractmethod
from collections.abc import Sequence
from typing import Any, Generic, Protocol, runtime_checkable

from typing_extensions import Self

from mersal.sagas.correlation_property import CorrelationProperty
from mersal.sagas.correlator import Correlator
from mersal.sagas.saga_data import SagaData, SagaDataT

__all__ = (
    "Saga",
    "SagaBase",
)


@runtime_checkable
class Saga(Protocol, Generic[SagaDataT]):
    correlator: Correlator
    data: SagaData[SagaDataT]
    data_type: type[SagaDataT]
    initiating_message_types: set[type]
    is_completed: bool
    is_unchanged: bool

    def correlate_messages(self, correlator: Correlator) -> None: ...

    @property
    def correlation_properties(self) -> Sequence[CorrelationProperty]: ...

    def generate_new_data(self) -> SagaData[SagaDataT]: ...

    async def resolve_conflict(self, fresh_data: SagaData[SagaDataT]) -> None: ...


class SagaBase(Saga, Generic[SagaDataT], metaclass=ABCMeta):
    initiating_message_types: set[type]

    def __init__(self) -> None:
        self.data: SagaData[SagaDataT] = None  # type: ignore[assignment]
        self.correlator = Correlator(self.data_type)
        self.is_completed = False
        self.is_unchanged = False

    def __class_getitem__(cls, annotation: Any) -> type[Self]:
        cls_dict: dict[str, Any] = {"data_type": annotation}

        return type(f"{cls.__name__}[{annotation}]", (cls,), cls_dict)  # type: ignore[return-value]

    @abstractmethod
    def correlate_messages(self, correlator: Correlator) -> None: ...

    @property
    def correlation_properties(self) -> Sequence[CorrelationProperty]:
        self.correlate_messages(self.correlator)
        return self.correlator.correlation_properties

    @abstractmethod
    def generate_new_data(self) -> SagaData[SagaDataT]: ...

    async def resolve_conflict(self, fresh_data: SagaData[SagaDataT]) -> None: ...
