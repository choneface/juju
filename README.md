# be-the-cowboy

`be-the-cowboy` is a small Python library and test runner for exercising real IPC handlers in a target app. It starts the app, sends messages over TCP or Unix sockets, and runs test cases concurrently by default.

It is named after *Be the Cowboy* by Mitski.

## Install Locally

```sh
python -m pip install -e .
```

## A Test File

```python
import be_the_cowboy as btc

app = btc.app(
    command=["cargo", "run"],
    cwd="../target-app",
    ready=btc.tcp_ready("127.0.0.1", 7878),
)
server = btc.connect("tcp://127.0.0.1:7878")


@btc.setup
async def start_app():
    await app.start()


@btc.teardown
async def stop_app():
    await app.stop()


@btc.test
async def ping_returns_pong():
    response = await server.send({"type": "ping"})

    response.expect({"type": "pong"})
    assert response.json["type"] == "pong"
```

Run it:

```sh
be-the-cowboy test tests/ipc_test.py
```

## IPC Protocol

The default codec is intentionally boring: JSON Lines. Each `send()` call opens a connection, writes one message plus `\n`, then reads one newline-delimited response. That makes concurrent tests naturally exercise parallel connection handling in the target program.

Supported URLs:

- `tcp://127.0.0.1:7878`
- `unix:///tmp/example-app/ipc.sock`

Supported codecs:

- `codec="jsonlines"` sends JSON plus `\n`
- `codec="text"` sends plain text plus `\n`
- `codec="protobuf"` sends raw protobuf bytes from a generated message class

Supported response modes:

- `response="jsonlines"` reads and parses one JSON line
- `response="text"` reads one text line
- `response="none"` writes, flushes, and closes without waiting for a reply

## Text Socket Without Responses

For apps that currently accept plain text on a Unix socket and do not write a socket response:

```python
from pathlib import Path

import be_the_cowboy as btc

SOCKET_PATH = "/tmp/example-app/ipc.sock"

app = btc.app(
    command=["cargo", "run"],
    cwd="../target-app",
    ready=lambda: Path(SOCKET_PATH).exists(),
)
server = btc.connect(
    f"unix://{SOCKET_PATH}",
    codec="text",
    response="none",
)


@btc.setup
async def start_app():
    socket = Path(SOCKET_PATH)
    if socket.exists():
        socket.unlink()
    await app.start()


@btc.teardown
async def stop_app():
    if app.process and app.process.returncode is None:
        await server.send("SHUTDOWN")
        await app.stop()
```

When the app pivots to JSON request/response, remove the transitional bits:

```python
server = btc.connect("unix:///tmp/example-app/ipc.sock")
```

## Protobuf IPC

Point `be-the-cowboy` at the directory that contains your `.proto` files, then use the generated message class as the client `message_type`:

```python
import be_the_cowboy as btc

schema = btc.protobuf("../target-app/src/protos")
Invoke = schema.message("contract.Invoke")

server = btc.connect(
    "unix:///tmp/example-app/ipc.sock",
    codec="protobuf",
    response="none",
    message_type=Invoke,
)

await server.send({"command": "PING"})
await server.send(Invoke(command="STATUS", data=b"payload"))
```

For protobuf socket responses, pass the response message type too:

```python
server = btc.connect(
    "unix:///tmp/example-app/ipc.sock",
    codec="protobuf",
    response="protobuf",
    message_type=Invoke,
    response_type=Reply,
)
```

## Runner Model

- `@btc.setup` functions run once before tests.
- `@btc.teardown` functions run once after tests.
- `@btc.test` functions run concurrently by default.
- Use `be-the-cowboy test --jobs 1 ...` for serial execution.

## API Sketch

```python
import be_the_cowboy as btc

target = btc.app(command=["cargo", "run"], cwd="../target-app")
await target.start()

server = btc.connect("tcp://127.0.0.1:7878")
response = await server.send({"op": "health"})

response.expect({"ok": True})
await target.stop()
```
