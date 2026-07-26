from pathlib import Path

import pytest
from anyio import sleep
from main import make_mersal_app
from notify_wishlist_users_handler import (
    FlakyNotifyWishlistUsersHandler,
    NotifyWishlistUsersHandler,
)
from record_price_change_handler import RecordPriceChangeHandler
from update_price_message_handler import UpdateProductPriceHandler

from mersal.persistence.in_memory import InMemorySubscriptionStore
from messages import PriceDecreased, UpdateProductPrice

__all__ = (
    "test_failing_handler_ends_up_in_the_error_queue",
    "test_notifications_catches_up_on_backlog_once_started",
    "test_price_drop_notifies_wishlisted_users",
    "test_sending_never_starts_the_sender_app",
)


pytestmark = pytest.mark.anyio


async def test_price_drop_notifies_wishlisted_users(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    subscription_store = InMemorySubscriptionStore()

    catalog_app, catalog_activator = make_mersal_app("catalog", tmp_path, subscription_store)
    notifications_app, notifications_activator = make_mersal_app("notifications", tmp_path, subscription_store)
    accounting_app, accounting_activator = make_mersal_app("accounting", tmp_path, subscription_store)

    catalog_activator.register(UpdateProductPrice, lambda _, app: UpdateProductPriceHandler(app))
    notifications_activator.register(PriceDecreased, lambda _, __: NotifyWishlistUsersHandler())
    accounting_activator.register(PriceDecreased, lambda _, __: RecordPriceChangeHandler())
    await notifications_app.subscribe(PriceDecreased)
    await accounting_app.subscribe(PriceDecreased)

    async with catalog_app, notifications_app, accounting_app:
        await catalog_app.send_local(UpdateProductPrice("product-42", 799.0))
        await sleep(1)

    assert not list((tmp_path / "catalog").glob("*.json"))

    out = capsys.readouterr().out
    assert "product-42 is now $799.00" in out
    assert "ada@example.com" in out
    assert "grace@example.com" in out
    assert "Logged price change for product-42" in out


async def test_failing_handler_ends_up_in_the_error_queue(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    subscription_store = InMemorySubscriptionStore()

    catalog_app, catalog_activator = make_mersal_app("catalog", tmp_path, subscription_store)
    notifications_app, notifications_activator = make_mersal_app("notifications", tmp_path, subscription_store)
    accounting_app, accounting_activator = make_mersal_app("accounting", tmp_path, subscription_store)

    catalog_activator.register(UpdateProductPrice, lambda _, app: UpdateProductPriceHandler(app))
    handler = FlakyNotifyWishlistUsersHandler()
    notifications_activator.register(PriceDecreased, lambda _, __: handler)
    accounting_activator.register(PriceDecreased, lambda _, __: RecordPriceChangeHandler())
    await notifications_app.subscribe(PriceDecreased)
    await accounting_app.subscribe(PriceDecreased)

    async with catalog_app, notifications_app, accounting_app:
        await catalog_app.send_local(UpdateProductPrice("product-42", 799.0))
        await sleep(1)

    assert handler.attempts == 5
    dead_letters = list((tmp_path / "error").glob("*.json"))
    assert len(dead_letters) == 1

    out = capsys.readouterr().out
    assert "Logged price change for product-42" in out


async def test_sending_never_starts_the_sender_app(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    subscription_store = InMemorySubscriptionStore()

    catalog_app, catalog_activator = make_mersal_app("catalog", tmp_path, subscription_store)
    catalog_activator.register(UpdateProductPrice, lambda _, app: UpdateProductPriceHandler(app))

    # Mirrors send_price_update.py: same name/base_directory as the worker's
    # catalog app, so it resolves to the same queue, but this instance is
    # never started - sending doesn't require a running worker.
    sender_app, _ = make_mersal_app("catalog", tmp_path)

    async with catalog_app:
        await sender_app.send_local(UpdateProductPrice("product-42", 799.0))
        await sleep(1)

    out = capsys.readouterr().out
    assert "product-42 is now $799.00" in out


async def test_notifications_catches_up_on_backlog_once_started(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    subscription_store = InMemorySubscriptionStore()

    catalog_app, catalog_activator = make_mersal_app("catalog", tmp_path, subscription_store)
    notifications_app, notifications_activator = make_mersal_app("notifications", tmp_path, subscription_store)

    catalog_activator.register(UpdateProductPrice, lambda _, app: UpdateProductPriceHandler(app))
    notifications_activator.register(PriceDecreased, lambda _, __: NotifyWishlistUsersHandler())

    # Subscribing registers the queue address, even though notifications never starts.
    await notifications_app.subscribe(PriceDecreased)

    await catalog_app.start()
    await catalog_app.send_local(UpdateProductPrice("product-42", 799.0))
    await sleep(1)
    await catalog_app.stop()

    assert list((tmp_path / "notifications").glob("*.json"))
    assert "ada@example.com" not in capsys.readouterr().out

    await notifications_app.start()
    await sleep(1)
    await notifications_app.stop()

    assert not list((tmp_path / "notifications").glob("*.json"))
    out = capsys.readouterr().out
    assert "ada@example.com" in out
    assert "grace@example.com" in out
