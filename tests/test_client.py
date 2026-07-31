import asyncio
import tempfile
import unittest
from pathlib import Path

import juju


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.received = []

        async def handle(reader, writer):
            raw = await reader.readline()
            self.received.append(raw)
            writer.write(b'{"ok":true,"echo":"pong"}\n')
            await writer.drain()
            writer.close()
            await writer.wait_closed()

        self.server = await asyncio.start_server(handle, "127.0.0.1", 0)
        sock = self.server.sockets[0]
        self.url = f"tcp://127.0.0.1:{sock.getsockname()[1]}"

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_send_jsonlines_message(self):
        client = juju.connect(self.url)

        response = await client.send({"type": "ping"})

        response.expect({"ok": True})
        self.assertEqual(response.json["echo"], "pong")
        self.assertEqual(self.received, [b'{"type":"ping"}\n'])

    async def test_send_text_without_waiting_for_response(self):
        client = juju.connect(self.url, codec="text", response="none")

        response = await client.send("SHUTDOWN")

        self.assertIsNone(response.body)
        self.assertEqual(response.raw, b"")
        self.assertEqual(self.received, [b"SHUTDOWN\n"])


class ResponseTests(unittest.TestCase):
    def test_expect_reports_field_mismatches(self):
        response = juju.Response({"ok": False}, b'{"ok":false}\n')

        with self.assertRaises(AssertionError):
            response.expect({"ok": True})


class UnixSocketClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_text_without_response_over_unix_socket(self):
        received = []

        async def handle(reader, writer):
            received.append(await reader.readline())
            writer.close()
            await writer.wait_closed()

        with tempfile.TemporaryDirectory() as tmp:
            socket_path = Path(tmp) / "ipc.sock"
            server = await asyncio.start_unix_server(handle, path=socket_path)
            try:
                client = juju.connect(f"unix://{socket_path}", codec="text", response="none")

                response = await client.send("SHUTDOWN")

                self.assertIsNone(response.body)
                self.assertEqual(received, [b"SHUTDOWN\n"])
            finally:
                server.close()
                await server.wait_closed()
