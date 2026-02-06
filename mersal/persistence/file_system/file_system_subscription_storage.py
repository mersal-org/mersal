from __future__ import annotations

import json
from pathlib import Path

from typing_extensions import Self

from mersal.subscription import SubscriptionStorage

__all__ = ("FileSystemSubscriptionStorage",)


class FileSystemSubscriptionStorage(SubscriptionStorage):
    __slots__ = ["_base_directory", "_is_centralized"]

    def __init__(self) -> None:
        self._base_directory: Path = None  # type: ignore[assignment]
        self._is_centralized: bool = None  # type: ignore[assignment]
        raise NotImplementedError()

    @classmethod
    def centralized(cls, base_directory: str | Path) -> Self:
        obj = cls.__new__(cls)
        obj._init(base_directory, is_centralized=True)
        return obj

    @classmethod
    def decentralized(cls, base_directory: str | Path) -> Self:
        obj = cls.__new__(cls)
        obj._init(base_directory, is_centralized=False)
        return obj

    def _init(self, base_directory: str | Path, *, is_centralized: bool) -> None:
        self._base_directory = Path(base_directory) / "subscriptions"
        self._base_directory.mkdir(parents=True, exist_ok=True)
        self._is_centralized = is_centralized

    async def register_subscriber(self, topic: str, subscriber_address: str) -> None:
        subscribers = self._read_topic(topic)
        subscribers.add(subscriber_address)
        self._write_topic(topic, subscribers)

    async def get_subscriber_addresses(self, topic: str) -> set[str]:
        return self._read_topic(topic)

    @property
    def is_centralized(self) -> bool:
        return self._is_centralized

    async def unregister_subscriber(self, topic: str, subscriber_address: str) -> None:
        subscribers = self._read_topic(topic)
        subscribers.discard(subscriber_address)
        self._write_topic(topic, subscribers)

    def _topic_path(self, topic: str) -> Path:
        return self._base_directory / f"{topic}.json"

    def _read_topic(self, topic: str) -> set[str]:
        path = self._topic_path(topic)
        if not path.exists():
            return set()
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data)

    def _write_topic(self, topic: str, subscribers: set[str]) -> None:
        path = self._topic_path(topic)
        path.write_text(json.dumps(sorted(subscribers)), encoding="utf-8")
