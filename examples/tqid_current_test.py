import juju

SOCKET = "unix:///run/the_queen_is_dead/ipc.sock"

app = juju.app(
    command=["cargo", "run"],
    cwd="/Users/gavingarcia/Desktop/repos/tqid",
    ready=juju.unix_ready("/run/the_queen_is_dead/ipc.sock"),
)
server = juju.connect(SOCKET, codec="text", response="none")


@juju.setup
async def start_app():
    await app.start()


@juju.teardown
async def stop_app():
    await server.send("SHUTDOWN")
    await app.stop()


@juju.test
async def sends_plain_text_line_to_tqid():
    response = await server.send("PING")

    assert response.body is None
