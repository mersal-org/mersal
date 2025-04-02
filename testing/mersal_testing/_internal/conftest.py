import pytest

from mersal.messages import TransportMessage
from mersal.persistence.in_memory.in_memory_subscription_storage import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.serialization.identity_serializer.identity_object_serializer import (
    IdentitySerializer,
)
from mersal.transport.in_memory import (
    InMemoryNetwork,
    InMemoryTransport,
    InMemoryTransportConfig,
)
from mersal_testing.test_doubles import TransportMessageBuilder

__all__ = (
    "anyio_backend",
    "fx_in_memory_network",
    "fx_in_memory_subscription_storage",
    "fx_in_memory_subscription_store",
    "fx_in_memory_transport",
    "fx_serializer",
    "transport_message",
)


@pytest.fixture(name="in_memory_network")
def fx_in_memory_network() -> InMemoryNetwork:
    return InMemoryNetwork()


@pytest.fixture(name="in_memory_transport")
def fx_in_memory_transport(in_memory_network: InMemoryNetwork) -> InMemoryTransport:
    return InMemoryTransportConfig(network=in_memory_network, input_queue_address="in_memory_queue_address").transport


@pytest.fixture(name="in_memory_subscription_store")
def fx_in_memory_subscription_store() -> InMemorySubscriptionStore:
    return InMemorySubscriptionStore()


@pytest.fixture(name="in_memory_subscription_storage")
def fx_in_memory_subscription_storage(
    in_memory_subscription_store: InMemorySubscriptionStore,
) -> InMemorySubscriptionStorage:
    return InMemorySubscriptionStorage.centralized(in_memory_subscription_store)


@pytest.fixture(name="serializer")
def fx_serializer() -> IdentitySerializer:
    return IdentitySerializer()


@pytest.fixture(
    params=[pytest.param("asyncio", id="asyncio")]  # , pytest.param("trio", id="trio")],
)
def anyio_backend(request: pytest.FixtureRequest) -> str:
    # We need to return a string but mypy is confused because request.param could be Any
    # We know it's a string based on the params list above
    return str(request.param)


@pytest.fixture
def transport_message() -> TransportMessage:
    # We're confident this is returning a TransportMessage object
    result = TransportMessageBuilder.build()
    assert isinstance(result, TransportMessage)
    return result
