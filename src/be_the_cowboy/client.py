from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from google.protobuf.message import Message

from .response import Response


@dataclass(frozen=True)
class IpcClient:
    url: str
    timeout: float = 3.0
    codec: str = "jsonlines"
    response: str = "jsonlines"
    message_type: type[Message] | None = None
    response_type: type[Message] | None = None

    async def send(self, message: Any) -> Response:
        parsed = urlparse(self.url)
        if parsed.scheme == "tcp":
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(parsed.hostname, parsed.port),
                timeout=self.timeout,
            )
        elif parsed.scheme == "unix":
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(parsed.path),
                timeout=self.timeout,
            )
        else:
            raise ValueError(f"unsupported IPC URL scheme: {parsed.scheme!r}")

        try:
            payload = encode(message, self.codec, self.message_type)
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), timeout=self.timeout)

            if self.response == "none":
                return Response(body=None, raw=b"")

            raw = await read_response(reader, self.response, self.timeout)
            if not raw:
                raise EOFError("IPC peer closed without sending a response")
            return Response(body=decode(raw, self.response, self.response_type), raw=raw)
        finally:
            writer.close()
            await writer.wait_closed()


async def read_response(reader: asyncio.StreamReader, codec: str, timeout: float) -> bytes:
    if codec in {"jsonlines", "text"}:
        return await asyncio.wait_for(reader.readline(), timeout=timeout)

    if codec == "protobuf":
        return await asyncio.wait_for(reader.read(), timeout=timeout)

    raise ValueError(f"unsupported response codec: {codec}")


def encode(message: Any, codec: str, message_type: type[Message] | None = None) -> bytes:
    if codec == "jsonlines":
        return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"

    if codec == "text":
        if isinstance(message, bytes):
            payload = message
        else:
            payload = str(message).encode("utf-8")
        return payload if payload.endswith(b"\n") else payload + b"\n"

    if codec == "protobuf":
        return to_protobuf_message(message, message_type).SerializeToString()

    raise ValueError(f"unsupported codec: {codec}")


def decode(raw: bytes, codec: str, response_type: type[Message] | None = None) -> Any:
    if codec == "jsonlines":
        return json.loads(raw)

    if codec == "text":
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    if codec == "protobuf":
        if response_type is None:
            raise ValueError("response_type is required for protobuf responses")
        message = response_type()
        message.ParseFromString(raw)
        return message

    raise ValueError(f"unsupported response codec: {codec}")


def to_protobuf_message(message: Any, message_type: type[Message] | None) -> Message:
    if isinstance(message, Message):
        return message

    if message_type is None:
        raise ValueError("message_type is required when sending non-message protobuf values")

    if isinstance(message, dict):
        protobuf = message_type()
        for key, value in message.items():
            setattr(protobuf, key, value)
        return protobuf

    raise TypeError(f"expected protobuf message or dict, got {type(message).__name__}")


def connect(
    url: str,
    *,
    timeout: float = 3.0,
    codec: str = "jsonlines",
    response: str = "jsonlines",
    message_type: type[Message] | None = None,
    response_type: type[Message] | None = None,
) -> IpcClient:
    return IpcClient(
        url=url,
        timeout=timeout,
        codec=codec,
        response=response,
        message_type=message_type,
        response_type=response_type,
    )
