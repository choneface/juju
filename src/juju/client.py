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

    async def send(self, message: Any) -> Response:
        if self.codec != "jsonlines":
            raise ValueError(f"unsupported codec: {self.codec}")

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
            payload = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), timeout=self.timeout)
            raw = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
            if not raw:
                raise EOFError("IPC peer closed without sending a response")
            return Response(body=json.loads(raw), raw=raw)
        finally:
            writer.close()
            await writer.wait_closed()


def connect(url: str, *, timeout: float = 3.0, codec: str = "jsonlines") -> IpcClient:
    return IpcClient(url=url, timeout=timeout, codec=codec)
