from collections.abc import Awaitable, Callable
from typing import TypeAlias, TypeVar

MessageT = TypeVar("MessageT")

MessageHandler: TypeAlias = Callable[[MessageT], Awaitable[None]]
