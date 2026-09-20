import unittest
from unittest.mock import AsyncMock
from aiohttp.test_utils import TestClient, TestServer
from backend.http_server import create_app


class LocalHTTP(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app(broadcast=AsyncMock())))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)
        self.headers = {'Host': '127.0.0.1:8766'}

    async def test_mic_requires_credential(self):
        response = await self.client.post('/api/mic', headers=self.headers)
        self.assertEqual(response.status, 401)

    async def test_untrusted_origin_is_rejected(self):
        response = await self.client.post('/api/mic', headers={**self.headers, 'Origin': 'https://attacker.example'})
        self.assertEqual(response.status, 403)

    async def test_untrusted_host_is_rejected(self):
        response = await self.client.get('/api/health', headers={'Host': 'attacker.example:8766'})
        self.assertEqual(response.status, 403)

    async def test_local_bootstrap_then_authenticated_mic(self):
        response = await self.client.get('/api/session', headers=self.headers)
        self.assertEqual(response.status, 200)
        data = await response.json()
        self.assertGreater(len(data['token']), 30)
        response = await self.client.post('/api/mic', headers={**self.headers, 'Authorization': 'Bearer ' + data['token']})
        self.assertEqual(response.status, 200)

    async def test_cross_site_bootstrap_is_rejected(self):
        response = await self.client.get('/api/session', headers={**self.headers, 'Sec-Fetch-Site': 'cross-site'})
        self.assertEqual(response.status, 403)

class WebSocketAccess(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from backend.security import LocalAccess
        from websockets.asyncio.server import serve
        self.access = LocalAccess()
        async def echo(ws):
            async for message in ws:
                await ws.send(message)
        self.server = await serve(echo, '127.0.0.1', 0, process_request=self.access.process_ws_request, subprotocols=['jarvis'])
        port = self.server.sockets[0].getsockname()[1]
        self.access.ws_hosts = {f'127.0.0.1:{port}'}
        self.url = f'ws://127.0.0.1:{port}/ws'
        self.addAsyncCleanup(self.close_server)

    async def close_server(self):
        self.server.close()
        await self.server.wait_closed()

    async def test_valid_browser_credential_connects(self):
        from websockets.asyncio.client import connect
        async with connect(self.url, origin='http://127.0.0.1:8766', subprotocols=['jarvis', self.access.token]) as ws:
            await ws.send('authenticated')
            self.assertEqual(await ws.recv(), 'authenticated')
            self.assertEqual(ws.subprotocol, 'jarvis')

    async def test_missing_credential_rejected(self):
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus
        with self.assertRaises(InvalidStatus) as caught:
            async with connect(self.url, origin='http://127.0.0.1:8766'):
                self.fail('unauthenticated connection accepted')
        self.assertEqual(caught.exception.response.status_code, 401)

    async def test_wrong_credential_rejected(self):
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus
        with self.assertRaises(InvalidStatus) as caught:
            async with connect(self.url, subprotocols=['jarvis', 'wrong-token']):
                self.fail('wrong credential accepted')
        self.assertEqual(caught.exception.response.status_code, 401)

    async def test_foreign_origin_rejected_even_with_credential(self):
        from websockets.asyncio.client import connect
        from websockets.exceptions import InvalidStatus
        with self.assertRaises(InvalidStatus) as caught:
            async with connect(self.url, origin='https://attacker.example', subprotocols=['jarvis', self.access.token]):
                self.fail('foreign origin accepted')
        self.assertEqual(caught.exception.response.status_code, 403)


class DesktopPermissions(unittest.TestCase):
    def test_only_trusted_audio_and_notifications_are_granted(self):
        from backend.security import grant_local_permission
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineCore import QWebEnginePermission
        from unittest.mock import Mock
        Kind = QWebEnginePermission.PermissionType
        for origin, kind, granted in [
            ('http://127.0.0.1:8766', Kind.MediaAudioCapture, True),
            ('http://127.0.0.1:8766', Kind.Notifications, True),
            ('https://attacker.example', Kind.MediaAudioCapture, False),
            ('http://127.0.0.1:5173', Kind.MediaAudioCapture, False),
            ('http://127.0.0.1:8766', Kind.MediaVideoCapture, False),
            ('http://127.0.0.1:8766', Kind.DesktopAudioVideoCapture, False),
        ]:
            with self.subTest(origin=origin, kind=kind):
                permission = Mock()
                permission.origin.return_value = QUrl(origin)
                permission.permissionType.return_value = kind
                grant_local_permission(permission, 'http://127.0.0.1:8766')
                self.assertEqual(permission.grant.call_count, int(granted))
                self.assertEqual(permission.deny.call_count, int(not granted))


if __name__ == '__main__':
    unittest.main()
