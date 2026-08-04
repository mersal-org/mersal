from typing import Final

IDEMPOTENCY_CHECK_KEY: Final = "mersal-message-is-repeated"
"""Key added to MessageHeaders to indicate if the message is repeated."""
