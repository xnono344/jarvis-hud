<div align="center">

<img src="src/assets/hero.png" width="180" alt="JARVIS HUD layered interface mark" />

# J.A.R.V.I.S HUD

### A cinematic local AI interface with guarded desktop tools.

React HUD · Python bridge · voice · skills · plugins · explicit approvals

![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=111827)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-authenticated-7C3AED?style=flat-square)
![Local first](https://img.shields.io/badge/runtime-local--first-22C55E?style=flat-square)

</div>

React/TypeScript HUD with a local Python assistant bridge, voice input/output, desktop tools, skills, plugins, and an optional Qt desktop shell.

## Highlights

- Animated heads-up display with live conversation and system state
- Gemini and OpenAI-compatible model routing
- Speech-to-text, text-to-speech, and microphone hotkey support
- Desktop tools, reusable skills, and optional service plugins
- Per-category execution allowlists and explicit destructive-action approval
- Authenticated local HTTP and WebSocket transport
- Optional native PySide6 desktop window
- Memory, application launch, filesystem, clipboard, notification, and window tools

## Architecture

```text
React HUD / Qt shell / mic hotkey
              │
      authenticated local transport
              │
        Python assistant bridge
        ├── model providers
        ├── guarded desktop tools
        ├── skills and plugins
        └── voice and local memory
```

## Quick start

Use Python 3.11+ and Node.js compatible with the installed Vite version.

```bash
npm install
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
# Configure backend/.env using backend/.env.example.
npm run build
./jarvis.sh
```

Open http://127.0.0.1:8766. For the native shell, install `PySide6` in the backend environment and run `./jarvis-desktop.sh`.

For frontend development, run the backend and `npm run dev`. Vite uses port 5173 with strict port selection. For a custom backend HTTP port, set `VITE_BACKEND_HTTP_URL` when starting/building Vite. If using another frontend origin (including Vite preview), add its exact origin to `[backend].browser_origins` in `backend/config.toml` and build with the backend URL override.

## Security model

- The backend binds to loopback only. HTTP and WebSocket requests validate the Host and browser Origin against the configured local addresses.
- The frontend obtains a per-process credential from `/api/session` and supplies it during the WebSocket handshake. The credential stays in memory, rotates on restart, and is fetched again on reconnect. The bootstrap response is not cached. Foreign browser origins and framing are rejected.
- POST requests require a bearer credential. `jarvis-mic.sh` obtains and supplies it automatically using the configured HTTP port; the hotkey does not need a manually stored token.
- Local command-line clients can bootstrap without an Origin header. This protects the local service from foreign browser pages; it is not an operating-system sandbox against other local processes.
- Qt grants only microphone and notification permissions to the exact backend origin. Other permission types and navigation to foreign origins are denied.
- `[tools].enabled`, `[skills].enabled`, and `[plugins].enabled` are enforced when executing, including actions inside skills. An empty list disables that category.
- `[applications].allowed` contains executable names accepted by `open_application`. Add your application's exact executable name there if needed. Arguments, paths, and shell expressions are rejected; explicit shell commands use the confirmed shell tool instead.
- Destructive actions and GitHub issue creation require approval from the requesting connection. Pending approvals and queued commands are cancelled on disconnect. Already-started tool/plugin effects settle under the conversation lock before another turn can run; completed side effects are not undone.
- File deletion removes the requested final symlink itself and resolves parent directories correctly. Microphone uploads use securely generated temporary filenames independent of message IDs, with cleanup on completion or failure.

Restart the backend and reload the HUD after updating the application. Existing clients using the old unauthenticated WebSocket connection must reload.

## Verify

```bash
backend/.venv/bin/python -m unittest discover -s backend/tests -v
npm run build
npm run lint
bash -n jarvis-mic.sh
```

The regression suite uses temporary files, local test servers, and mocked model/desktop boundaries. It covers approvals and denial, connection ownership, disconnects, serialized turns, enabled policies, safe deletion/upload paths, HTTP/WebSocket authentication, and Qt permission decisions. The Qt permission test requires PySide6.

`INTEGRATION.md` and `BACKEND_BUILD_PLAN.md` document earlier design stages; the current source and this README describe the implemented connection and execution behavior.
