import os
from pathlib import Path

import be_the_cowboy as btc

TQID_REPO = Path(os.environ["TQID_REPO"]).resolve()
SOCKET_PATH = os.environ.get("TQID_SOCKET", "/tmp/the_queen_is_dead/ipc.sock")

schema = btc.protobuf(TQID_REPO / "src" / "protos")
Invoke = schema.message("contract.Invoke")

app = btc.app(
    command=["cargo", "run"],
    cwd=TQID_REPO,
    ready=lambda: Path(SOCKET_PATH).exists(),
)
server = btc.connect(
    f"unix://{SOCKET_PATH}",
    codec="protobuf",
    response="none",
    message_type=Invoke,
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
        try:
            await server.send({"command": "SHUTDOWN"})
        except OSError:
            pass
        await app.stop()


@btc.test
async def sends_ping_invoke():
    response = await server.send({"command": "PING"})

    assert response.body is None
    await app.assert_running()


@btc.test
async def sends_status_invoke_with_payload():
    response = await server.send(Invoke(command="STATUS", data=b"happy-path"))

    assert response.body is None
    await app.assert_running()
