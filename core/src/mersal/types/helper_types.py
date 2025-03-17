from collections.abc import Awaitable
from typing import TypeAlias, TypeVar

T = TypeVar("T")

SyncOrAsyncUnion: TypeAlias = T | Awaitable[T]
