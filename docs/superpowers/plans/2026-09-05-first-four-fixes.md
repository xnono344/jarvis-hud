# First Four Review Fixes

Goal: implement the four authorized review findings, preserving existing HUD flows.
Architecture: keep the WebSocket reader responsive with a bounded per-client work queue and shared conversation lock; route nested skill effects through the bridge execution gate; preserve deletion targets and use secure temporary uploads; share a runtime credential between HTTP and WebSocket services with explicit trusted origins.

- [x] Confirmation lifecycle: regress approval, denial, timeout, cross-client approval, disconnect cancellation, and serialized turns; update bridge/server.py and permissions.py.
- [x] Execution policy: regress disabled tools/skills/nested plugin calls and command injection via application launching; update bridge dispatcher, skills, config, and system tool. Empty enabled lists mean disabled.
- [x] Files: regress link deletion and client-controlled upload names; update filesystem.py and bridge audio ingestion.
- [x] Local access: regress HTTP origins/hosts/auth, WebSocket handshake, and Qt permissions; introduce shared security module, wire main/http/frontend/hotkey, restrict Qt permission grants.
- [x] Run unittest suite, TypeScript build, lint, and authenticated local transport checks. Update README with configuration and verification commands.

No live model calls, microphone recordings, or real desktop actions are needed for these checks. Tests substitute those external boundaries. Source backup is stored outside the project because this folder is not a Git repository.

Verification: 29 regression tests pass; production TypeScript/Vite build and Oxlint pass. An offscreen Qt check loaded the built HUD against an isolated authenticated backend, sent a chat message, accepted a mock action dialog, and received the confirmation response. Independent code review findings were fixed and re-reviewed. No live model, microphone, or desktop action was used.
