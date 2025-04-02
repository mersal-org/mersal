from collections.abc import Callable
from functools import partial
from inspect import getfullargspec, ismethod
from typing import Any, Generic, ParamSpec, TypeVar

from anyio.to_thread import run_sync

from mersal.utils.predicates import is_async_callable

__all__ = (
    "AsyncCallable",
    "async_partial",
)


P = ParamSpec("P")
T = TypeVar("T")


class AsyncCallable(Generic[P, T]):
    """Wrap a callable into an asynchronous callable."""

    __slots__ = (
        "_parsed_signature",
        "args",
        "is_method",
        "kwargs",
        "num_expected_args",
        "ref",
    )

    def __init__(self, fn: Callable[P, T]) -> None:
        """Initialize the wrapper from any callable.

        Args:
            fn: Callable to wrap - can be any sync or async callable.
        """
        self.is_method = ismethod(fn) or (callable(fn) and ismethod(fn.__call__))  # type: ignore[operator]
        self.num_expected_args = len(getfullargspec(fn).args) - (1 if self.is_method else 0)
        self.ref = fn if is_async_callable(fn) else async_partial(fn)  # pyright: ignore

    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        """Proxy the wrapped function's call method.

        Args:
            *args: Args of the wrapped function.
            **kwargs: Kwargs of the wrapper function.

        Returns:
            The return value of the wrapped function.
        """
        return await self.ref(*args, **kwargs)


def async_partial(fn: Callable) -> Callable:
    """Wrap a given sync function making it async.

    In difference to the :func:`asyncio.run_sync` function, it allows for passing kwargs.

    Args:
        fn: A sync callable to wrap.

    Returns:
        A wrapper
    """

    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        applied_kwarg = partial(fn, **kwargs)
        return await run_sync(applied_kwarg, *args)

    # this allows us to unwrap the partial later, so it's an important "hack".
    wrapper.func = fn  # type: ignore[attr-defined]
    return wrapper
