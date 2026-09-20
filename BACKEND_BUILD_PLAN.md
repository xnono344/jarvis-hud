# JARVIS Backend Build Plan

> **Based on INTEGRATION.md analysis of existing frontend**
> **Frontend path: `<project-root>`**
> **Backend path: `<project-root>/backend`**

---

## Architecture Overview

```
backend/
├── main.py                 # Entrypoint: loads config, starts bridge + HTTP server
├── config.py               # Single source of truth: .env + config.toml
├── .env.example            # Template for environment variables
├── config.toml             # Non-secret configuration
├── bridge/
│   ├── __init__.py
│   ├── server.py           # WebSocket server (asyncio/websockets)
│   └── protocol.py         # Message types, serialization, validation
├── brain/
│   ├── __init__.py
│   ├── router.py           # Picks provider based on config
│   ├── base.py             # Shared interface: send(messages, tools) -> response
│   ├── gemini_provider.py  # Google Gemini API
│   └── universal_provider.py  # OpenAI-compatible (NVIDIA NIM, Kilo, OpenRouter)
├── memory/
│   ├── __init__.py
│   ├── memory.py           # save_summary() / load_summary()
│   └── memory.json         # Persistent file (or SQLite)
├── permissions.py          # Risk tiers + confirmation flow logic
├── tools/
│   ├── __init__.py
│   ├── registry.py         # Registers 12 tools + risk tiers
│   ├── filesystem.py       # read_file, write_file, delete_file, list_directory
│   ├── shell.py            # run_shell_command
│   ├── system.py           # open_application, kill_process, system_control
│   ├── window.py           # window_management (hyprctl dispatch)
│   ├── clipboard.py        # clipboard (wl-copy/wl-paste)
│   ├── notify.py           # notify (notify-send)
│   └── web.py              # web_search
├── plugins/
│   ├── __init__.py
│   ├── base.py             # Plugin interface: NAME, DESCRIPTION, execute(action, params)
│   ├── spotify_plugin.py   # playerctl (MPRIS)
│   ├── github_plugin.py    # GitHub API (PAT)
│   └── reddit_plugin.py    # Reddit public JSON endpoints
├── skills/
│   ├── __init__.py
│   ├── skills.py           # 5 skills: system_status, focus_mode, quick_note, clean_downloads, daily_recap
│   └── skills_registry.py  # Maps skill name -> function
└── http_server.py          # aiohttp/FastAPI for /api/telemetry, /api/health, static files (prod)
```

---

## Step-by-Step Implementation Plan

### Phase 0: Project Setup & Config (Day 1)

#### 0.1 Create backend directory structure
```bash
mkdir -p backend/{bridge,brain,memory,tools,plugins,skills}
touch backend/{bridge,brain,memory,tools,plugins,skills}/__init__.py
```

#### 0.2 Create config.py + .env.example + config.toml

**config.py** - Single config loader:
```python
# Loads .env (secrets) + config.toml (non-secrets)
# Provides: Config class with all settings as attributes
# Validates required fields on startup
```

**.env.example**:
```
# LLM Provider: "gemini" or "universal"
LLM_PROVIDER=gemini

# Gemini
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-1.5-pro

# Universal (OpenAI-compatible)
UNIVERSAL_BASE_URL=https://api.openai.com/v1
UNIVERSAL_API_KEY=your-key-here
UNIVERSAL_MODEL=gpt-4o

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8765
WS_PATH=/ws

# Memory
MEMORY_FILE=backend/memory/memory.json

# Plugins
GITHUB_TOKEN=ghp_xxx
SPOTIFY_PLAYERCTL=playerctl
```

**config.toml**:
```toml
[backend]
host = "0.0.0.0"
port = 8765
ws_path = "/ws"

[telemetry]
update_interval_ms = 2000

[tools]
enabled = ["read_file", "write_file", "delete_file", "list_directory", "run_shell_command", "open_application", "kill_process", "system_control", "window_management", "clipboard", "notify", "web_search"]

[plugins]
enabled = ["spotify", "github", "reddit"]

[skills]
enabled = ["system_status", "focus_mode", "quick_note", "clean_downloads", "daily_recap"]
```

---

### Phase 1: Brain / LLM Layer (Day 1-2)

#### 1.1 brain/base.py - Shared Interface
```python
from abc import ABC, abstractmethod
from typing import Any

class LLMProvider(ABC):
    @abstractmethod
    async def send(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Returns: {content: str, tool_calls: list[dict] | None}"""
        pass
```

#### 1.2 brain/gemini_provider.py
- Use `google-generativeai` package
- Implement `send()` with tool calling support
- Handle API key from config

#### 1.3 brain/universal_provider.py
- Use `openai` package (works with any OpenAI-compatible endpoint)
- Base URL, API key, model from config
- Same interface as Gemini

#### 1.4 brain/router.py
```python
def get_provider() -> LLMProvider:
    if config.LLM_PROVIDER == "gemini":
        return GeminiProvider()
    return UniversalProvider()
```

#### 1.5 Test: Plain text round-trip
```bash
cd backend && python -c "from brain.router import get_provider; import asyncio; p = get_provider(); print(asyncio.run(p.send([{'role': 'user', 'content': 'Hello'}])))"
```

---

### Phase 2: Permissions + Confirmation Flow (Day 2)

#### 2.1 permissions.py
```python
from enum import Enum

class RiskTier(Enum):
    SAFE = "safe"
    RISKY = "risky"
    DESTRUCTIVE = "destructive"

TOOL_RISK = {
    "read_file": RiskTier.SAFE,
    "list_directory": RiskTier.SAFE,
    "web_search": RiskTier.SAFE,
    "notify": RiskTier.SAFE,
    "clipboard_read": RiskTier.SAFE,
    "write_file": RiskTier.RISKY,
    "open_application": RiskTier.RISKY,
    "window_management": RiskTier.RISKY,
    "clipboard_write": RiskTier.RISKY,
    "system_control": RiskTier.RISKY,  # except shutdown/reboot
    "delete_file": RiskTier.DESTRUCTIVE,
    "run_shell_command": RiskTier.DESTRUCTIVE,
    "kill_process": RiskTier.DESTRUCTIVE,
    "system_control_shutdown": RiskTier.DESTRUCTIVE,
    "system_control_reboot": RiskTier.DESTRUCTIVE,
}

async def confirm_destructive(bridge, call_id: str, description: str) -> bool:
    """Send tool:call to frontend, wait for tool:confirm, return confirmed"""
    pass

async def verify_result(tool_name: str, params: dict, expected_outcome: str) -> bool:
    """Re-verify action succeeded (e.g., file actually deleted, process actually dead)"""
    pass
```

#### 2.2 Test with fake destructive tool
Create a test tool that "deletes" a temp file, verify confirmation flow works end-to-end.

---

### Phase 3: Tools Implementation (Day 2-3)

All tools follow pattern: `async def tool_name(params: dict) -> str` with docstring as LLM description.

#### 3.1 tools/filesystem.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `read_file(path)` | SAFE | `aiofiles.open(path).read()` |
| `write_file(path, content)` | RISKY | `aiofiles.open(path, 'w').write(content)` |
| `delete_file(path)` | DESTRUCTIVE | `os.remove(path)` + verify gone |
| `list_directory(path)` | SAFE | `os.listdir(path)` + stats |

#### 3.2 tools/shell.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `run_shell_command(cmd)` | DESTRUCTIVE | `asyncio.create_subprocess_shell()` with timeout, capture stdout/stderr |

#### 3.3 tools/system.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `open_application(name)` | RISKY | `hyprctl dispatch exec [name]` |
| `kill_process(name_or_pid)` | DESTRUCTIVE | `pkill` or `kill -9` + verify via `pgrep` |
| `system_control(action)` | RISKY/DESTRUCTIVE | `wpctl` (volume/brightness), `hyprctl dispatch exit` (lock), `systemctl poweroff/reboot` (destructive) |

#### 3.4 tools/window.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `window_management(action)` | RISKY | `hyprctl dispatch [focuswindow/movewindow/resizewindow/workspace]` |

#### 3.5 tools/clipboard.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `clipboard(action, content?)` | SAFE/RISKY | `wl-paste` (read), `wl-copy` (write) |

#### 3.6 tools/notify.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `notify(title, message)` | SAFE | `notify-send` |

#### 3.7 tools/web.py
| Tool | Risk | Implementation |
|------|------|----------------|
| `web_search(query)` | SAFE | `requests` to DuckDuckGo HTML or use `ddgs` package |

#### 3.8 tools/registry.py
```python
TOOLS = {
    "read_file": (read_file, RiskTier.SAFE, "Read a file from disk"),
    "write_file": (write_file, RiskTier.RISKY, "Write content to a file"),
    # ... all 12 tools
}

def get_tool_schema() -> list[dict]:
    """Return OpenAI/Gemini function calling schema for all tools"""
    pass
```

---

### Phase 4: Memory (Day 3)

#### 4.1 memory/memory.py
```python
MEMORY_FILE = Path("backend/memory/memory.json")

async def load_summary() -> str:
    if MEMORY_FILE.exists():
        data = json.loads(MEMORY_FILE.read_text())
        return data.get("summary", "")
    return ""

async def save_summary(summary: str):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_FILE.write_text(json.dumps({"summary": summary, "updated": time.time()}))
```

#### 4.2 Integration with Brain
- On startup: `summary = await load_summary()` prepend to system prompt
- On session end: Generate summary from conversation `await save_summary(summary)`
- Summary format: "Last session: User asked about X, we did Y, outcome Z."

---

### Phase 5: Plugins (Day 3-4)

#### 5.1 plugins/base.py
```python
from typing import Protocol

class Plugin(Protocol):
    NAME: str
    DESCRIPTION: str
    async def execute(self, action: str, params: dict) -> str: ...
```

#### 5.2 plugins/spotify_plugin.py
- Uses `playerctl` (MPRIS) - no API key needed
- Actions: `play`, `pause`, `next`, `previous`, `current-track`
- `playerctl -p spotify play/pause/next/previous metadata`

#### 5.3 plugins/github_plugin.py
- Uses `httpx` + GitHub REST API
- Requires `GITHUB_TOKEN` (PAT with `notifications`, `repo` scopes)
- Actions: `list_notifications`, `list_repos`, `create_issue`

#### 5.4 plugins/reddit_plugin.py
- Uses `httpx` to public JSON endpoints (no auth)
- Actions: `top_posts(subreddit, limit=10)`
- Endpoint: `https://www.reddit.com/r/{subreddit}/top.json?limit={limit}`

#### 5.5 plugins/__init__.py
```python
PLUGINS = {
    "spotify": SpotifyPlugin(),
    "github": GitHubPlugin(),
    "reddit": RedditPlugin(),
}
```

---

### Phase 6: Skills (Day 4)

#### 6.1 skills/skills.py
Each skill = async function chaining tool calls.

```python
async def system_status() -> str:
    cpu = await read_file("/proc/stat")  # or use tools
    ram = await read_file("/proc/meminfo")
    # Format nice response
    return f"CPU: {cpu}%\nRAM: {ram}%\nBattery: {await get_battery()}%"

async def focus_mode() -> str:
    await notify("Focus Mode", "Notifications muted")
    windows = await window_management("list")
    return f"Focus mode active. Open windows: {windows}"

async def quick_note(text: str) -> str:
    notes_file = Path.home() / "notes.txt"
    await write_file(notes_file, f"[{datetime.now()}] {text}\n", append=True)
    return "Note saved."

async def clean_downloads(days: int = 30) -> str:
    # List files older than N days in ~/Downloads
    # For each: request confirmation via permissions.confirm_destructive()
    # If confirmed: delete + verify
    pass

async def daily_recap() -> str:
    memory = await load_summary()
    github_notifs = await github_plugin.execute("list_notifications", {})
    spotify = await spotify_plugin.execute("current-track", {})
    return f"Recap:\n{memory}\n\nGitHub: {github_notifs}\n\nNow Playing: {spotify}"
```

#### 6.2 skills/skills_registry.py
```python
SKILLS = {
    "system_status": system_status,
    "focus_mode": focus_mode,
    "quick_note": quick_note,
    "clean_downloads": clean_downloads,
    "daily_recap": daily_recap,
}
```

---

### Phase 7: WebSocket Bridge (Day 4-5)

#### 7.1 bridge/protocol.py
```python
from dataclasses import dataclass
from typing import Literal
import json

@dataclass
class WSMessage:
    type: str
    payload: dict

# Frontend -> Backend
@dataclass
class ChatMessage(WSMessage):
    type: Literal["chat:message"]
    payload: {"prompt": str, "message_id": str}

@dataclass
class ToolConfirm(WSMessage):
    type: Literal["tool:confirm"]
    payload: {"call_id": str, "confirmed": bool}

# Backend -> Frontend
@dataclass
class ChatResponse(WSMessage):
    type: Literal["chat:response"]
    payload: {"message": dict, "status": str}  # ChatMessage + JarvisStatus

@dataclass
class ToolCall(WSMessage):
    type: Literal["tool:call"]
    payload: {"call_id": str, "tool": str, "params": dict, "description": str}

@dataclass
class ToolResult(WSMessage):
    type: Literal["tool:result"]
    payload: {"call_id": str, "result": str, "error": str | None}

@dataclass
class StatusChange(WSMessage):
    type: Literal["status:change"]
    payload: {"status": str}  # JarvisStatus

@dataclass
class TelemetryUpdate(WSMessage):
    type: Literal["telemetry:update"]
    payload: {"cpu": int, "ram": int, "gpu": int}

@dataclass
class Notification(WSMessage):
    type: Literal["notification"]
    payload: {"title": str, "message": str, "level": str}
```

#### 7.2 bridge/server.py
```python
import asyncio
import websockets
import json
from brain.router import get_provider
from tools.registry import TOOLS, get_tool_schema
from permissions import confirm_destructive, verify_result, RiskTier
from memory.memory import load_summary, save_summary
from plugins import PLUGINS
from skills.skills_registry import SKILLS

class BridgeServer:
    def __init__(self):
        self.provider = get_provider()
        self.clients = set()
        self.conversation_history = []
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        base = """You are J.A.R.V.I.S., a desktop AI assistant for the local operator on CachyOS/Hyprland.
You have access to tools for file operations, system control, window management, and plugins.
Always be concise. Use tools when needed. For destructive actions, request confirmation."""
        summary = asyncio.run(load_summary())
        if summary:
            base += f"\n\nPrevious session summary: {summary}"
        return base

    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                await self.process_message(websocket, json.loads(message))
        finally:
            self.clients.remove(websocket)

    async def process_message(self, ws, msg):
        mtype = msg.get("type")
        if mtype == "chat:message":
            await self.handle_chat(ws, msg["payload"])
        elif mtype == "tool:confirm":
            await self.handle_tool_confirm(ws, msg["payload"])

    async def handle_chat(self, ws, payload):
        prompt = payload["prompt"]
        message_id = payload["message_id"]

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": prompt})

        # Send thinking status
        await ws.send(json.dumps({"type": "status:change", "payload": {"status": "thinking"}}))

        # Call LLM with tools
        response = await self.provider.send(
            [{"role": "system", "content": self.system_prompt}] + self.conversation_history,
            tools=get_tool_schema()
        )

        # Handle tool calls
        if response.get("tool_calls"):
            for tc in response["tool_calls"]:
                await self.execute_tool(ws, tc)
                # Re-call LLM with tool results
                response = await self.provider.send(...)

        # Send final response
        assistant_msg = {
            "id": message_id + "_resp",
            "role": "assistant",
            "content": response["content"],
            "timestamp": int(time.time() * 1000)
        }
        await ws.send(json.dumps({
            "type": "chat:response",
            "payload": {"message": assistant_msg, "status": "idle"}
        }))
        self.conversation_history.append({"role": "assistant", "content": response["content"]})

    async def execute_tool(self, ws, tool_call):
        tool_name = tool_call["function"]["name"]
        params = json.loads(tool_call["function"]["arguments"])
        call_id = tool_call["id"]

        tool_func, risk, _ = TOOLS[tool_name]

        if risk == RiskTier.DESTRUCTIVE:
            description = f"About to execute {tool_name} with params: {params}. Confirm?"
            confirmed = await confirm_destructive(ws, call_id, description)
            if not confirmed:
                await ws.send(json.dumps({"type": "tool:result", "payload": {"call_id": call_id, "result": "", "error": "User cancelled"}}))
                return

        try:
            result = await tool_func(params)
            # Re-verify for destructive
            if risk == RiskTier.DESTRUCTIVE:
                verified = await verify_result(tool_name, params, result)
                if not verified:
                    result = f"WARNING: Re-verification failed for {tool_name}"
            await ws.send(json.dumps({"type": "tool:result", "payload": {"call_id": call_id, "result": result, "error": None}}))
        except Exception as e:
            await ws.send(json.dumps({"type": "tool:result", "payload": {"call_id": call_id, "result": "", "error": str(e)}}))

    async def broadcast_telemetry(self):
        while True:
            cpu, ram, gpu = await get_system_metrics()
            msg = json.dumps({"type": "telemetry:update", "payload": {"cpu": cpu, "ram": ram, "gpu": gpu}})
            for ws in self.clients:
                await ws.send(msg)
            await asyncio.sleep(config.telemetry.update_interval_ms / 1000)
```

---

### Phase 8: HTTP Server + Main Entry (Day 5)

#### 8.1 http_server.py (aiohttp)
```python
from aiohttp import web
import json

async def telemetry_handler(request):
    cpu, ram, gpu = await get_system_metrics()
    return web.json_response({"cpu": cpu, "ram": ram, "gpu": gpu})

async def health_handler(request):
    return web.json_response({"status": "ok"})

async def config_handler(request):
    return web.json_response({
        "llm_provider": config.LLM_PROVIDER,
        "model": config.GEMINI_MODEL if config.LLM_PROVIDER == "gemini" else config.UNIVERSAL_MODEL,
        "tools_enabled": config.tools.enabled,
        "plugins_enabled": config.plugins.enabled,
    })

def create_app():
    app = web.Application()
    app.router.add_get("/api/telemetry", telemetry_handler)
    app.router.add_get("/api/health", health_handler)
    app.router.add_get("/api/config", config_handler)
    # Serve static files in production
    return app
```

#### 8.2 main.py
```python
import asyncio
import sys
sys.path.insert(0, "backend")

from config import config
from bridge.server import BridgeServer
from http_server import create_app
from aiohttp import web

async def main():
    # Start WebSocket bridge
    bridge = BridgeServer()
    ws_server = await websockets.serve(bridge.handle_client, config.BACKEND_HOST, config.BACKEND_PORT)

    # Start HTTP server (for telemetry polling + static files)
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.BACKEND_HOST, config.BACKEND_PORT + 1)  # e.g., 8766
    await site.start()

    print(f"JARVIS Backend running:")
    print(f"  WebSocket: ws://{config.BACKEND_HOST}:{config.BACKEND_PORT}{config.WS_PATH}")
    print(f"  HTTP:      http://{config.BACKEND_HOST}:{config.BACKEND_PORT + 1}")

    # Run telemetry broadcast
    asyncio.create_task(bridge.broadcast_telemetry())

    # Keep running
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
```

---

### Phase 9: Integration Testing (Day 5-6)

#### 9.1 Manual Test Checklist

| Test | Expected |
|------|----------|
| Start backend (`python backend/main.py`) | WebSocket + HTTP servers start |
| Frontend connects to `ws://localhost:8765/ws` | WebSocket handshake succeeds |
| Send chat message "Hello" | Backend returns LLM response, status goes thinking->idle |
| Telemetry polling `/api/telemetry` | Returns real CPU/RAM/GPU |
| WebSocket telemetry push | Frontend receives push updates |
| Tool: `read_file` (safe) | Executes immediately, returns content |
| Tool: `write_file` (risky) | Executes immediately, logs action |
| Tool: `delete_file` (destructive) | Requests confirmation, waits, executes, verifies |
| Plugin: `spotify current-track` | Returns current track via playerctl |
| Plugin: `github list_notifications` | Returns notifications via PAT |
| Plugin: `reddit top_posts python` | Returns top posts from r/python |
| Skill: `system_status` | Returns formatted CPU/RAM/battery |
| Skill: `daily_recap` | Combines memory + GitHub + Spotify |
| Memory: restart backend | Previous session summary injected into prompt |

#### 9.2 Frontend Integration Changes (Minimal)

Only change needed in frontend: Replace `sendMessage` in `JarvisProvider.tsx` to use WebSocket instead of mock.

```typescript
// In JarvisProvider.tsx - replace sendMessage with:
const sendMessage = useCallback(async (prompt: string) => {
  const messageId = Date.now().toString()
  setStatus('thinking')
  setMessages((m) => [...m, { id: messageId, role: 'user', content: prompt, timestamp: Date.now() }])

  wsRef.current?.send(JSON.stringify({
    type: 'chat:message',
    payload: { prompt, message_id: messageId }
  }))
}, [])
```

Add WebSocket connection logic in `App.tsx` or `JarvisProvider.tsx`:
```typescript
const wsRef = useRef<WebSocket | null>(null)

useEffect(() => {
  wsRef.current = new WebSocket('ws://localhost:8765/ws')
  wsRef.current.onmessage = (event) => {
    const msg = JSON.parse(event.data)
    switch (msg.type) {
      case 'chat:response':
        setMessages(m => [...m, msg.payload.message])
        setStatus(msg.payload.status)
        break
      case 'status:change':
        setStatus(msg.payload.status)
        break
      case 'tool:call':
        // Show confirmation dialog
        break
      case 'telemetry:update':
        // Update metrics
        break
    }
  }
  return () => wsRef.current?.close()
}, [])
```

**Note**: Frontend changes are OUT OF SCOPE for backend build. Document here for integration.

---

## Dependencies

### Python Packages (requirements.txt)
```
websockets>=12.0
aiohttp>=3.9
aiofiles>=23.0
google-generativeai>=0.8
openai>=1.30
httpx>=0.27
python-dotenv>=1.0
tomli>=2.0  # for config.toml (stdlib in 3.11+)
psutil>=5.9  # for system metrics
ddgs>=0.1    # for web search (optional)
```

### System Dependencies (CachyOS/Arch)
```bash
sudo pacman -S python python-pip
# For tools:
sudo pacman -S hyprland wl-clipboard notify-send libnotify playerctl nvidia-utils
# For GPU telemetry:
sudo pacman -S nvidia-smi
```

---

## Configuration Summary

| Config | Source | Required |
|--------|--------|----------|
| `LLM_PROVIDER` | .env | Yes (gemini/universal) |
| `GEMINI_API_KEY` | .env | If gemini |
| `GEMINI_MODEL` | .env | If gemini |
| `UNIVERSAL_BASE_URL` | .env | If universal |
| `UNIVERSAL_API_KEY` | .env | If universal |
| `UNIVERSAL_MODEL` | .env | If universal |
| `GITHUB_TOKEN` | .env | For GitHub plugin |
| `BACKEND_PORT` | .env / config.toml | Default 8765 |
| `MEMORY_FILE` | config.toml | Default backend/memory/memory.json |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| WebSocket connection drops | Auto-reconnect in frontend; backend stateless per connection |
| LLM API failures | Graceful fallback to "I'm having trouble thinking right now" |
| Destructive tool bugs | Mandatory re-verification; dry-run mode for testing |
| Hyprland commands fail | Check `hyprctl` exists; fallback error messages |
| Config missing | Validate on startup, clear error messages |

---

## Success Criteria

- [ ] Backend starts without errors
- [ ] Frontend connects via WebSocket
- [ ] Chat works: user message -> LLM response (thinking->idle states)
- [ ] Telemetry works: both HTTP polling and WebSocket push
- [ ] All 12 tools execute with correct risk tier behavior
- [ ] Confirmation flow works for destructive tools + re-verification
- [ ] Memory persists across restarts
- [ ] All 3 plugins functional
- [ ] All 5 skills functional
- [ ] No hardcoded paths/keys/models anywhere

---

## Estimated Timeline

| Phase | Duration |
|-------|----------|
| Phase 0: Setup & Config | 2-3 hours |
| Phase 1: Brain/LLM | 3-4 hours |
| Phase 2: Permissions | 2-3 hours |
| Phase 3: 12 Tools | 4-6 hours |
| Phase 4: Memory | 1-2 hours |
| Phase 5: 3 Plugins | 3-4 hours |
| Phase 6: 5 Skills | 2-3 hours |
| Phase 7: WebSocket Bridge | 3-4 hours |
| Phase 8: HTTP + Main | 2-3 hours |
| Phase 9: Integration Testing | 3-4 hours |
| **Total** | **~25-36 hours** |

---

## Next Steps

1. **Review this plan** - Confirm architecture decisions (WebSocket vs HTTP, port, etc.)
2. **Create backend directory** and start Phase 0
3. **Implement incrementally** - Test each phase before moving to next
4. **Frontend integration** - After backend works, update frontend `JarvisProvider.tsx` to use WebSocket

---

*Plan complete. Ready for implementation.*
