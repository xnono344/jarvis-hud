"""J.A.R.V.I.S native desktop shell (PySide6 / QtWebEngine, Wayland-native).

Owns the full lifecycle: spawns backend/main.py (WS + HTTP + serves the built
UI), waits for /api/health, opens a real window on the local UI, grants mic +
notification permissions to the local origin, and shuts the backend down on
exit. No Electron, no browser needed, no sudo needed.

Usage:
    backend/.venv/bin/python backend/desktop/app.py [--smoke-test]
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from backend.config import config
from backend.security import grant_local_permission, same_origin

BACKEND_MAIN = PROJECT_ROOT / "backend" / "main.py"
BACKEND_HOST = "[::1]" if config.backend_host == "::1" else config.backend_host
BACKEND_HTTP = f"http://{BACKEND_HOST}:{config.backend_http_port}"
BACKEND_HEALTH = BACKEND_HTTP + "/api/health"
ICON = PROJECT_ROOT / "public" / "favicon.svg"

log = logging.getLogger("jarvis.desktop")


def venv_python() -> str:
    exe = PROJECT_ROOT / "backend" / ".venv" / "bin" / "python"
    if exe.exists():
        return str(exe)
    return sys.executable


def wait_for_backend(timeout_s: float = 30.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(BACKEND_HEALTH, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def start_backend() -> subprocess.Popen:
    env = dict(os.environ)
    proc = subprocess.Popen(
        [venv_python(), str(BACKEND_MAIN)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    if not wait_for_backend():
        proc.terminate()
        raise RuntimeError("backend did not become healthy in time (see backend logs)")
    return proc


def stop_backend(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def _chromium_flags() -> None:
    """Chromium flags for a local kiosk-style app window.

    --autoplay-policy=no-user-gesture-required: spoken replies must play
    without a prior click (plain Chromium would silently block them).
    """
    extra = "--autoplay-policy=no-user-gesture-required"
    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
    if extra not in existing:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{existing} {extra}".strip()


def _tiny_wav_b64() -> str:
    """0.2s 440Hz mono WAV for in-page audio-playback diagnostics."""
    import base64
    import math
    import struct

    rate, dur, freq = 8000, 0.2, 440
    frames = b"".join(
        struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / rate)))
        for i in range(int(rate * dur))
    )
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + len(frames), b"WAVE", b"fmt ", 16, 1, 1,
        rate, rate * 2, 2, 16, b"data", len(frames),
    )
    return base64.b64encode(header + frames).decode("ascii")


def _smoke_voice(view, app, ok: bool) -> None:
    """In-page voice diagnostic: mic + speaker, results via console mirror."""
    from PySide6.QtCore import QTimer

    if not ok:
        print("SMOKE-VOICE: page failed to load", flush=True)
        app.quit()
        return
    wav = _tiny_wav_b64()
    js = f"""(async () => {{
      const out = [];
      out.push('hasMediaDevices=' + !!navigator.mediaDevices);
      try {{
        const devs = await navigator.mediaDevices.enumerateDevices();
        out.push('devices=' + devs.map(d => d.kind + ':' + (d.label || 'n/a')).join(','));
      }} catch (e) {{ out.push('enumerateDevices ERROR: ' + e.name + ': ' + e.message); }}
      try {{
        const s = await navigator.mediaDevices.getUserMedia({{ audio: true }});
        out.push('getUserMedia OK tracks=' + s.getAudioTracks().length);
        s.getTracks().forEach(t => t.stop());
      }} catch (e) {{ out.push('getUserMedia ERROR: ' + e.name + ': ' + e.message); }}
      try {{
        const a = new Audio('data:audio/wav;base64,{wav}');
        await a.play();
        out.push('audio.play OK');
      }} catch (e) {{ out.push('audio.play ERROR: ' + e.name + ': ' + e.message); }}
      console.log('VOICETEST ' + out.join(' | '));
    }})();"""
    view.page().runJavaScript(js)
    QTimer.singleShot(15000, lambda: _smoke_loop(view, app))
    QTimer.singleShot(120000, app.quit)


def _smoke_loop(view, app) -> None:
    """Full UI voice loop through the real page: hook <audio>.play, send a
    chat message via the real input, click the real mic button twice, then
    report. Proves provider handlers, not just raw browser APIs."""
    from PySide6.QtCore import QTimer

    js = """(async () => {
      const sleep = (ms) => new Promise(r => setTimeout(r, ms));
      const origPlay = HTMLAudioElement.prototype.play;
      let plays = 0;
      HTMLAudioElement.prototype.play = function () {
        plays++;
        try { console.log('PLAYCALLED srclen=' + (this.src || '').length); }
        catch (e) {}
        return origPlay.call(this);
      };
      // 1. send a chat message through the real input + Enter
      const input = document.querySelector('input[placeholder*="Awaiting"], input[placeholder*="thinking"]');
      if (!input) { console.log('VOICELOOP no-input-found'); return; }
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'Reply with exactly: PAGE LOOP OK');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      console.log('VOICELOOP step=chat-sent');
      await sleep(25000); // LLM reply + spoken audio
      // 2. click mic, record ~2s, click again to send
      const micBtn = () => document.querySelector('button[title*="Speak"], button[title*="Stop"]');
      const b1 = micBtn();
      if (!b1) { console.log('VOICELOOP no-mic-button'); return; }
      b1.click();
      console.log('VOICELOOP step=mic-started');
      await sleep(2500);
      const b2 = micBtn();
      if (b2) b2.click();
      console.log('VOICELOOP step=mic-stopped');
      await sleep(30000); // STT + reply + spoken audio
      console.log('VOICELOOP done plays=' + plays);
    })();"""
    view.page().runJavaScript(js)
    QTimer.singleShot(110000, app.quit)


def _js_sync(page, expression: str, timeout_ms: int = 15000):
    """Run page JS and block for the result (inspection only, no injection)."""
    from PySide6.QtCore import QEventLoop, QTimer

    done = QEventLoop()
    result: dict = {}
    page.runJavaScript(expression, lambda value: (result.setdefault("value", value), done.quit()))
    QTimer.singleShot(timeout_ms, done.quit)
    done.exec()
    return result.get("value")


def _smoke_realinput(view, app, window) -> None:
    """REAL user-input test: genuine Qt mouse clicks + keystrokes (which go
    through real hit-testing and focus), never JS value injection. Fails if
    the UI is click-dead like the scanlines incident."""
    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtTest import QTest

    report: list[str] = []

    # A real user's click activates the window via the WM; the harness must
    # do the same explicitly or keystrokes have nowhere to land.
    window.activateWindow()
    window.raise_()
    view.setFocus()
    QTest.qWait(800)
    report.append(f"window-active={window.isActiveWindow()}")
    # QWebEngineView renders+receives input in an internal child: synthetic
    # events must target the focus proxy, not the parent view (a real mouse
    # doesn't care — the window system routes it — but QTest posts direct).
    target = view.focusProxy() or view
    report.append(f"input-target={type(target).__name__}")

    def js(expr: str):
        return _js_sync(view.page(), expr)

    def _parse_rect(rect):
        import json as _json

        if not rect or rect == "NONE":
            return None
        if isinstance(rect, str):
            try:
                rect = _json.loads(rect)
            except Exception:
                return None
        try:
            return (int(rect["x"] + rect["width"] / 2), int(rect["y"] + rect["height"] / 2))
        except Exception:
            return None

    def click_center(rect) -> bool:
        pt = _parse_rect(rect)
        if pt is None:
            return False
        local = target.mapFrom(view, QPoint(*pt)) if target is not view else QPoint(*pt)
        QTest.mouseClick(target, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, local)
        QTest.qWait(600)
        return True

    try:
        # 1. real click into the command input
        diag = js("(() => [...document.querySelectorAll('input')].map(e => (e.type || 'text') + '=' + (e.placeholder || e.checked)) .join(';;'))()")
        report.append(f"page={diag!r}")
        inp = js("(() => { const el = document.querySelector('input[placeholder*=\"Awaiting\"], input[placeholder*=\"thinking\"]'); if (!el) return 'NONE'; const r = el.getBoundingClientRect(); return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()")
        report.append(f"input-rect={'found' if inp else 'MISSING'}")
        if not inp or not click_center(inp):
            print("REALINPUT FAIL no-input | " + " | ".join(report), flush=True)
            app.quit()
            return
        # 2. real keystrokes — first verify hit-test + focus ground truth
        _pt = _parse_rect(inp)
        probe = js(
            "(() => { const ae = document.activeElement;"
            f" const el = document.elementFromPoint({_pt[0] if _pt else -1}, {_pt[1] if _pt else -1});"
            " const desc = (e) => e ? e.tagName + '.' + (e.className && e.className.baseVal !== undefined ? '' : String(e.className).split(' ').slice(0,2).join('.')) : 'none';"
            " return 'active=' + desc(ae) + ' hit=' + desc(el); })()"
        )
        report.append(f"focus={probe!r}")
        QTest.keyClicks(target, "hello jarvis")
        QTest.qWait(600)
        typed = js("(() => { const el = document.querySelector('input[placeholder*=\"Awaiting\"], input[placeholder*=\"thinking\"]'); return el ? el.value : null; })()")
        report.append(f"typed={typed!r}")
        # 3. real Enter -> message sends, input clears
        count_js = "(() => (document.body.innerText.match(/J\\.A\\.R\\.V\\.I\\.S:/g) || []).length)()"
        before = js(count_js) or 0
        QTest.keyClick(target, Qt.Key.Key_Enter)
        QTest.qWait(1000)
        cleared = js("(() => { const el = document.querySelector('input[placeholder*=\"Awaiting\"], input[placeholder*=\"thinking\"]'); return el ? el.value : 'NO-INPUT'; })()")
        report.append(f"cleared={cleared == ''}")
        # 4. wait for the assistant reply bubble (real backend round trip)
        grew = False
        for _ in range(40):
            QTest.qWait(1000)
            if (js(count_js) or 0) > before:
                grew = True
                break
        report.append(f"reply-arrived={grew}")
        # 5. real click on a QuickNav mode button (thinking pulse)
        nav = js("(() => { const b = [...document.querySelectorAll('button')].find(e => e.textContent.trim() === 'FOCUS'); if (!b) return 'NONE'; const r = b.getBoundingClientRect(); return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()")
        clicked_nav = bool(nav) and click_center(nav)
        report.append(f"nav-click={clicked_nav}")
        # 6. real mic press/release (records ~1.5s of room audio, harmless)
        mic = js("(() => { const b = document.querySelector('button[title*=\"Speak\"], button[title*=\"Stop\"]'); if (!b) return 'NONE'; const r = b.getBoundingClientRect(); return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()")
        if mic and click_center(mic):
            QTest.qWait(1500)
            title = js("(() => { const b = document.querySelector('button[title*=\"Speak\"], button[title*=\"Stop\"]'); return b ? b.title : null; })()")
            report.append(f"mic-recording-state={title}")
            mic2 = js("(() => { const b = document.querySelector('button[title*=\"Speak\"], button[title*=\"Stop\"]'); if (!b) return 'NONE'; const r = b.getBoundingClientRect(); return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()")
            if mic2:
                click_center(mic2)
                QTest.qWait(1000)
                report.append("mic-sent=true")
        else:
            report.append("mic-button=MISSING")
        # 7. task checkbox toggles via real click
        box = js("(() => { const c = document.querySelector('input[type=checkbox]'); if (!c) return 'NONE'; const r = c.getBoundingClientRect(); return JSON.stringify({x: r.x, y: r.y, width: r.width, height: r.height}); })()")
        report.append(f"checkbox-click={bool(box) and click_center(box)}")
    except Exception as e:  # never trap the harness in the window
        report.append(f"harness-error={e!r}")
    print("REALINPUT " + " | ".join(report), flush=True)
    QTimer.singleShot(4000, app.quit)


def run_gui(smoke_test: bool = False) -> int:
    import signal as _signal

    _chromium_flags()

    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QIcon
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication, QMainWindow

    app = QApplication(sys.argv)
    # SIGTERM/SIGINT must unwind through app.exec() so the backend subprocess
    # in the finally-block below is always reaped, never orphaned. Qt blocks in
    # C++ during exec(), so a watchdog timer hands control back to Python
    # regularly — that is what lets the pending signal handler actually run.
    _quit_requested = False

    def _ask_quit(*_args):
        nonlocal _quit_requested
        _quit_requested = True

    _signal.signal(_signal.SIGTERM, _ask_quit)
    _signal.signal(_signal.SIGINT, _ask_quit)
    _watchdog = QTimer()
    _watchdog.timeout.connect(lambda: app.quit() if _quit_requested else None)
    _watchdog.start(500)
    app.setApplicationName("jarvis")
    app.setApplicationDisplayName("J.A.R.V.I.S")
    app.setOrganizationName("jarvis")

    backend = start_backend()
    try:
        window = QMainWindow()
        window.setWindowTitle("J.A.R.V.I.S")
        if ICON.exists():
            window.setWindowIcon(QIcon(str(ICON)))
        window.resize(1366, 860)

        class _LoggingPage(QWebEnginePage):
            def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
                return same_origin(url.toString(), BACKEND_HTTP)

            # Mirror the page console into our log: mic/play failures show
            # up here instead of dying silently inside the web view.
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                log.warning("page console [%s:%s]: %s", level, lineNumber, message)

        view = QWebEngineView(window)
        page = _LoggingPage(view)
        view.setPage(page)
        # Local app origin only: auto-grant mic (voice) + notifications via
        # the current permission API (the old featurePermissionRequested path
        # is deprecated in this Qt version).
        def _grant(permission):
            grant_local_permission(permission, BACKEND_HTTP)

        page.permissionRequested.connect(_grant)
        window.setCentralWidget(view)
        if "--smoke-realinput" in sys.argv[1:]:
            view.loadFinished.connect(
                lambda ok: (
                    QTimer.singleShot(3000, lambda: _smoke_realinput(view, app, window)) if ok else app.quit()
                )
            )
            # Real typing + clicks + mic + reply need ~60s; cap at 150s.
            QTimer.singleShot(150000, app.quit)
        elif "--smoke-voice" in sys.argv[1:]:
            view.loadFinished.connect(lambda ok: _smoke_voice(view, app, ok) if ok else app.quit())
            # Failsafe: loop needs ~75s (chat + STT + replies); cap at 150s.
            QTimer.singleShot(150000, app.quit)
        elif smoke_test:
            view.loadFinished.connect(
                lambda ok: (
                    print(f"SMOKE: ui-loaded={ok}", flush=True),
                    QTimer.singleShot(3000, app.quit),
                )
            )
            # Failsafe: never linger longer than 25s in smoke mode.
            QTimer.singleShot(25000, app.quit)
        view.load(QUrl(BACKEND_HTTP + "/"))
        window.show()
        return app.exec()
    finally:
        stop_backend(backend)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
    smoke = "--smoke-test" in (argv or sys.argv[1:])
    if not (PROJECT_ROOT / "dist" / "index.html").exists():
        print("no production build — run `npm run build` first", file=sys.stderr)
        return 1
    if not (PROJECT_ROOT / "backend" / ".env").exists():
        print("missing backend/.env — copy backend/.env.example first", file=sys.stderr)
        return 1
    try:
        return run_gui(smoke_test=smoke)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
