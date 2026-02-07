from __future__ import annotations

import importlib
import json
import uuid
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mersal.exceptions.base_exceptions import ConcurrencyExceptionError
from mersal.sagas.saga_data import SagaData
from mersal.sagas.saga_storage import SagaStorage

if TYPE_CHECKING:
    from collections.abc import Sequence

    from mersal.sagas import CorrelationProperty
    from mersal.transport import TransactionContext

__all__ = ("FileSystemSagaStorage",)


class FileSystemSagaStorage(SagaStorage):
    def __init__(self, base_directory: str | Path) -> None:
        self._base_directory = Path(base_directory) / "sagas"

    async def __call__(self) -> None:
        if self._base_directory.exists():
            for f in self._base_directory.iterdir():
                if f.suffix == ".json":
                    f.unlink()
        self._base_directory.mkdir(parents=True, exist_ok=True)

    async def find_using_id(self, saga_data_type: type, message_id: uuid.UUID) -> SagaData | None:
        path = self._saga_path(message_id)
        if not path.exists():
            return None
        return self._read_saga(path)

    async def find(self, saga_data_type: type, property_name: str, property_value: Any) -> SagaData | None:
        for saga_data in self._read_all():
            if type(saga_data.data) is not saga_data_type:
                continue

            if hasattr(saga_data.data, property_name) and getattr(saga_data.data, property_name) == property_value:
                return deepcopy(saga_data)

        return None

    async def insert(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        path = self._saga_path(saga_data.id)
        if path.exists():
            raise Exception("SagaData already exist")

        self._verify_correlation_properties_uniqueness(saga_data, correlation_properties)
        if saga_data.revision != 0:
            raise Exception("Inserted data must have revision=0")

        self._write_saga(path, deepcopy(saga_data))

    async def update(
        self,
        saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
        transaction_context: TransactionContext,
    ) -> None:
        self._verify_correlation_properties_uniqueness(saga_data, correlation_properties)
        path = self._saga_path(saga_data.id)
        if not path.exists():
            raise Exception("Saga couldn't be found")

        current_saga_data = self._read_saga(path)
        if not current_saga_data.revision == saga_data.revision:
            raise ConcurrencyExceptionError("Concurrency issues, different revisios")

        _copy = deepcopy(saga_data)
        _copy.revision += 1
        self._write_saga(path, _copy)
        saga_data.revision += 1

    async def delete(self, saga_data: SagaData, transaction_context: TransactionContext) -> None:
        path = self._saga_path(saga_data.id)
        if path.exists():
            path.unlink()

        saga_data.revision += 1

    def _saga_path(self, saga_id: uuid.UUID) -> Path:
        return self._base_directory / f"{saga_id}.json"

    def _read_saga(self, path: Path) -> SagaData:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _deserialize_saga_data(data)

    def _write_saga(self, path: Path, saga_data: SagaData) -> None:
        data = _serialize_saga_data(saga_data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _read_all(self) -> list[SagaData]:
        if not self._base_directory.exists():
            return []
        result = []
        for path in self._base_directory.iterdir():
            if path.suffix == ".json":
                result.append(self._read_saga(path))
        return result

    def _verify_correlation_properties_uniqueness(
        self,
        new_or_updated_saga_data: SagaData,
        correlation_properties: Sequence[CorrelationProperty],
    ) -> None:
        for existing_saga_data in self._read_all():
            if existing_saga_data.id == new_or_updated_saga_data.id:
                continue

            if type(existing_saga_data) is type(new_or_updated_saga_data):
                continue

            for correlation_property in correlation_properties:
                property_name = correlation_property.property_name
                new_value = getattr(new_or_updated_saga_data.data, property_name)
                if hasattr(existing_saga_data.data, property_name):
                    existing_value = getattr(existing_saga_data.data, property_name)

                    if existing_value == new_value:
                        raise Exception("Correlation properties are not unique!")


def _serialize_saga_data(saga_data: SagaData) -> dict:
    data_obj = saga_data.data
    data_type = type(data_obj)

    return {
        "id": str(saga_data.id),
        "revision": saga_data.revision,
        "data": vars(data_obj) if hasattr(data_obj, "__dict__") else data_obj,
        "data_type_module": data_type.__module__,
        "data_type_name": data_type.__qualname__,
    }


def _deserialize_saga_data(raw: dict) -> SagaData:
    module = importlib.import_module(raw["data_type_module"])
    data_type = getattr(module, raw["data_type_name"])
    data_dict = raw["data"]

    data_obj = data_type(**data_dict) if isinstance(data_dict, dict) else data_dict

    return SagaData(
        id=uuid.UUID(raw["id"]),
        revision=raw["revision"],
        data=data_obj,
    )
