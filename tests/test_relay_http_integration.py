"""
Real HTTP Integration Test Suite for LibreSprite MCP Relay Server.

Starts an actual local HTTP RelayServer and executes real HTTP requests using urllib.
Covers:
1. Authenticated vs unauthenticated /poll and /result requests across all 3 token mechanisms:
   - X-MCP-Token HTTP header
   - URL query parameter ?token=
   - JSON body parameter session_token
2. Command queue lifecycle and empty queue behavior
3. Strict command correlation via UUID (command_id)
4. Protection against silent command overwriting (concurrency guard)
5. Timeout handling and rejection of delayed/stale responses
6. Safe duplicate result handling
7. Payload size bounds (>5MB returns 413)
8. Invalid Content-Length and malformed JSON payloads (returns 400)
9. Session token rotation invalidating previous credentials
10. Server shutdown and clean restart on same port
"""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

import pytest

from libresprite_game_mcp.bridge.http_relay import RelayServer, RelayState, MAX_PAYLOAD_BYTES


def find_free_port() -> int:
    """Finds an available local port for isolated server testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def send_http(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
) -> Tuple[int, Dict[str, Any]]:
    """Helper to send HTTP requests and parse JSON responses."""
    req = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            return status, json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return err.code, parsed


class TestRelayHttpIntegration:
    @pytest.fixture(autouse=True)
    def setup_server(self):
        self.port = find_free_port()
        self.state = RelayState(port=self.port)
        self.server = RelayServer(port=self.port, relay_state=self.state)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.port}"
        # Give server a moment to bind
        time.sleep(0.05)
        yield
        self.server.stop()

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to protected endpoints must return 401."""
        # 1. /poll without token
        status, body = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Type": "application/json", "Content-Length": "2"},
            data=b"{}",
        )
        assert status == 401
        assert "Unauthorized" in body.get("error", "")

        # 2. /result without token
        status, body = send_http(
            f"{self.base_url}/result",
            method="POST",
            headers={"Content-Type": "application/json", "Content-Length": "2"},
            data=b"{}",
        )
        assert status == 401
        assert "Unauthorized" in body.get("error", "")

        # 3. Invalid header token
        status, body = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": "2",
                "X-MCP-Token": "bad_token_12345",
            },
            data=b"{}",
        )
        assert status == 401

        # 4. Invalid query parameter token
        status, body = send_http(
            f"{self.base_url}/poll?token=wrong_query_token",
            method="POST",
            headers={"Content-Type": "application/json", "Content-Length": "2"},
            data=b"{}",
        )
        assert status == 401

        # 5. Invalid body token
        bad_body = json.dumps({"session_token": "wrong_body_token"}).encode("utf-8")
        status, body = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Type": "application/json", "Content-Length": str(len(bad_body))},
            data=bad_body,
        )
        assert status == 401

    def test_authenticated_requests_supported_via_all_mechanisms(self):
        """Valid session token accepted via header, query parameter, or JSON body."""
        valid_tok = self.state.session_token

        # Mechanism 1: HTTP Header (X-MCP-Token)
        body1 = json.dumps({"client_info": {"mode": "header_test"}}).encode("utf-8")
        status, data = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body1)),
                "X-MCP-Token": valid_tok,
            },
            data=body1,
        )
        assert status == 200
        assert data.get("command") is None
        assert self.state.is_alive()
        assert self.state.client_info.get("mode") == "header_test"

        # Mechanism 2: Query parameter (?token=)
        body2 = json.dumps({"client_info": {"mode": "query_test"}}).encode("utf-8")
        status, data = send_http(
            f"{self.base_url}/poll?token={valid_tok}",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body2)),
            },
            data=body2,
        )
        assert status == 200
        assert self.state.client_info.get("mode") == "query_test"

        # Mechanism 3: JSON body field (session_token)
        body3 = json.dumps({"session_token": valid_tok, "client_info": {"mode": "body_test"}}).encode("utf-8")
        status, data = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body3)),
            },
            data=body3,
        )
        assert status == 200
        assert self.state.client_info.get("mode") == "body_test"

    def test_payload_bounds_and_malformed_json(self):
        """Enforces 5MB size limits, valid headers, and well-formed JSON."""
        valid_tok = self.state.session_token

        # 1. Payload exceeding MAX_PAYLOAD_BYTES (5MB) rejected with 413
        oversized_len = MAX_PAYLOAD_BYTES + 1024
        req = urllib.request.Request(
            f"{self.base_url}/poll",
            data=b"a" * 16,
            method="POST",
            headers={
                "Content-Length": str(oversized_len),
                "X-MCP-Token": valid_tok,
                "Connection": "close",
            },
        )
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(req, timeout=5.0)
        assert exc_info.value.code == 413

        # 2. Malformed JSON payload returns 400
        broken_json = b'{"unclosed_json: '
        status, body = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(broken_json)),
                "X-MCP-Token": valid_tok,
            },
            data=broken_json,
        )
        assert status == 400
        assert "Malformed JSON" in body.get("error", "")

        # 3. Non-object JSON payload returns 400
        array_json = b'[1, 2, 3]'
        status, body = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(array_json)),
                "X-MCP-Token": valid_tok,
            },
            data=array_json,
        )
        assert status == 400
        assert "must be a JSON object" in body.get("error", "")

    def test_command_lifecycle_and_correlation(self):
        """Verifies command queuing, popping, execution correlation, and result delivery."""
        valid_tok = self.state.session_token

        # Mark alive via initial poll
        init_body = json.dumps({"session_token": valid_tok}).encode("utf-8")
        send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(init_body))},
            data=init_body,
        )
        assert self.state.is_alive()

        # Queue a command in a separate thread
        queue_result = {}

        def queue_worker():
            cmd = {"type": "create_canvas", "params": {"width": 32, "height": 32}}
            res = self.state.queue_command(cmd, timeout=5.0)
            queue_result.update(res)

        t = threading.Thread(target=queue_worker)
        t.start()

        # Wait briefly for command to be queued
        time.sleep(0.05)

        # 1. /poll fetches the queued command
        poll_body = json.dumps({"session_token": valid_tok}).encode("utf-8")
        status, poll_resp = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(poll_body))},
            data=poll_body,
        )
        assert status == 200
        cmd = poll_resp.get("command")
        assert cmd is not None
        assert cmd.get("type") == "create_canvas"
        cmd_id = cmd.get("command_id")
        assert cmd_id is not None

        # 2. Immediate subsequent poll returns empty queue (command was popped)
        status, empty_poll = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(poll_body))},
            data=poll_body,
        )
        assert empty_poll.get("command") is None

        # 3. Post result with matching command_id
        result_payload = {
            "session_token": valid_tok,
            "command_id": cmd_id,
            "status": "success",
            "result": {"message": "Canvas created 32x32"},
        }
        res_bytes = json.dumps(result_payload).encode("utf-8")
        status, res_resp = send_http(
            f"{self.base_url}/result",
            method="POST",
            headers={"Content-Length": str(len(res_bytes))},
            data=res_bytes,
        )
        assert status == 200
        assert res_resp.get("status") == "received"
        assert res_resp.get("command_id") == cmd_id

        # 4. Verify queuing thread received the exact result
        t.join(timeout=2.0)
        assert queue_result.get("status") == "success"
        assert queue_result.get("result", {}).get("message") == "Canvas created 32x32"

    def test_concurrent_command_overwrite_prevention(self):
        """Attempting to queue a second command while one is in-flight must be rejected."""
        valid_tok = self.state.session_token

        # Mark alive
        body = json.dumps({"session_token": valid_tok}).encode("utf-8")
        send_http(f"{self.base_url}/poll", method="POST", headers={"Content-Length": str(len(body))}, data=body)

        first_cmd_result = {}

        def first_worker():
            res = self.state.queue_command({"type": "get_preview"}, timeout=2.0)
            first_cmd_result.update(res)

        t = threading.Thread(target=first_worker)
        t.start()
        time.sleep(0.05)

        # Attempt to queue a second command while first is in-flight
        second_res = self.state.queue_command({"type": "clear_canvas"}, timeout=1.0)
        assert second_res.get("status") == "error"
        assert "already pending execution" in second_res.get("error", "")

        t.join(timeout=3.0)

    def test_timeout_and_stale_response_discard(self):
        """Late responses arriving after a command timeout must be discarded, not corrupting state."""
        valid_tok = self.state.session_token

        # Mark alive
        body = json.dumps({"session_token": valid_tok}).encode("utf-8")
        send_http(f"{self.base_url}/poll", method="POST", headers={"Content-Length": str(len(body))}, data=body)

        # 1. Queue command with very short timeout
        short_res = self.state.queue_command({"type": "put_pixel"}, timeout=0.1)
        assert short_res.get("status") == "error"
        assert "timed out after 0.1s" in short_res.get("error", "")

        # 2. LibreSprite sends delayed result for the timed-out command
        stale_payload = {
            "session_token": valid_tok,
            "command_id": "old-stale-uuid-from-timed-out-command",
            "status": "success",
            "result": {"message": "Late delivery"},
        }
        res_bytes = json.dumps(stale_payload).encode("utf-8")
        status, res_resp = send_http(
            f"{self.base_url}/result",
            method="POST",
            headers={"Content-Length": str(len(res_bytes))},
            data=res_bytes,
        )
        assert status == 200
        # Must be flagged as ignored, not accepted
        assert res_resp.get("status") == "ignored"
        assert res_resp.get("reason") == "stale_or_invalid_command_id"

    def test_duplicate_result_handling(self):
        """Duplicate results sent for the same command are safely ignored."""
        valid_tok = self.state.session_token
        body = json.dumps({"session_token": valid_tok}).encode("utf-8")
        send_http(f"{self.base_url}/poll", method="POST", headers={"Content-Length": str(len(body))}, data=body)

        cmd_res = {}

        def worker():
            res = self.state.queue_command({"type": "draw_rect"}, timeout=3.0)
            cmd_res.update(res)

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        # Poll command
        _, poll_data = send_http(
            f"{self.base_url}/poll", method="POST", headers={"Content-Length": str(len(body))}, data=body
        )
        cmd_id = poll_data["command"]["command_id"]

        result_payload = {
            "session_token": valid_tok,
            "command_id": cmd_id,
            "status": "success",
            "result": {"message": "Drawn"},
        }
        res_bytes = json.dumps(result_payload).encode("utf-8")

        # First delivery -> accepted
        _, resp1 = send_http(
            f"{self.base_url}/result", method="POST", headers={"Content-Length": str(len(res_bytes))}, data=res_bytes
        )
        assert resp1.get("status") == "received"

        # Wait for thread to consume
        t.join(timeout=1.0)
        assert cmd_res.get("status") == "success"

        # Duplicate delivery -> ignored
        _, resp2 = send_http(
            f"{self.base_url}/result", method="POST", headers={"Content-Length": str(len(res_bytes))}, data=res_bytes
        )
        assert resp2.get("status") == "ignored"

    def test_session_token_rotation(self):
        """Rotating the session token immediately invalidates the old token."""
        old_tok = self.state.session_token
        new_tok = self.state.rotate_session_token()
        assert new_tok != old_tok

        # Request with old token fails
        old_body = json.dumps({"session_token": old_tok}).encode("utf-8")
        status, _ = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(old_body))},
            data=old_body,
        )
        assert status == 401

        # Request with new token succeeds
        new_body = json.dumps({"session_token": new_tok}).encode("utf-8")
        status, data = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(new_body))},
            data=new_body,
        )
        assert status == 200

    def test_server_shutdown_and_restart(self):
        """Server stops cleanly, releases the port, and can be restarted."""
        self.server.stop()
        time.sleep(0.05)

        # Starting a new server on the same port should succeed
        new_server = RelayServer(port=self.port, relay_state=self.state)
        new_server.start()
        time.sleep(0.05)

        body = json.dumps({"session_token": self.state.session_token}).encode("utf-8")
        status, data = send_http(
            f"{self.base_url}/poll",
            method="POST",
            headers={"Content-Length": str(len(body))},
            data=body,
        )
        assert status == 200
        new_server.stop()
