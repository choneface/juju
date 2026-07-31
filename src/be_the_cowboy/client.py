from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .response import Response


@dataclass(frozen=True)
class IpcClient:
    url: str
    timeout: float = 3.0
    codec: str = "jsonlines"
    response: str = "jsonlines"

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
            payload = encode(message, self.codec)
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), timeout=self.timeout)

            if self.response == "none":
                return Response(body=None, raw=b"")

            raw = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
            if not raw:
                raise EOFError("IPC peer closed without sending a response")
            return Response(body=decode(raw, self.response), raw=raw)
        finally:
            writer.close()
            await writer.wait_closed()


def encode(message: Any, codec: str) -> bytes:
    if codec == "jsonlines":
        return json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"

    if codec == "text":
        if isinstance(message, bytes):
            payload = message
        else:
            payload = str(message).encode("utf-8")
        return payload if payload.endswith(b"\n") else payload + b"\n"

    raise ValueError(f"unsupported codec: {codec}")


def decode(raw: bytes, codec: str) -> Any:
    if codec == "jsonlines":
        return json.loads(raw)

    if codec == "text":
        return raw.decode("utf-8", errors="replace").rstrip("\r\n")

    raise ValueError(f"unsupported response codec: {codec}")


def connect(
    url: str,
    *,
    timeout: float = 3.0,
    codec: str = "jsonlines",
    response: str = "jsonlines",
) -> IpcClient:
    return IpcClient(url=url, timeout=timeout, codec=codec, response=response)
