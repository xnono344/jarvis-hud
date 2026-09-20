"""Local WebSocket bridge talking to the frontend (see INTEGRATION.md).

One BridgeServer instance owns: the LLM provider, the conversation history,
the connected clients, and the tool-execution loop with confirmation.
"""

from __future__ import annotations

import asyncio
import base64
import itertools
import logging
import os
import subprocess
import tempfile
import uuid

log = logging.getLogger("jarvis.bridge")

try:
    from backend.brain.base import retryable
    from backend.brain.router import get_providers
    from backend.bridge import protocol
    from backend.config import config
    from backend.memory.memory import load_summary, save_summary
    from backend.permissions import (
        RiskTier,
        describe_action,
        request_confirmation,
        resolve_confirmation,
        verify_result,
    )
    from backend.plugins import PLUGINS
    from backend.skills import SKILLS
    from backend.tools.registry import TOOLS, effective_risk, get_tool_schema
except ImportError:  # pragma: no cover - direct backend/ execution fallback
    from brain.base import retryable  # type: ignore[no-redef]
    from brain.router import get_providers  # type: ignore[no-redef]
    from bridge import protocol  # type: ignore[no-redef]
    from config import config  # type: ignore[no-redef]
    from memory.memory import load_summary, save_summary  # type: ignore[no-redef]
    from permissions import (  # type: ignore[no-redef]
        RiskTier,
        describe_action,
        request_confirmation,
        resolve_confirmation,
        verify_result,
    )
    from plugins import PLUGINS  # type: ignore[no-redef]
    from skills import SKILLS  # type: ignore[no-redef]
    from tools.registry import TOOLS, effective_risk, get_tool_schema  # type: ignore[no-redef]

MAX_TOOL_ROUNDS = 5
MAX_HISTORY = 40

_call_counter = itertools.count(1)


def full_tool_schema() -> list[dict]:
    """The 12 tools plus the skill/plugin dispatchers the LLM can call."""
    schemas = get_tool_schema(config.tools_enabled)
    schemas = list(schemas)
    schemas.append(
        {
            "type": "function",
            "function": {
                "name": "run_skill",
                "description": "Run a named skill routine. Available: "
                + ", ".join(sorted(name for name in SKILLS if name in config.skills_enabled)),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill name"},
                        "text": {"type": "string", "description": "Input text (quick_note)"},
                        "days": {"type": "string", "description": "Day threshold (clean_downloads)"},
                    },
                    "required": ["name"],
                },
            },
        }
    )
    schemas.append(
        {
            "type": "function",
            "function": {
                "name": "run_plugin",
                "description": "Run a plugin action. spotify: play/pause/next/previous/current-track. "
                "github: list_notifications/list_repos/create_issue. reddit: top_posts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Plugin name (spotify/github/reddit)"},
                        "action": {"type": "string", "description": "Plugin action"},
                        "subreddit": {"type": "string", "description": "Subreddit (reddit top_posts)"},
                        "repo": {"type": "string", "description": "owner/name (github create_issue)"},
                        "title": {"type": "string", "description": "Issue title (github create_issue)"},
                        "body": {"type": "string", "description": "Issue body (github create_issue)"},
                    },
                    "required": ["name", "action"],
                },
            },
        }
    )
    return schemas


def build_system_prompt(summary: str = "") -> str:
    plugin_lines = "\n".join(f"- {name}: {mod.DESCRIPTION}" for name, mod in PLUGINS.items() if name in config.plugins_enabled)
    skill_lines = "\n".join(f"- {name}" for name in sorted(name for name in SKILLS if name in config.skills_enabled))
    prompt = (
        "You are J.A.R.V.I.S. — the Iron Man AI: a calm, formal, dry-witted "
        "British butler for the operator of this CachyOS/Hyprland (Wayland) desktop.\n\n"
        "Character rules (never break them):\n"
        "- Address the user ONLY as 'sir'. Never use any other name or title.\n"
        "- Butler cadence: 'At once, sir.', 'Certainly, sir.', 'Right away, sir.', "
        "'As you wish, sir.' Open action replies with an acknowledgement + sir.\n"
        "- Report results like status readouts: brief, precise, composed. "
        "Understated dry wit is welcome; sarcasm, slang, and chatter are not.\n"
        "- Be concise and direct. Use tools when sir asks you to do something on "
        "the system; answer from knowledge when no action is needed.\n\n"
        f"Plugins (call run_plugin with name + action):\n{plugin_lines}\n\n"
        f"Skills (call run_skill with name + params):\n{skill_lines}\n\n"
        "Destructive actions always ask sir for confirmation first — the system handles "
        "the confirmation dialog, you just call the tool and report the verified result."
    )
    if summary.strip():
        prompt += f"\n\nHere's what we last talked about: {summary.strip()}"
    return prompt


def get_system_metrics() -> tuple[int, int, int]:
    """Return (cpu %, ram %, gpu %) — same shape as the old Vite telemetry plugin."""
    import psutil

    cpu = int(psutil.cpu_percent(interval=0.2))
    ram = int(psutil.virtual_memory().percent)
    gpu = 0
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            gpu = max(0, min(100, int(out.stdout.strip().split()[0])))
    except Exception:
        gpu = 0
    return cpu, ram, gpu


class BridgeServer:
    def __init__(self):
        self.providers = get_providers()
        self.provider = self.providers[0]
        self._provider_index = 0
        self.clients: set = set()
        self.history: list[dict] = []
        self.system_prompt = build_system_prompt()
        self._summary_loaded = False
        self._turn_lock = asyncio.Lock()

    async def _ensure_summary(self):
        if self._summary_loaded:
            return
        self._summary_loaded = True
        try:
            summary = await load_summary()
        except Exception as e:
            log.warning("could not load memory summary: %s", e)
            return
        if summary:
            self.system_prompt = build_system_prompt(summary)

    def _messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.history[-MAX_HISTORY:]

    # -- connection handling -------------------------------------------------

    async def handle_client(self, websocket):
        await self._ensure_summary()
        self.clients.add(websocket)
        queue = asyncio.Queue(maxsize=8)

        async def work():
            while True:
                mtype, payload = await queue.get()
                try:
                    # The existing conversation is shared; keep whole turns ordered.
                    async with self._turn_lock:
                        start = len(self.history)
                        try:
                            if mtype == "chat:message":
                                await self.handle_chat(websocket, payload)
                            else:
                                await self.handle_audio_input(websocket, payload)
                        except asyncio.CancelledError:
                            # Never retain an incomplete tool-call/result sequence.
                            del self.history[start:]
                            self.history.append({"role": "assistant", "content": "The connection closed during a turn. Already-started actions may have completed; check their state before retrying."})
                            raise
                except Exception:
                    log.exception("client work failed")
                    await websocket.send(protocol.notification("Action failed", "Please try again.", "error"))
                finally:
                    queue.task_done()

        worker = asyncio.create_task(work())
        try:
            async for raw in websocket:
                try:
                    mtype, payload = protocol.parse_message(raw)
                except ValueError as e:
                    await websocket.send(protocol.notification("Protocol error", str(e), "error"))
                    continue
                if mtype in ("chat:message", "audio:input"):
                    try:
                        queue.put_nowait((mtype, payload))
                    except asyncio.QueueFull:
                        await websocket.send(protocol.notification("Busy", "Too many queued commands. Try again shortly.", "warning"))
                elif mtype == "tool:confirm":
                    resolve_confirmation(str(payload.get("call_id", "")), payload.get("confirmed"), owner=websocket)
                else:
                    await websocket.send(protocol.notification("Unknown message", f"ignored type {mtype!r}", "warning"))
        except Exception as e:
            log.info("client disconnected with error: %s", e)
        finally:
            self.clients.discard(websocket)
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
            if not self.clients:
                async with self._turn_lock:
                    await self._end_of_session()

    async def _end_of_session(self):
        """Save a short summary when a session with real conversation ends."""
        if len(self.history) < 2:
            return
        try:
            convo = "\n".join(f"{m.get('role')}: {str(m.get('content', ''))[:500]}" for m in self.history[-10:])
            response = await self._send_with_failover(
                [
                    {
                        "role": "user",
                        "content": "Summarize this assistant session in 2-3 sentences for next time's briefing memory:\n" + convo,
                    }
                ]
            )
            summary = (response.get("content") or "").strip()
            if summary:
                await save_summary(summary)
        except Exception as e:
            log.warning("could not save session summary: %s", e)

    # -- chat ----------------------------------------------------------------

    async def handle_chat(self, ws, payload: dict):
        prompt = str(payload.get("prompt", "")).strip()
        message_id = str(payload.get("message_id", f"m{next(_call_counter)}"))
        if not prompt:
            await ws.send(protocol.chat_response(message_id + "_resp", "Empty message — nothing to do.", "idle"))
            return

        self.history.append({"role": "user", "content": prompt})
        await ws.send(protocol.status_change("thinking"))

        try:
            reply = await self._agent_loop(ws)
        except Exception as e:
            log.exception("agent loop failed")
            reply = f"Something went wrong on my end: {e}"

        self.history.append({"role": "assistant", "content": reply})
        await ws.send(protocol.chat_response(message_id + "_resp", reply, "idle"))
        await self._speak_reply(ws, message_id + "_resp", reply)

    async def _send_with_failover(self, messages, tools=None) -> dict:
        """Try providers in order; on quota/outage advance permanently."""
        while True:
            provider = self.providers[self._provider_index]
            try:
                return await provider.send(messages, tools=tools)
            except Exception as e:
                if retryable(e) and self._provider_index < len(self.providers) - 1:
                    log.warning(
                        "provider %d failed (%s) — failing over",
                        self._provider_index,
                        str(e)[:150],
                    )
                    self._provider_index += 1
                    self.provider = self.providers[self._provider_index]
                    continue
                raise

    async def _agent_loop(self, ws) -> str:
        """Run the LLM <-> tool loop until a final answer (max MAX_TOOL_ROUNDS)."""
        schemas = full_tool_schema()
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._send_with_failover(self._messages(), tools=schemas)
            tool_calls = response.get("tool_calls") or []
            if not tool_calls:
                return response.get("content", "") or "(no response)"
            self.history.append(
                {"role": "assistant", "content": response.get("content", ""), "tool_calls": tool_calls}
            )
            for tc in tool_calls:
                result = await self.execute_call(ws, tc)
                self.history.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result})
        # One last push for a final answer without tools.
        response = await self._send_with_failover(self._messages())
        return response.get("content", "") or "(no response)"

    # -- voice ---------------------------------------------------------------

    async def _speak_reply(self, ws, message_id: str, reply: str):
        """Synthesize the reply and push audio:play. Text is already delivered;
        TTS failure only skips audio, never the answer."""
        if not config.voice_enabled or not reply.strip():
            return
        try:
            from backend.voice.speak import speak

            snippet = reply.strip()[: config.voice_reply_max_chars or 800]
            path = await speak(snippet)
            try:
                with open(path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("ascii")
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
            await ws.send(protocol.audio_play(message_id, audio_b64))
        except Exception as e:
            log.warning("TTS failed, text reply already sent: %s", e)

    async def handle_audio_input(self, ws, payload: dict):
        """Mic utterance -> transcribe -> normal chat flow."""
        message_id = str(payload.get("message_id", f"v{next(_call_counter)}"))
        audio_b64 = str(payload.get("audio", ""))
        mime = str(payload.get("mime", "audio/webm")).lower()
        if not audio_b64:
            return
        ext = ".webm" if "webm" in mime else ".mp3" if "mpeg" in mime else ".wav"
        tmp_path = None
        try:
            audio = base64.b64decode(audio_b64, validate=True)
            with tempfile.NamedTemporaryFile(prefix="jarvis-mic-", suffix=ext, delete=False) as f:
                tmp_path = f.name
                f.write(audio)
            from backend.voice.stt import transcribe

            text = (await transcribe(tmp_path)).strip()
        except Exception as e:
            log.warning("STT failed: %s", e)
            await ws.send(protocol.chat_response(message_id + "_resp", "I couldn't hear that — try again.", "idle"))
            return
        finally:
            try:
                if tmp_path is not None:
                    os.remove(tmp_path)
            except OSError:
                pass
        if not text:
            await ws.send(protocol.chat_response(message_id + "_resp", "Didn't catch that — say again?", "idle"))
            return
        await ws.send(protocol.chat_transcript(message_id, text))
        await self.handle_chat(ws, {"prompt": text, "message_id": message_id})

    # -- tool execution --------------------------------------------------------

    async def _send(self, ws, raw: str):
        await ws.send(raw)

    async def execute_call(self, ws, tc: dict) -> str:
        try:
            return await self._execute_action(ws, tc.get("name", ""), tc.get("arguments", {}) or {})
        except Exception as e:
            return f"error: {e}"

    async def _execute_action(self, ws, name: str, args: dict) -> str:
        """Single execution gate, including every nested skill action."""
        call_id = uuid.uuid4().hex
        try:
            if not isinstance(name, str) or not isinstance(args, dict):
                raise ValueError("invalid action arguments")
            if name == "run_skill":
                skill = str(args.get("name", ""))
                if skill not in config.skills_enabled:
                    raise PermissionError(f"skill {skill!r} is not enabled")
                if skill not in SKILLS:
                    raise ValueError(f"unknown skill {skill!r}")

                async def dispatch(child_name, child_args):
                    return await self._execute_action(ws, child_name, child_args)

                result = await SKILLS[skill](args, dispatch=dispatch)
            elif name == "run_plugin":
                plugin = str(args.get("name", ""))
                if plugin not in config.plugins_enabled:
                    raise PermissionError(f"plugin {plugin!r} is not enabled")
                if plugin not in PLUGINS:
                    raise ValueError(f"unknown plugin {plugin!r}")
                action = str(args.get("action", "")).strip().lower()
                if plugin == "github" and action == "create_issue":
                    await self._confirm(ws, call_id, f"Create GitHub issue in {args.get('repo')}: {args.get('title')}?")
                result = await self._run_effect(PLUGINS[plugin].execute(action, dict(args)))
            else:
                if name not in config.tools_enabled:
                    raise PermissionError(f"tool {name!r} is not enabled")
                if name not in TOOLS:
                    raise ValueError(f"unknown tool {name!r}")
                fn, _, _ = TOOLS[name]
                risk = effective_risk(name, args)
                if risk == RiskTier.DESTRUCTIVE:
                    await self._confirm(ws, call_id, describe_action(name, args))
                result = await self._run_effect(fn(args))
                if risk == RiskTier.DESTRUCTIVE:
                    ok, detail = await verify_result(name, args)
                    if not ok:
                        raise RuntimeError(f"{result}\nRe-verification failed: {detail}")
                    result = f"{result}\n({detail})"
        except Exception as e:
            await ws.send(protocol.tool_result(call_id, "", str(e)))
            raise
        await ws.send(protocol.tool_result(call_id, result))
        return result

    async def _run_effect(self, awaitable):
        # Once a side effect has begun, settle it before releasing the turn lock.
        # Cancelling communicate() alone can leave an owned subprocess running.
        effect = asyncio.create_task(awaitable)
        try:
            return await asyncio.shield(effect)
        except asyncio.CancelledError:
            try:
                await effect
            except Exception:
                log.exception("active action failed while its client disconnected")
            raise

    async def _confirm(self, ws, call_id, description):
        confirmed = await request_confirmation(ws.send, call_id, description, owner=ws)
        if not confirmed:
            raise PermissionError("Action cancelled or confirmation timed out before execution")

    async def broadcast_event(self, raw: str):
        """Push one pre-built JSON frame to every connected client."""
        for ws in list(self.clients):
            try:
                await ws.send(raw)
            except Exception:
                pass

    # -- telemetry broadcast ---------------------------------------------------

    async def broadcast_telemetry(self):
        interval = max(1, (config.telemetry_interval_ms or 2000) / 1000)
        while True:
            try:
                cpu, ram, gpu = await asyncio.to_thread(get_system_metrics)
                raw = protocol.telemetry_update(cpu, ram, gpu)
                for ws in list(self.clients):
                    try:
                        await ws.send(raw)
                    except Exception:
                        pass
            except Exception as e:
                log.warning("telemetry broadcast failed: %s", e)
            await asyncio.sleep(interval)
