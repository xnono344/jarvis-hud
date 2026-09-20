"""Local transport trust: explicit browser origins plus a per-process credential."""
from __future__ import annotations

import secrets
from http import HTTPStatus
from urllib.parse import urlsplit

from backend.config import config


def same_origin(url: str, trusted: str) -> bool:
    try:
        a, b = urlsplit(url), urlsplit(trusted)
        return (a.scheme, a.hostname, a.port) == (b.scheme, b.hostname, b.port) and not a.username and not a.password
    except ValueError:
        return False


class LocalAccess:
    def __init__(self):
        if config.backend_host not in ('127.0.0.1', 'localhost', '::1'):
            raise ValueError('The desktop bridge must bind to a loopback host')
        self.token = secrets.token_urlsafe(32)
        hosts = ('127.0.0.1', 'localhost', '[::1]')
        self.http_hosts = {f'{host}:{config.backend_http_port}' for host in hosts}
        self.ws_hosts = {f'{host}:{config.backend_ws_port}' for host in hosts}
        self.origins = {f'http://{host}' for host in self.http_hosts}
        self.origins.update(config.browser_origins)

    def request_allowed(self, headers, *, websocket=False) -> bool:
        try:
            hosts = self.ws_hosts if websocket else self.http_hosts
            if headers.get('Host', '').lower() not in hosts:
                return False
            origin = headers.get('Origin')
            if origin is not None and origin not in self.origins:
                return False
            # A browser request from a foreign page must never bootstrap a token.
            if headers.get('Sec-Fetch-Site') == 'cross-site' and origin not in self.origins:
                return False
            return True
        except (ValueError, KeyError):
            return False

    def authenticated(self, token: str) -> bool:
        return isinstance(token, str) and secrets.compare_digest(token, self.token)

    def process_ws_request(self, connection, request):
        if not self.request_allowed(request.headers, websocket=True):
            return connection.respond(HTTPStatus.FORBIDDEN, 'Untrusted local origin or host\n')
        if request.path != config.ws_path:
            return connection.respond(HTTPStatus.NOT_FOUND, 'Unknown WebSocket path\n')
        # Subprotocols carry browser credentials without query-string/log leakage.
        try:
            offered = [v.strip() for v in request.headers.get('Sec-WebSocket-Protocol', '').split(',')]
            authorized = len(offered) == 2 and offered[0] == 'jarvis' and self.authenticated(offered[1])
        except (ValueError, KeyError):
            authorized = False
        if not authorized:
            return connection.respond(HTTPStatus.UNAUTHORIZED, 'Local session credential required\n')
        return None


def grant_local_permission(permission, trusted_origin: str):
    """Qt permission boundary; never grant cameras, screens, or foreign origins."""
    from PySide6.QtWebEngineCore import QWebEnginePermission

    allowed = {
        QWebEnginePermission.PermissionType.MediaAudioCapture,
        QWebEnginePermission.PermissionType.Notifications,
    }
    if same_origin(permission.origin().toString(), trusted_origin) and permission.permissionType() in allowed:
        permission.grant()
    else:
        permission.deny()
