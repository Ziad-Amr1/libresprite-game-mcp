"""
Hardened HTTP relay server bridging MCP tools with the live LibreSprite GUI application.
Provides local session token authentication, payload bounds, command correlation, and secure command dispatch.

Locking Strategy:
- State access is synchronized via a non-reentrant threading.Lock (self.lock).
- Internal helpers requiring self.lock are explicitly named with `_locked` suffix (e.g. `_is_alive_locked`).
- Public methods acquire self.lock and delegate to locked helpers as needed.
- Network wait (command_event.wait) is strictly executed OUTSIDE self.lock to avoid deadlocks.
- Command correlation uses unique UUIDs (command_id) to prevent race conditions, stale response captures,
  and silent command overwrites.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
import uuid
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, Optional, Type

from libresprite_game_mcp.config import get_libresprite_scripts_dir

DEFAULT_PORT = 64823
MAX_PAYLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class RelayState:
    """
    Thread-safe state container managing communication between MCP and LibreSprite GUI.
    """

    def __init__(self, port: int = DEFAULT_PORT):
        self.lock = threading.Lock()
        self.port = port
        self.connected = False
        self.last_ping = 0.0
        self.pending_command: Optional[Dict[str, Any]] = None
        self.active_command_id: Optional[str] = None
        self.command_event = threading.Event()
        self.command_response: Optional[Dict[str, Any]] = None
        self.client_info: Dict[str, Any] = {}
        # Cryptographically secure session token
        self.session_token = secrets.token_hex(16)
        self._write_session_token()

    def _write_session_token(self) -> None:
        """
        Writes session token to both LibreSprite's native script storage location
        and a standard JSON token file for tooling and inspection.
        """
        try:
            scripts_dir = get_libresprite_scripts_dir()
            roaming_dir = scripts_dir.parent
            roaming_dir.mkdir(parents=True, exist_ok=True)

            # 1. Native LibreSprite storage file: <Roaming>/LibreSprite/libresprite_mcp_bridge.js.session_token
            # Loaded automatically by `storage.load("session_token")` in the bridge script.
            native_token_file = roaming_dir / "libresprite_mcp_bridge.js.session_token"
            with open(native_token_file, "w", encoding="utf-8") as f:
                f.write(self.session_token)

            # 2. Standard JSON token file with port metadata
            json_token_file = roaming_dir / "mcp_session_token.json"
            with open(json_token_file, "w", encoding="utf-8") as f:
                json.dump({"session_token": self.session_token, "port": self.port}, f, indent=2)
        except Exception:
            pass

    def rotate_session_token(self) -> str:
        """Rotates the session token, invalidating old sessions."""
        with self.lock:
            self.session_token = secrets.token_hex(16)
            self._write_session_token()
            return self.session_token

    def _is_alive_locked(self, timeout_sec: float = 4.0) -> bool:
        """
        Internal check of connection health.
        MUST only be called when self.lock is already acquired.
        """
        return self.connected and (time.time() - self.last_ping < timeout_sec)

    def is_alive(self, timeout_sec: float = 4.0) -> bool:
        """Public thread-safe check of whether LibreSprite bridge is alive."""
        with self.lock:
            return self._is_alive_locked(timeout_sec)

    def queue_command(self, cmd_data: Dict[str, Any], timeout: float = 10.0) -> Dict[str, Any]:
        """
        Queues a command for LibreSprite, waits for the correlated result, and returns it.
        Guarantees:
        1. No deadlock: uses _is_alive_locked without re-acquiring self.lock.
        2. No command overwrite: rejects new commands if an existing command is in-flight.
        3. Strict correlation: uses command_id UUID to match the exact response.
        4. No stale consumption: if a command times out, late responses are safely ignored.
        """
        with self.lock:
            if not self._is_alive_locked():
                return {
                    "status": "error",
                    "error": "LibreSprite is not connected. Please open LibreSprite and run the 'libresprite_mcp_bridge.js' script from the Scripts menu."
                }

            if self.active_command_id is not None or self.pending_command is not None:
                return {
                    "status": "error",
                    "error": "A command is already pending execution in LibreSprite. Concurrent execution is rejected."
                }

            cmd_id = str(uuid.uuid4())
            self.active_command_id = cmd_id
            self.command_response = None
            self.command_event.clear()
            self.pending_command = {
                "command_id": cmd_id,
                "type": cmd_data.get("type"),
                "params": cmd_data.get("params", {}),
            }

        # Wait outside lock so the HTTP handler can deliver the response
        got_response = self.command_event.wait(timeout=timeout)

        with self.lock:
            self.pending_command = None
            if not got_response or self.command_response is None:
                # Invalidate active_command_id so any delayed response is discarded
                self.active_command_id = None
                self.command_response = None
                return {"status": "error", "error": f"Command timed out after {timeout}s"}

            resp = self.command_response
            self.command_response = None
            self.active_command_id = None
            return resp

    def pop_pending_command(self) -> Optional[Dict[str, Any]]:
        """Retrieves and clears the pending command for delivery to LibreSprite."""
        with self.lock:
            cmd = self.pending_command
            self.pending_command = None
            return cmd

    def set_command_response(self, resp: Dict[str, Any]) -> bool:
        """
        Accepts and matches a response from LibreSprite.
        Returns True if the response matched the active command_id, False if discarded (stale/duplicate).
        """
        with self.lock:
            resp_cmd_id = resp.get("command_id") if isinstance(resp, dict) else None
            if self.active_command_id is not None and resp_cmd_id == self.active_command_id:
                self.command_response = resp
                self.command_event.set()
                return True
            # Discard stale, unsolicited, or mismatched responses
            return False

    def reset(self) -> None:
        """Resets the state container to initial conditions (useful on restart or between tests)."""
        with self.lock:
            self.connected = False
            self.last_ping = 0.0
            self.pending_command = None
            self.active_command_id = None
            self.command_response = None
            self.command_event.set()  # Unblock any waiting thread
            self.client_info.clear()
            self.session_token = secrets.token_hex(16)
            self._write_session_token()


state = RelayState()


class RelayRequestHandler(BaseHTTPRequestHandler):
    """
    Hardened HTTP request handler with authentication, payload bounds, and correlation.
    """

    relay_state: RelayState = state

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine polling logs
        pass

    def _is_authenticated(self, body_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Verifies session token from:
        1. X-MCP-Token HTTP header (standard HTTP clients / CLI)
        2. Query parameter `?token=<token>` (LibreSprite storage.fetch compatible)
        3. JSON body field `session_token` (LibreSprite storage.fetch compatible)
        Uses constant-time comparison (secrets.compare_digest).
        """
        target = self.relay_state.session_token
        if not target:
            return False

        # 1. Header
        header_token = self.headers.get("X-MCP-Token")
        if header_token and secrets.compare_digest(header_token, target):
            return True

        # 2. Query parameter
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if "token" in qs and len(qs["token"]) > 0:
            if secrets.compare_digest(qs["token"][0], target):
                return True

        # 3. Body field
        if body_data and isinstance(body_data, dict):
            body_token = body_data.get("session_token")
            if isinstance(body_token, str) and secrets.compare_digest(body_token, target):
                return True

        return False

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if status >= 400:
            self.send_header("Connection", "close")
            self.close_connection = True
        # Security: Never emit wildcard CORS. Restrict headers.
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/status":
            alive = self.relay_state.is_alive()
            with self.relay_state.lock:
                last_ping = self.relay_state.last_ping
                client_info = dict(self.relay_state.client_info)
            self._send_json({
                "connected": alive,
                "client_info": client_info if alive else {},
                "last_ping_ago": (time.time() - last_ping) if last_ping else None,
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        # Enforce Payload Bounds on Content-Length before reading
        content_len_header = self.headers.get("Content-Length")
        if not content_len_header or not content_len_header.isdigit():
            self._send_json({"error": "Invalid or missing Content-Length header"}, 400)
            return

        content_len = int(content_len_header)
        if content_len > MAX_PAYLOAD_BYTES:
            self._send_json({"error": f"Payload too large. Maximum size is {MAX_PAYLOAD_BYTES} bytes."}, 413)
            return

        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            if not isinstance(body, dict):
                self._send_json({"error": "Payload must be a JSON object"}, 400)
                return
        except Exception:
            self._send_json({"error": "Malformed JSON payload"}, 400)
            return

        # Enforce Authentication (checking header, query param, or parsed body)
        if not self._is_authenticated(body):
            self._send_json({"error": "Unauthorized. Missing or invalid session token."}, 401)
            return

        parsed = urlparse(self.path)
        if parsed.path == "/poll":
            with self.relay_state.lock:
                self.relay_state.connected = True
                self.relay_state.last_ping = time.time()
                if "client_info" in body and isinstance(body["client_info"], dict):
                    self.relay_state.client_info = body["client_info"]

            cmd = self.relay_state.pop_pending_command()
            self._send_json({"command": cmd})

        elif parsed.path == "/result":
            with self.relay_state.lock:
                self.relay_state.last_ping = time.time()

            accepted = self.relay_state.set_command_response(body)
            if accepted:
                self._send_json({"status": "received", "command_id": body.get("command_id")})
            else:
                self._send_json({
                    "status": "ignored",
                    "reason": "stale_or_invalid_command_id",
                    "command_id": body.get("command_id"),
                })

        else:
            self._send_json({"error": "Unknown endpoint"}, 404)


def make_request_handler(state_instance: RelayState) -> Type[RelayRequestHandler]:
    """Creates a request handler class bound to a specific RelayState instance."""
    class BoundHandler(RelayRequestHandler):
        relay_state = state_instance
    return BoundHandler


class RelayServer:
    def __init__(self, port: int = DEFAULT_PORT, relay_state: Optional[RelayState] = None):
        self.port = port
        self.relay_state = relay_state or state
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.server is not None:
            return

        handler_cls = make_request_handler(self.relay_state)
        self.server = HTTPServer(("127.0.0.1", self.port), handler_cls)

        def run():
            try:
                if self.server:
                    self.server.serve_forever()
            except Exception:
                pass

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            self.thread = None


global_relay = RelayServer()


def ensure_relay_running(port: int = DEFAULT_PORT) -> None:
    global global_relay
    if global_relay.server is None:
        global_relay = RelayServer(port)
        global_relay.start()
