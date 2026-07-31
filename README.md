# juju

`juju` is a small Python library and test runner for exercising real IPC handlers in a target app. It starts the app, sends messages over TCP or Unix sockets, and runs test cases concurrently by default.

It is named after *Juju* by Siouxsie and the Banshees.

## Install locally

```sh
python -m pip install -e .
```

## A test file

```python
import juju

app = juju.app(
    command=["cargo", "run"],
    ready=juju.tcp_ready("127.0.0.1", 7878),
)
server = juju.connect("tcp://127.0.0.1:7878")


@juju.setup
async def start_app():
    await app.start()


@juju.teardown
async def stop_app():
    await app.stop()


@juju.test
async def ping_returns_pong():
    response = await server.send({"type": "ping"})

    response.expect({"type": "pong"})
    assert response.json["type"] == "pong"
```

Run it:

```sh
juju test tests/ipc_test.py
```

## IPC protocol

The default codec is intentionally boring: JSON Lines. Each `send()` call opens a connection, writes one message plus `\n`, then reads one newline-delimited response. That makes concurrent tests naturally exercise parallel connection handling in the target program.

Supported URLs:

- `tcp://127.0.0.1:7878`
- `unix:///tmp/app.sock`

Supported codecs:

- `codec="jsonlines"` sends JSON plus `\n`
- `codec="text"` sends plain text plus `\n`

Supported response modes:

- `response="jsonlines"` reads and parses one JSON line
- `response="text"` reads one text line
- `response="none"` writes, flushes, and closes without waiting for a reply

## Current tqid shape

Today `tqid` accepts a plain text line on a Unix socket and does not write a socket response. That works like this:

```python
import juju

app = juju.app(
    command=["cargo", "run"],
    cwd="/Users/gavingarcia/Desktop/repos/tqid",
    ready=juju.unix_ready("/run/the_queen_is_dead/ipc.sock"),
)
server = juju.connect(
    "unix:///run/the_queen_is_dead/ipc.sock",
    codec="text",
    response="none",
)


@juju.setup
async def start_app():
    await app.start()


@juju.teardown
async def stop_app():
    await server.send("SHUTDOWN")
    await app.stop()
```

When `tqid` pivots to JSON request/response, remove the transitional bits:

```python
server = juju.connect("unix:///run/the_queen_is_dead/ipc.sock")
```

## Runner model

- `@juju.setup` functions run once before tests.
- `@juju.teardown` functions run once after tests.
- `@juju.test` functions run concurrently by default.
- Use `juju test --jobs 1 ...` for serial execution.

## API sketch

```python
target = juju.app(command=["cargo", "run"], cwd="../my-rust-app")
await target.start()

server = juju.connect("tcp://127.0.0.1:7878")
response = await server.send({"op": "health"})

response.expect({"ok": True})
await target.stop()
```
