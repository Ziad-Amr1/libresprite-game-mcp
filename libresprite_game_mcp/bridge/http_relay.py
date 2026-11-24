"""
HTTP relay server bridging MCP tools with the live LibreSprite GUI application.
Provides command queuing, execution timeouts, and live canvas preview retrieval.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

DEFAULT_PORT = 64823


class RelayState:
    def __init__(self):
        self.lock = threading.Lock()
        self.connected = False
        self.last_ping = 0.0
        self.pending_command: Optional[Dict[str, Any]] = None
        self.command_event = threading.Event()
        self.command_response: Optional[Dict[str, Any]] = None
        self.client_info: Dict[str, Any] = {}

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

        # Wait for completion
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
    """Handles HTTP requests between LibreSprite and MCP."""

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress routine polling logs
        pass

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/status":
            alive = state.is_alive()
            self._send_json({
                "connected": alive,
                "client_info": state.client_info if alive else {},
                "last_ping_ago": time.time() - state.last_ping if state.last_ping else None,
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        content_len = int(self.headers.get("Content-Length", 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b"{}"

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            body = {}

        if self.path == "/poll":
            # LibreSprite polling for next action
            with state.lock:
                state.connected = True
                state.last_ping = time.time()
                if "client_info" in body:
                    state.client_info = body["client_info"]

            cmd = state.pop_pending_command()
            self._send_json({"command": cmd})

        elif self.path == "/result":
            # LibreSprite returning execution response
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
            except Exception as e:
                pass

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()
            self.server = None


# Global relay server instance
global_relay = RelayServer()


def ensure_relay_running(port: int = DEFAULT_PORT) -> None:
    global global_relay
    if global_relay.server is None:
        global_relay = RelayServer(port)
        global_relay.start()
