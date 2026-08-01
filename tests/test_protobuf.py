import asyncio
import tempfile
import unittest
from pathlib import Path

import be_the_cowboy as btc


class ProtobufTests(unittest.IsolatedAsyncioTestCase):
    async def test_generates_message_class_and_sends_protobuf_bytes(self):
        root = Path(__file__).resolve().parent / "fixtures" / "protos"
        schema = btc.protobuf(root)
        Invoke = schema.message("contract.Invoke")
        received = []
        handled = asyncio.Event()

        async def handle(reader, writer):
            raw = await reader.read()
            received.append(Invoke.FromString(raw))
            handled.set()
            writer.close()
            await writer.wait_closed()

        with tempfile.TemporaryDirectory() as tmp:
            socket_path = Path(tmp) / "ipc.sock"
            server = await asyncio.start_unix_server(handle, path=socket_path)
            try:
                client = btc.connect(
                    f"unix://{socket_path}",
                    codec="protobuf",
                    response="none",
                    message_type=Invoke,
                )

                response = await client.send({"command": "PING", "data": b"payload"})
                await asyncio.wait_for(handled.wait(), timeout=1.0)

                self.assertIsNone(response.body)
                self.assertEqual(received[0].command, "PING")
                self.assertEqual(received[0].data, b"payload")
            finally:
                server.close()
                await server.wait_closed()

    async def test_can_send_existing_message_instance(self):
        root = Path(__file__).resolve().parent / "fixtures" / "protos"
        schema = btc.protobuf(root)
        Invoke = schema.message("Invoke")
        received = []
        handled = asyncio.Event()

        async def handle(reader, writer):
            received.append(Invoke.FromString(await reader.read()))
            handled.set()
            writer.close()
            await writer.wait_closed()

        with tempfile.TemporaryDirectory() as tmp:
            socket_path = Path(tmp) / "ipc.sock"
            server = await asyncio.start_unix_server(handle, path=socket_path)
            try:
                client = btc.connect(f"unix://{socket_path}", codec="protobuf", response="none")

                await client.send(Invoke(command="STATUS"))
                await asyncio.wait_for(handled.wait(), timeout=1.0)

                self.assertEqual(received[0].command, "STATUS")
            finally:
                server.close()
                await server.wait_closed()

    async def test_can_read_protobuf_response(self):
        root = Path(__file__).resolve().parent / "fixtures" / "protos"
        schema = btc.protobuf(root)
        Invoke = schema.message("contract.Invoke")

        async def handle(reader, writer):
            Invoke.FromString(await reader.read(1024))
            writer.write(Invoke(command="PONG", data=b"ok").SerializeToString())
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        with tempfile.TemporaryDirectory() as tmp:
            socket_path = Path(tmp) / "ipc.sock"
            server = await asyncio.start_unix_server(handle, path=socket_path)
            try:
                client = btc.connect(
                    f"unix://{socket_path}",
                    codec="protobuf",
                    response="protobuf",
                    message_type=Invoke,
                    response_type=Invoke,
                )

                response = await client.send({"command": "PING"})

                self.assertEqual(response.body.command, "PONG")
                self.assertEqual(response.body.data, b"ok")
            finally:
                server.close()
                await server.wait_closed()
