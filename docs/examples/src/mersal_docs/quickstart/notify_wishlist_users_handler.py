from __future__ import annotations

from messages import PriceDecreased

__all__ = (
    "FlakyNotifyWishlistUsersHandler",
    "NotifyWishlistUsersHandler",
)


_wishlists: dict[str, list[str]] = {
    "product-42": ["ada@example.com", "grace@example.com"],
}


class NotifyWishlistUsersHandler:
    async def __call__(self, event: PriceDecreased) -> None:
        for email in _wishlists.get(event.product_id, []):
            print(f"[notifications] Emailing {email}: {event.product_id} dropped to ${event.new_price:.2f}")


class FlakyNotifyWishlistUsersHandler:
    def __init__(self) -> None:
        self.attempts = 0

    async def __call__(self, event: PriceDecreased) -> None:
        self.attempts += 1
        print(f"[notifications] Attempt {self.attempts}: emailing wishlist for {event.product_id}...")
        raise ConnectionError("SendGrid API is currently unreachable!")
