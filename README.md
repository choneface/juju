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

The first codec is intentionally boring: JSON Lines. Each `send()` call opens a connection, writes one JSON document plus `\n`, then reads one newline-delimited response. That makes concurrent tests naturally exercise parallel connection handling in the target program.

Supported URLs:

- `tcp://127.0.0.1:7878`
- `unix:///tmp/app.sock`

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
