"""
Hardened HTTP relay server bridging MCP tools with the live LibreSprite GUI application.
Provides local session token authentication, payload bounds, and secure command dispatch.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional

from libresprite_game_mcp.config import get_libresprite_scripts_dir

DEFAULT_PORT = 64823
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class RelayState:
    def __init__(self):
        self.lock = threading.Lock()
        self.connected = False
        self.last_ping = 0.0
        self.pending_command: Optional[Dict[str, Any]] = None
        self.command_event = threading.Event()
        self.command_response: Optional[Dict[str, Any]] = None
        self.client_info: Dict[str, Any] = {}
        # Generate cryptographically secure session token
        self.session_token = secrets.token_hex(16)
        self._write_session_token()

    def _write_session_token(self) -> None:
        """Writes session token to user's secure roaming directory for the bridge script."""
        try:
            token_file = get_libresprite_scripts_dir().parent / "mcp_session_token.json"
            token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, "w", encoding="utf-8") as f:
                json.dump({"session_token": self.session_token, "port": DEFAULT_PORT}, f, indent=2)
        except Exception:
            pass

    def is_alive(self, timeout_sec: float = 4.0) -> bool:
        with self.lock:
            return self.connected and (time.time() - self.last_ping < timeout_sec)

    def queue_command(self, cmd_data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """Queues a command for LibreSprite, waits for result, and returns it."""
        with self.lock:
            if not self.is_alive():
                return {
                    "status": "error",
                    "error": "LibreSprite is not connected. Please open LibreSprite and run the 'libresprite_mcp_bridge.js' script from the Scripts menu."
                }
            self.command_response = None
            self.command_event.clear()
            self.pending_command = cmd_data

        got_response = self.command_event.wait(timeout=timeout)
        with self.lock:
            self.pending_command = None
            if not got_response or self.command_response is None:
                return {"status": "error", "error": f"Command timed out after {timeout}s"}
            return self.command_response

    def pop_pending_command(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            cmd = self.pending_command
            self.pending_command = None
            return cmd

    def set_command_response(self, resp: Dict[str, Any]) -> None:
        with self.lock:
            self.command_response = resp
            self.command_event.set()


state = RelayState()


class RelayRequestHandler(BaseHTTPRequestHandler):
    """Hardened HTTP request handler with authentication and payload bounds."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine polling logs
        pass

    def _is_authenticated(self) -> bool:
        """Verifies session token from X-MCP-Token header or query parameters."""
        token = self.headers.get("X-MCP-Token")
        if token and secrets.compare_digest(token, state.session_token):
            return True

        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if "token" in qs and len(qs["token"]) > 0:
            if secrets.compare_digest(qs["token"][0], state.session_token):
                return True

        return False

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # Security: Do NOT emit wildcard CORS. Restrict to localhost.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/status":
            alive = state.is_alive()
            self._send_json({
                "connected": alive,
                "client_info": state.client_info if alive else {},
                "last_ping_ago": time.time() - state.last_ping if state.last_ping else None,
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        # 1. Enforce Authentication
        if not self._is_authenticated():
            self._send_json({"error": "Unauthorized. Missing or invalid X-MCP-Token."}, 401)
            return

        # 2. Enforce Payload Bounds
        content_len_header = self.headers.get("Content-Length")
        if not content_len_header or not content_len_header.isdigit():
            self._send_json({"error": "Invalid Content-Length header"}, 400)
            return

        content_len = int(content_len_header)
        if content_len > MAX_PAYLOAD_BYTES:
            self._send_json({"error": f"Payload too large. Maximum size is {MAX_PAYLOAD_BYTES} bytes."}, 413)
            return

        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            self._send_json({"error": "Malformed JSON payload"}, 400)
            return

        parsed = urlparse(self.path)
        if parsed.path == "/poll":
            with state.lock:
                state.connected = True
                state.last_ping = time.time()
                if "client_info" in body:
                    state.client_info = body["client_info"]

            cmd = state.pop_pending_command()
            self._send_json({"command": cmd})

        elif parsed.path == "/result":
            with state.lock:
                state.last_ping = time.time()
            state.set_command_response(body)
            self._send_json({"status": "received"})

        else:
            self._send_json({"error": "Unknown endpoint"}, 404)


class RelayServer:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.server is not None:
            return

        def run():
            try:
                self.server = HTTPServer(("127.0.0.1", self.port), RelayRequestHandler)
                self.server.serve_forever()
            except Exception:
                pass

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server = None


global_relay = RelayServer()


def ensure_relay_running(port: int = DEFAULT_PORT) -> None:
    global global_relay
    if global_relay.server is None:
        global_relay = RelayServer(port)
        global_relay.start()
