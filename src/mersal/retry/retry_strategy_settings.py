from dataclasses import dataclass

__all__ = ("RetryStrategySettings",)


@dataclass
class RetryStrategySettings:
    error_queue_name: str = "error"
    max_no_of_retries: int = 5
    error_tracking_max_age_seconds: float = 1800.0
    """Evict a tracked message's error history once this long has passed since its last
    registered error, regardless of whether `clean_up` was ever called for it.

    A safety net for `InMemoryErrorTracker` against entries that never reach an explicit
    `clean_up` call (e.g. the message is redelivered to a different worker instance, or
    this instance is killed/restarted before the message next succeeds or is
    deadlettered) - mirrors Rebus's `InMemErrorTracker` age-based sweep.
    """
    error_tracking_sweep_interval_seconds: float = 60.0
    """How often `InMemoryErrorTracker` checks for entries older than
    `error_tracking_max_age_seconds`."""
