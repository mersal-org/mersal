from collections.abc import Iterator
from dataclasses import dataclass

__all__ = ("DestinationAddresses",)


@dataclass
class DestinationAddresses:
    address: set[str]

    def __iter__(self) -> Iterator[str]:
        return iter(self.address)
