import asyncio
import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from backend.bridge.server import BridgeServer
from backend.config import config
from backend import permissions
from backend.tools.filesystem import delete_file
from backend.tools.system import open_application


class Socket:
    def __init__(self, prompt='test', approve=True):
        self.incoming = asyncio.Queue()
        self.incoming.put_nowait(json.dumps({'type': 'chat:message', 'payload': {'prompt': prompt}}))
        self.sent = []
        self.approve = approve

    def __aiter__(self):
        return self

    async def __anext__(self):
        raw = await self.incoming.get()
        if raw is None:
            raise StopAsyncIteration
        return raw

    async def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        if msg['type'] == 'tool:call':
            self.incoming.put_nowait(json.dumps({'type': 'tool:confirm', 'payload': {
                'call_id': msg['payload']['call_id'], 'confirmed': self.approve}}))
        if msg['type'] == 'chat:response':
            self.incoming.put_nowait(None)


class ReviewFixes(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='jarvis-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.provider = AsyncMock()
        with patch('backend.bridge.server.get_providers', return_value=[self.provider]):
            self.bridge = BridgeServer()
        self.bridge._summary_loaded = True
        self.bridge._end_of_session = AsyncMock()
        self.enterContext(patch.object(config, 'voice_enabled', False))

    async def test_approval_is_read_while_tool_waits(self):
        target = self.root / 'delete-me'
        target.write_text('fixture')
        self.provider.send.side_effect = [
            {'tool_calls': [{'id': 'model-call', 'name': 'delete_file', 'arguments': {'path': str(target)}}]},
            {'content': 'finished'},
        ]
        with patch.object(permissions, 'CONFIRM_TIMEOUT_S', .05):
            await asyncio.wait_for(self.bridge.handle_client(Socket()), 1)
        self.assertFalse(target.exists(), 'approved action was never executed')

    async def test_disabled_tool_cannot_write(self):
        target = self.root / 'blocked'
        with patch.object(config, 'tools_enabled', ['notify']):
            result = await self.bridge.execute_call(Socket(), {'name': 'write_file', 'arguments': {'path': str(target), 'content': 'bad'}})
        self.assertFalse(target.exists())
        self.assertIn('not enabled', result)

    async def test_disabled_skill_cannot_write(self):
        target = self.root / 'notes'
        with patch.object(config, 'skills_enabled', []), patch.object(config, 'notes_file', str(target)):
            result = await self.bridge.execute_call(Socket(), {'name': 'run_skill', 'arguments': {'name': 'quick_note', 'text': 'bad'}})
        self.assertFalse(target.exists())
        self.assertIn('not enabled', result)

    async def test_skill_cannot_bypass_disabled_write_tool(self):
        target = self.root / 'notes'
        with patch.object(config, 'tools_enabled', []), patch.object(config, 'notes_file', str(target)):
            result = await self.bridge.execute_call(Socket(), {'name': 'run_skill', 'arguments': {'name': 'quick_note', 'text': 'bad'}})
        self.assertFalse(target.exists())
        self.assertIn('not enabled', result)

    async def test_application_rejects_arbitrary_command(self):
        with patch('backend.tools.system._run', new=AsyncMock(return_value=(0, 'ok'))):
            with self.assertRaises((ValueError, PermissionError)):
                await open_application({'name': 'sh -c "touch /tmp/should-not-run"'})

    async def test_delete_link_preserves_target(self):
        target = self.root / 'real'
        target.write_text('keep')
        link = self.root / 'link'
        link.symlink_to(target)
        await delete_file({'path': str(link)})
        self.assertTrue(target.exists())
        self.assertFalse(os.path.lexists(link))

    async def test_audio_ignores_client_filename_and_cleans_up(self):
        observed = []
        async def transcribe(path):
            observed.append(Path(path))
            self.assertEqual(Path(path).read_bytes(), b'audio')
            return 'hello'
        with patch('backend.voice.stt.transcribe', new=transcribe), patch.object(self.bridge, 'handle_chat', new=AsyncMock()):
            await self.bridge.handle_audio_input(Socket(), {
                'message_id': '../../untrusted/upload', 'audio': base64.b64encode(b'audio').decode(), 'mime': 'audio/webm'})
        self.assertEqual(len(observed), 1, 'client filename prevented secure upload')
        self.assertFalse(observed[0].exists())

    async def test_denial_preserves_file(self):
        target = self.root / 'keep'
        target.write_text('keep')
        self.provider.send.side_effect = [
            {'tool_calls': [{'id': 'same-id', 'name': 'delete_file', 'arguments': {'path': str(target)}}]},
            {'content': 'cancelled'},
        ]
        await asyncio.wait_for(self.bridge.handle_client(Socket(approve=False)), 1)
        self.assertEqual(target.read_text(), 'keep')

    async def test_disconnect_cancels_pending_confirmation(self):
        target = self.root / 'keep'
        target.write_text('keep')
        self.provider.send.return_value = {'tool_calls': [{'name': 'delete_file', 'arguments': {'path': str(target)}}]}
        class Disconnect(Socket):
            async def send(self, raw):
                if json.loads(raw)['type'] == 'tool:call':
                    self.incoming.put_nowait(None)
        await asyncio.wait_for(self.bridge.handle_client(Disconnect()), 1)
        self.assertTrue(target.exists())
        self.assertFalse(permissions._pending)

    async def test_confirmations_are_owned_and_strict_booleans(self):
        owner, stranger = object(), object()
        ready = asyncio.Event()
        async def send(raw):
            ready.set()
        task = asyncio.create_task(permissions.request_confirmation(send, 'same-id', 'test', owner=owner))
        await ready.wait()
        self.assertFalse(permissions.resolve_confirmation('same-id', True, owner=stranger))
        self.assertFalse(permissions.resolve_confirmation('same-id', 'false', owner=owner))
        self.assertFalse(task.done())
        self.assertTrue(permissions.resolve_confirmation('same-id', False, owner=owner))
        self.assertFalse(await task)

    async def test_confirmation_timeout_denies(self):
        with patch.object(permissions, 'CONFIRM_TIMEOUT_S', .01), self.assertLogs('jarvis.permissions', level='WARNING'):
            self.assertFalse(await permissions.request_confirmation(AsyncMock(), 'timeout', 'test'))
        self.assertFalse(permissions._pending)

    async def test_nested_recap_obeys_plugin_disablement(self):
        with patch.object(config, 'plugins_enabled', []), patch('backend.memory.memory.load_summary', new=AsyncMock(return_value='')):
            result = await self.bridge.execute_call(Socket(), {'name': 'run_skill', 'arguments': {'name': 'daily_recap'}})
        self.assertIn("plugin 'github' is not enabled", result)
        self.assertIn("plugin 'spotify' is not enabled", result)

    async def test_enabled_nested_note_still_works(self):
        target = self.root / 'notes'
        with patch.object(config, 'notes_file', str(target)):
            await self.bridge.execute_call(Socket(), {'name': 'run_skill', 'arguments': {'name': 'quick_note', 'text': 'remember'}})
        self.assertIn('remember', target.read_text())

    async def test_delete_dangling_link(self):
        link = self.root / 'dangling'
        link.symlink_to(self.root / 'missing')
        await delete_file({'path': str(link)})
        self.assertFalse(os.path.lexists(link))

    async def test_approved_application_launches_without_arguments(self):
        with patch.object(config, 'applications_allowed', ['firefox']), patch('backend.tools.system._run', new=AsyncMock(return_value=(0, 'ok'))) as run:
            result = await open_application({'name': 'firefox'})
        self.assertIn('launched: firefox', result)
        run.assert_awaited_once_with('hyprctl', 'dispatch', 'exec', 'firefox')

    async def test_shared_conversation_turns_are_serialized(self):
        started = asyncio.Event()
        release = asyncio.Event()
        seen = []
        async def chat(ws, payload):
            seen.append(payload['prompt'])
            if payload['prompt'] == 'first':
                started.set()
                await release.wait()
            await ws.send(json.dumps({'type': 'chat:response'}))
        self.bridge.handle_chat = chat
        first = asyncio.create_task(self.bridge.handle_client(Socket('first')))
        await started.wait()
        second = asyncio.create_task(self.bridge.handle_client(Socket('second')))
        await asyncio.sleep(.01)
        self.assertEqual(seen, ['first'])
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 1)
        self.assertEqual(seen, ['first', 'second'])

    async def test_padded_power_action_still_requires_approval(self):
        class DenyingSocket(Socket):
            async def send(self, raw):
                msg = json.loads(raw)
                self.sent.append(msg)
                if msg['type'] == 'tool:call':
                    permissions.resolve_confirmation(msg['payload']['call_id'], False, owner=self)
        ws = DenyingSocket()
        with patch('backend.tools.system._run', new=AsyncMock(return_value=(0, 'ok'))) as run:
            result = await self.bridge.execute_call(ws, {'name': 'system_control', 'arguments': {'action': ' shutdown '}})
        self.assertIn('cancelled', result.lower())
        run.assert_not_awaited()

    async def test_delete_resolves_symlink_parents_before_dotdot(self):
        nested = self.root / 'nested'
        (nested / 'dir').mkdir(parents=True)
        (nested / 'victim').write_text('delete')
        (self.root / 'victim').write_text('keep')
        (self.root / 'link').symlink_to(nested / 'dir')
        await delete_file({'path': str(self.root / 'link' / '..' / 'victim')})
        self.assertTrue((self.root / 'victim').exists(), 'unrelated file was deleted')
        self.assertEqual((self.root / 'victim').read_text(), 'keep')
        self.assertFalse((nested / 'victim').exists())

    async def test_disconnect_drains_started_effect_before_releasing_turn(self):
        from backend.tools.registry import TOOLS
        started, release, completed = asyncio.Event(), asyncio.Event(), asyncio.Event()
        async def effect(args):
            started.set()
            await release.wait()
            completed.set()
            return 'done'
        self.provider.send.return_value = {'tool_calls': [{'name': 'notify', 'arguments': {'message': 'test'}}]}
        ws = Socket()
        with patch.dict(TOOLS, {'notify': (effect, permissions.RiskTier.SAFE, {})}):
            client = asyncio.create_task(self.bridge.handle_client(ws))
            await started.wait()
            ws.incoming.put_nowait(None)
            await asyncio.sleep(.01)
            try:
                self.assertFalse(client.done(), 'disconnect abandoned an active effect')
                self.assertTrue(self.bridge._turn_lock.locked())
            finally:
                release.set()
                await asyncio.wait_for(client, 1)
            self.assertTrue(completed.is_set())


if __name__ == '__main__':
    unittest.main()
