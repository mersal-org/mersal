#
__all__ = ("Singleton",)


from typing import Any


class Singleton(type):
    def __init__(cls, *args: Any, **kwargs: Any) -> None:
        cls.__instance = None
        super().__init__(*args, **kwargs)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
            return cls.__instance
        return cls.__instance  # type: ignore[unreachable]
