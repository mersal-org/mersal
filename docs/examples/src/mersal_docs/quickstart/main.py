from __future__ import annotations

import argparse
from pathlib import Path

import anyio
from notify_wishlist_users_handler import NotifyWishlistUsersHandler
from record_price_change_handler import RecordPriceChangeHandler
from update_price_message_handler import UpdateProductPriceHandler

from mersal.activation import BuiltinHandlerActivator
from mersal.app import Mersal
from mersal.persistence.in_memory import (
    InMemorySubscriptionStorage,
    InMemorySubscriptionStore,
)
from mersal.serialization.dataclass_serializer import DataclassSerializer
from mersal.transport.file_system import FileSystemTransportConfig
from messages import PriceDecreased, UpdateProductPrice

__all__ = (
    "main",
    "make_mersal_app",
)


def make_mersal_app(
    name: str,
    base_directory: str | Path,
    subscription_store: InMemorySubscriptionStore | None = None,
) -> tuple[Mersal, BuiltinHandlerActivator]:
    activator = BuiltinHandlerActivator()
    transport = FileSystemTransportConfig(
        base_directory=base_directory,
        input_queue_address=name,
    ).transport
    if subscription_store is None:
        subscription_store = InMemorySubscriptionStore()
    app = Mersal(
        name,
        activator,
        transport=transport,
        message_body_serializer=DataclassSerializer({UpdateProductPrice, PriceDecreased}),
        subscription_storage=InMemorySubscriptionStorage.centralized(subscription_store),
    )
    return app, activator


async def main(run_catalog: bool, run_notifications: bool) -> None:
    subscription_store = InMemorySubscriptionStore()
    base_directory = ".mersal-quickstart"

    catalog_app, catalog_activator = make_mersal_app("catalog", base_directory, subscription_store)
    notifications_app, notifications_activator = make_mersal_app("notifications", base_directory, subscription_store)
    accounting_app, accounting_activator = make_mersal_app("accounting", base_directory, subscription_store)

    catalog_activator.register(UpdateProductPrice, lambda _, app: UpdateProductPriceHandler(app))
    notifications_activator.register(PriceDecreased, lambda _, __: NotifyWishlistUsersHandler())
    accounting_activator.register(PriceDecreased, lambda _, __: RecordPriceChangeHandler())
    await notifications_app.subscribe(PriceDecreased)
    await accounting_app.subscribe(PriceDecreased)

    if run_catalog:
        await catalog_app.start()
    if run_notifications:
        await notifications_app.start()
    await accounting_app.start()

    print("Running. Press Ctrl+C to stop.")
    await anyio.sleep_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--notifications", action="store_true")
    args = parser.parse_args()

    run_both = not args.catalog and not args.notifications
    anyio.run(main, args.catalog or run_both, args.notifications or run_both)
