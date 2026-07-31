from __future__ import annotations

import asyncio
import os
import shlex
import signal
import socket
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Union

ReadyCheck = Callable[[], Union[bool, Awaitable[bool]]]


@dataclass
class App:
    command: str | Sequence[str]
    cwd: str | os.PathLike[str] | None = None
    env: dict[str, str] | None = None
    ready: ReadyCheck | None = None
    timeout: float = 15.0
    stdout: int | None = None
    stderr: int | None = None

    def __post_init__(self) -> None:
        self.process: asyncio.subprocess.Process | None = None

    async def start(self) -> "App":
        if self.process and self.process.returncode is None:
            return self

        args = shlex.split(self.command) if isinstance(self.command, str) else list(self.command)
        env = os.environ.copy()
        if self.env:
            env.update(self.env)

        self.process = await asyncio.create_subprocess_exec(
            *args,
            cwd=str(Path(self.cwd)) if self.cwd else None,
            env=env,
            stdout=self.stdout if self.stdout is not None else sys.stdout.fileno(),
            stderr=self.stderr if self.stderr is not None else sys.stderr.fileno(),
        )

        if self.ready:
            await self.wait_until_ready()
        return self

    async def wait_until_ready(self) -> None:
        if not self.ready:
            return

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self.process and self.process.returncode is not None:
                raise RuntimeError(f"app exited before it became ready: {self.process.returncode}")

            result = self.ready()
            if asyncio.iscoroutine(result) or isinstance(result, Awaitable):
                result = await result
            if result:
                return
            await asyncio.sleep(0.05)

        raise TimeoutError(f"app was not ready within {self.timeout:.1f}s")

    async def stop(self, grace: float = 2.0) -> None:
        if not self.process or self.process.returncode is not None:
            return

        self.process.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(self.process.wait(), timeout=grace)
        except TimeoutError:
            self.process.kill()
            await self.process.wait()


def app(
    command: str | Sequence[str],
    *,
    cwd: str | os.PathLike[str] | None = None,
    env: dict[str, str] | None = None,
    ready: ReadyCheck | None = None,
    timeout: float = 15.0,
) -> App:
    return App(command=command, cwd=cwd, env=env, ready=ready, timeout=timeout)


def tcp_ready(host: str, port: int, timeout: float = 0.2) -> ReadyCheck:
    def check() -> bool:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except OSError:
            return False

    return check


def unix_ready(path: str | os.PathLike[str], timeout: float = 0.2) -> ReadyCheck:
    def check() -> bool:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect(str(path))
            return True
        except OSError:
            return False
        finally:
            sock.close()

    return check
