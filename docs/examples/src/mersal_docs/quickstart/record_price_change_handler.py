from __future__ import annotations

from messages import PriceDecreased

__all__ = ("RecordPriceChangeHandler",)


_price_change_log: list[str] = []


class RecordPriceChangeHandler:
    async def __call__(self, event: PriceDecreased) -> None:
        _price_change_log.append(f"{event.product_id}: ${event.new_price:.2f}")
        print(f"[accounting] Logged price change for {event.product_id}: now ${event.new_price:.2f}")
