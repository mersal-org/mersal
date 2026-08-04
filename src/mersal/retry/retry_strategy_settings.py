from dataclasses import dataclass

__all__ = ("RetryStrategySettings",)


@dataclass
class RetryStrategySettings:
    error_queue_name: str = "error"
    max_no_of_retries: int = 5
