from dataclasses import dataclass

__all__ = (
    "PriceDecreased",
    "UpdateProductPrice",
)


@dataclass
class UpdateProductPrice:
    product_id: str
    new_price: float


@dataclass
class PriceDecreased:
    product_id: str
    new_price: float
