from asyncio import iscoroutinefunction
from collections.abc import Awaitable, Callable
from functools import partial
from typing import ParamSpec, TypeGuard, TypeVar

__all__ = ("is_async_callable",)


P = ParamSpec("P")
T = TypeVar("T")


def is_async_callable(value: Callable[P, T]) -> TypeGuard[Callable[P, Awaitable[T]]]:
    """Extend :func:`asyncio.iscoroutinefunction` to additionally detect async :func:`functools.partial` objects and
    class instances with ``async def __call__()`` defined.

    Args:
        value: Any

    Returns:
        Bool determining if type of ``value`` is an awaitable.
    """
    while isinstance(value, partial):
        value = value.func

    return iscoroutinefunction(value) or (
        callable(value) and iscoroutinefunction(value.__call__)  #  type: ignore[operator]
    )
