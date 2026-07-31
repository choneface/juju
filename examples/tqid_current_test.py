from pathlib import Path

import juju

SOCKET_PATH = "/tmp/the_queen_is_dead/ipc.sock"
SOCKET = f"unix://{SOCKET_PATH}"

app = juju.app(
    command=["cargo", "run"],
    cwd="/Users/gavingarcia/Desktop/repos/tqid",
    ready=lambda: Path(SOCKET_PATH).exists(),
)
server = juju.connect(SOCKET, codec="text", response="none")


@juju.setup
async def start_app():
    socket = Path(SOCKET_PATH)
    if socket.exists():
        socket.unlink()
    await app.start()


@juju.teardown
async def stop_app():
    if app.process and app.process.returncode is None:
        await server.send("SHUTDOWN")
        await app.stop()


@juju.test
async def sends_ping_line_to_tqid():
    response = await server.send("PING")

    assert response.body is None


@juju.test
async def sends_status_line_to_tqid():
    response = await server.send("STATUS")

    assert response.body is None


@juju.test
async def sends_lowercase_text_line_to_tqid():
    response = await server.send("hello from juju")

    assert response.body is None


@juju.test
async def sends_structured_text_for_future_jsonish_shape():
    response = await server.send("event=ping id=42")

    assert response.body is None
