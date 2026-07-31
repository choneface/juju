import be_the_cowboy

app = be_the_cowboy.app(
    command=["cargo", "run"],
    ready=be_the_cowboy.tcp_ready("127.0.0.1", 7878),
)
server = be_the_cowboy.connect("tcp://127.0.0.1:7878")


@be_the_cowboy.setup
async def start_app():
    await app.start()


@be_the_cowboy.teardown
async def stop_app():
    await app.stop()


@be_the_cowboy.test
async def ping_returns_pong():
    response = await server.send({"type": "ping"})

    response.expect({"type": "pong"})
    assert response.json["type"] == "pong"
