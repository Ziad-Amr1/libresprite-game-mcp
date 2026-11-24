"""
Live Runtime Integration Test with actual LibreSprite binary.
Executes an end-to-end roundtrip:
Python RelayServer -> LibreSprite JS Engine -> RelayServer -> Python Client.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

from libresprite_game_mcp.bridge.http_relay import RelayServer, RelayState
from libresprite_game_mcp.config import get_libresprite_scripts_dir
from libresprite_game_mcp.core.cli_runner import LibreSpriteCLI


def test_live_libresprite_runtime_roundtrip():
    cli = LibreSpriteCLI()
    if not cli.is_available():
        pytest.skip("LibreSprite executable not found on system.")

    port = 64835
    state = RelayState(port=port)
    server = RelayServer(port=port, relay_state=state)
    server.start()

    token = state.session_token
    scripts_dir = get_libresprite_scripts_dir()
    roaming_dir = scripts_dir.parent

    test_script_name = "test_pytest_live_bridge.js"
    (roaming_dir / f"{test_script_name}.session_token").write_text(token, encoding="utf-8")

    js_code = f"""
var tok = "";
if (storage.load("session_token")) {{
    tok = storage.get("session_token");
}}
if (!tok) {{
    tok = "{token}";
}}

var pollKey = "mcp_poll_ptest";
var resultKey = "mcp_result_ptest";

function poll() {{
    var body = JSON.stringify({{
        session_token: tok,
        client_info: {{ version: "1.1-dev", runtime_pytest: true }}
    }});
    var url = "http://127.0.0.1:{port}/poll?token=" + encodeURIComponent(tok);
    storage.fetch(url, pollKey, "", "POST", body, "Content-Type", "application/json");
}}

function onEvent(ev) {{
    if (ev === "init") {{
        poll();
    }} else if (ev === pollKey + "_fetch") {{
        var raw = storage.get(pollKey);
        try {{
            var data = JSON.parse(raw);
            if (data && data.command) {{
                var resBody = JSON.stringify({{
                    session_token: tok,
                    command_id: data.command.command_id,
                    status: "success",
                    result: {{
                        message: "Pytest live roundtrip verified",
                        type: data.command.type
                    }}
                }});
                storage.fetch("http://127.0.0.1:{port}/result?token=" + encodeURIComponent(tok), resultKey, "", "POST", resBody, "Content-Type", "application/json");
            }} else {{
                app.yield("next_tick", 4);
            }}
        }} catch(e) {{}}
    }} else if (ev === "next_tick") {{
        poll();
    }} else if (ev === resultKey + "_fetch") {{
        app.command.Exit();
    }}
}}
"""
    test_script_path = Path(test_script_name).resolve()
    test_script_path.write_text(js_code, encoding="utf-8")

    received = {}

    def queue_worker():
        for _ in range(80):
            if state.is_alive():
                break
            time.sleep(0.1)
        if state.is_alive():
            res = state.queue_command({"type": "live_ping", "params": {}}, timeout=10.0)
            received.update(res)

    t = threading.Thread(target=queue_worker)
    t.start()

    proc = subprocess.run(
        [cli.exe_path, "--script", str(test_script_path)],
        capture_output=True,
        text=True,
        timeout=25,
    )

    t.join(timeout=3.0)
    server.stop()
    test_script_path.unlink(missing_ok=True)
    (roaming_dir / f"{test_script_name}.session_token").unlink(missing_ok=True)

    assert proc.returncode == 0
    assert received.get("status") == "success"
    assert received.get("result", {}).get("message") == "Pytest live roundtrip verified"
    assert received.get("result", {}).get("type") == "live_ping"
