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
