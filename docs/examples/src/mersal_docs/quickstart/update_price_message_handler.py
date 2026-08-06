from __future__ import annotations

from typing import TYPE_CHECKING

from messages import PriceDecreased, UpdateProductPrice

if TYPE_CHECKING:
    from mersal.core.app import Mersal

__all__ = ("UpdateProductPriceHandler",)


_catalog_prices: dict[str, float] = {}


class UpdateProductPriceHandler:
    def __init__(self, catalog_app: Mersal) -> None:
        self._app = catalog_app

    async def __call__(self, command: UpdateProductPrice) -> None:
        _catalog_prices[command.product_id] = command.new_price
        print(f"[catalog] {command.product_id} is now ${command.new_price:.2f}")
        await self._app.publish(PriceDecreased(command.product_id, command.new_price))
