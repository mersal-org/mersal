from typing import Any

import pytest

from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal_testing.transport.basic_transport_tests import (
    BasicTransportTest,
    TransportMaker,
)

__all__ = ("TestBasicTransportFunctionalityForInMemoryTransport",)


pytestmark = pytest.mark.anyio


class TestBasicTransportFunctionalityForInMemoryTransport(BasicTransportTest):
    @pytest.fixture(scope="function")
    def in_memory_network(self):
        return InMemoryNetwork()

    @pytest.fixture
    def transport_maker(self, in_memory_network: InMemoryNetwork) -> TransportMaker:  # pyright: ignore[reportIncompatibleMethodOverride]
        def maker(**kwargs: Any):
            input_queue_address = kwargs.get("input_queue_address", "default")
            return InMemoryTransport(
                InMemoryTransportConfig(network=in_memory_network, input_queue_address=input_queue_address)
            )

        return maker
