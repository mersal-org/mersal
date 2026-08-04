from __future__ import annotations

import anyio
from main import make_mersal_app
from messages import UpdateProductPrice

__all__ = ("main",)


async def main() -> None:
    catalog_app, _ = make_mersal_app("catalog", ".mersal-quickstart")
    await catalog_app.send_local(UpdateProductPrice("product-42", 799.0))


if __name__ == "__main__":
    anyio.run(main)
