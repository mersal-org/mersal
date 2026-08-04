from dataclasses import dataclass

from mersal.sagas.correlation_error_handler import CorrelationErrorHandler
from mersal.sagas.plugin import SagaPlugin
from mersal.sagas.saga_storage import SagaStorage

__all__ = ("SagaConfig",)


@dataclass
class SagaConfig:
    storage: SagaStorage
    correlation_error_handler: CorrelationErrorHandler | None = None

    @property
    def plugin(self) -> SagaPlugin:
        return SagaPlugin(self)
