"""Loopback helpers for Google login.

The web page at ``{login_url}/cli/login`` exchanges Google credentials for a
Digen token, then POSTs it to a local callback server. This CLI does not call
Google exchange itself. Email/password and Apple login are not supported.

- loopback: listen on 127.0.0.1, receive POST /callback with token + state
- manual: print the login URL and let the user paste the Digen token
"""

from __future__ import annotations

import os
import secrets
import socket
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

_CALLBACK_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Digen Skill CLI</title></head>
<body style="font-family: sans-serif; text-align: center; margin-top: 10vh;">
<h2>Login complete. You can close this page and return to the terminal.</h2>
</body></html>
"""

LOOPBACK_TIMEOUT = 180.0


def generate_state() -> str:
    """32 bytes of url-safe random data, used as a CSRF check on the callback."""
    return secrets.token_urlsafe(32)


def build_cli_login_url(
    login_base: str,
    *,
    hint: str,
    callback: Optional[str] = None,
    state: Optional[str] = None,
) -> str:
    """Build ``{login_base}/cli/login?...`` for the dedicated web login page."""
    base = login_base.rstrip("/") + "/cli/login"
    params: dict[str, str] = {"hint": hint}
    if callback:
        params["callback"] = callback
    if state:
        params["state"] = state
    return base + "?" + urlencode(params)


class TokenCaptureServer:
    """Single-shot HTTP server that accepts POST /callback with a Digen token."""

    def __init__(self, port: int = 0):
        self.result: Optional[dict] = None
        self._stop = threading.Event()
        self._server = HTTPServer(("127.0.0.1", port), self._make_handler())
        self.port = self._server.server_port
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while not self._stop.is_set():
            self._server.handle_request()
            if self.result is not None:
                self._stop.set()
                return

    def _make_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != "/callback":
                    self.send_response(404)
                    self.end_headers()
                    return
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else ""
                qs = parse_qs(raw, keep_blank_values=True)
                token = (qs.get("token") or [None])[0]
                if not token:
                    self.send_response(400)
                    self.end_headers()
                    return
                outer.result = {
                    "token": token,
                    "state": (qs.get("state") or [None])[0] or None,
                    "name": (qs.get("name") or [None])[0] or None,
                    "email": (qs.get("email") or [None])[0] or None,
                    "id": (qs.get("id") or [None])[0] or None,
                    "sessionid": (qs.get("sessionid") or qs.get("sessionId") or [None])[0] or None,
                }
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(_CALLBACK_HTML.encode("utf-8"))

            def do_GET(self):  # noqa: N802
                self.send_response(405)
                self.end_headers()

            def log_message(self, format, *args):  # noqa: A002
                pass

        return Handler

    def wait_for_result(self, timeout: float = LOOPBACK_TIMEOUT) -> Optional[dict]:
        self._thread.join(timeout=timeout)
        self._stop.set()
        if self._thread.is_alive():
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1) as sock:
                    sock.sendall(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
            except OSError:
                pass
            self._thread.join(timeout=2)
        try:
            self._server.server_close()
        except Exception:
            pass
        return self.result


def loopback_callback_server(port: int = 0) -> TokenCaptureServer:
    """Start a local loopback server (call wait_for_result() after opening the browser)."""
    return TokenCaptureServer(port)


def open_browser(url: str) -> bool:
    def _open():
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()
    return True


def prompt_for_token(login_url: str, console) -> str:
    """Manual fallback: print the URL and read the Digen token pasted by the user."""
    console.print("[bold]Open this URL if the browser does not open:[/bold]")
    # Plain print so a long URL stays on one line (copy-paste / tests).
    print(login_url, flush=True)
    console.print(
        "[dim]Copy the token from the page and paste it here "
        "(same as: digenskill login --token)[/dim]"
    )
    return console.input("[bold yellow]token> [/bold yellow]").strip()
