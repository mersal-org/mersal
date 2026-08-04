from __future__ import annotations

import base64
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from mersal.messages import TransportMessage
from mersal.messages.message_headers import MessageHeaders
from mersal.transport.base_transport import BaseTransport

if TYPE_CHECKING:
    from mersal.transport import TransactionContext
    from mersal.transport.outgoing_message import OutgoingMessage

__all__ = (
    "FileSystemTransport",
    "FileSystemTransportConfig",
)


@dataclass
class FileSystemTransportConfig:
    base_directory: str | Path
    input_queue_address: str

    @property
    def transport(self) -> FileSystemTransport:
        return FileSystemTransport(self)


class FileSystemTransport(BaseTransport):
    def __init__(self, config: FileSystemTransportConfig) -> None:
        super().__init__(address=config.input_queue_address)
        self._base_directory = Path(config.base_directory)
        self._input_queue_address = config.input_queue_address

    async def create_queue(self, address: str) -> None:
        self._get_directory(address).mkdir(parents=True, exist_ok=True)

    async def __call__(self) -> None:
        await self.create_queue(self._input_queue_address)

    async def receive(self, transaction_context: TransactionContext) -> TransportMessage | None:
        queue_dir = self._get_directory(self._input_queue_address)
        if not queue_dir.exists():
            return None

        files = sorted(f for f in queue_dir.iterdir() if f.suffix == ".json")
        if not files:
            return None

        file_path = files[0]
        data = json.loads(file_path.read_text(encoding="utf-8"))
        file_path.unlink()

        message = _deserialize_transport_message(data)

        async def on_nack(_: TransactionContext) -> None:
            self._deliver(self._input_queue_address, message)

        transaction_context.on_nack(on_nack)

        return message

    async def send_outgoing_messages(
        self,
        outgoing_message: list[OutgoingMessage],
        transaction_context: TransactionContext,
    ) -> None:
        for message in outgoing_message:
            self._deliver(message.destination_address, message.transport_message)

    def _deliver(self, destination_address: str, message: TransportMessage) -> None:
        queue_dir = self._get_directory(destination_address)
        queue_dir.mkdir(parents=True, exist_ok=True)

        file_name = f"{time.time_ns():020d}_{uuid.uuid4().hex}.json"
        file_path = queue_dir / file_name

        data = _serialize_transport_message(message)
        file_path.write_text(json.dumps(data), encoding="utf-8")

    def _get_directory(self, queue_name: str) -> Path:
        return self._base_directory / queue_name


def _serialize_transport_message(message: TransportMessage) -> dict:
    body = message.body
    if isinstance(body, bytes | bytearray):
        body_encoded = base64.b64encode(body).decode("ascii")
        body_type = "bytes"
    elif isinstance(body, str):
        body_encoded = body
        body_type = "str"
    else:
        body_encoded = json.dumps(body)
        body_type = "json"

    headers = {}
    for key, value in message.headers.items():
        headers[key] = str(value)

    return {
        "headers": headers,
        "body": body_encoded,
        "body_type": body_type,
    }


def _deserialize_transport_message(data: dict) -> TransportMessage:
    body_type = data.get("body_type", "str")
    body_encoded = data["body"]

    if body_type == "bytes":
        body = base64.b64decode(body_encoded)
    elif body_type == "json":
        body = json.loads(body_encoded)
    else:
        body = body_encoded

    headers = MessageHeaders(data.get("headers", {}))

    return TransportMessage(body=body, headers=headers)
