from .default_retry_step import DefaultRetryStep
from .error_handling.error_handler import ErrorHandler
from .error_tracking.error_tracker import ErrorTracker
from .fail_fast.fail_fast_checker import FailFastChecker
from .retry_strategy import RetryStrategy

__all__ = ("DefaultRetryStrategy",)


class DefaultRetryStrategy(RetryStrategy):
    def __init__(
        self,
        error_tracker: ErrorTracker,
        error_handler: ErrorHandler,
        fail_fast_checker: FailFastChecker,
        pdb_on_exception: bool = False,
    ) -> None:
        self.error_tracker = error_tracker
        self.error_handler = error_handler
        self.fail_fast_checker = fail_fast_checker
        self.pdb_on_exception = pdb_on_exception

    def get_retry_step(self) -> DefaultRetryStep:
        return DefaultRetryStep(
            self.error_tracker,
            self.error_handler,
            self.fail_fast_checker,
            self.pdb_on_exception,
        )
