from pathlib import Path

import be_the_cowboy

SOCKET_PATH = "/tmp/example-app/ipc.sock"
SOCKET = f"unix://{SOCKET_PATH}"

app = be_the_cowboy.app(
    command=["cargo", "run"],
    cwd="../target-app",
    ready=lambda: Path(SOCKET_PATH).exists(),
)
server = be_the_cowboy.connect(SOCKET, codec="text", response="none")


@be_the_cowboy.setup
async def start_app():
    socket = Path(SOCKET_PATH)
    if socket.exists():
        socket.unlink()
    await app.start()


@be_the_cowboy.teardown
async def stop_app():
    if app.process and app.process.returncode is None:
        await server.send("SHUTDOWN")
        await app.stop()


@be_the_cowboy.test
async def sends_ping_line_to_target():
    response = await server.send("PING")

    assert response.body is None


@be_the_cowboy.test
async def sends_status_line_to_target():
    response = await server.send("STATUS")

    assert response.body is None


@be_the_cowboy.test
async def sends_lowercase_text_line_to_target():
    response = await server.send("hello from be-the-cowboy")

    assert response.body is None


@be_the_cowboy.test
async def sends_structured_text_for_future_jsonish_shape():
    response = await server.send("event=ping id=42")

    assert response.body is None
