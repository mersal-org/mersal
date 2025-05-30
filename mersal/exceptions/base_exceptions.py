from typing import Any

__all__ = (
    "ConcurrencyExceptionError",
    "MersalExceptionError",
    "MissingDependencyExceptionError",
)


class MersalExceptionError(Exception):
    """Base exception class from which all Mersal exceptions inherit."""

    detail: str

    def __init__(self, *args: Any, detail: str = "") -> None:
        """Initialize ``mersalException``.

        Args:
            *args: args are converted to :class:`str` before passing to :class:`Exception`
            detail: detail of the exception.
        """
        self.detail = detail
        super().__init__(*(str(arg) for arg in args if arg), detail)

    def __repr__(self) -> str:
        if self.detail:
            return f"{self.__class__.__name__} - {self.detail}"
        return self.__class__.__name__

    def __str__(self) -> str:
        return " ".join(self.args).strip()


class MissingDependencyExceptionError(MersalExceptionError, ImportError):
    """Missing optional dependency.

    This exception is raised only when a module depends on a dependency that has not been installed.
    """

    def __init__(self, package: str, install_package: str | None = None) -> None:
        super().__init__(
            f"Package {package!r} is not installed but required. You can install it by running "
            f"'pip install litestar[{install_package or package}]' to install litestar with the required extra "
            f"or 'pip install {install_package or package}' to install the package separately"
        )


class ConcurrencyExceptionError(MersalExceptionError):
    pass
