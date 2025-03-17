import uuid
from dataclasses import dataclass
from typing import Generic, TypeVar

__all__ = ("SagaData",)


SagaDataT = TypeVar("SagaDataT")


@dataclass
class SagaData(Generic[SagaDataT]):
    id: uuid.UUID
    revision: int
    data: SagaDataT
