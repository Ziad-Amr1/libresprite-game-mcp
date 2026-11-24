"""
Live Runtime Verification of LibreSprite MCP Bridge.
Spawns RelayServer, writes session token, launches LibreSprite executable with test script,
executes a live roundtrip command, and asserts that Python receives the response.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path

from libresprite_game_mcp.bridge.http_relay import RelayServer, RelayState
from libresprite_game_mcp.config import get_libresprite_scripts_dir


def main():
    print("=== STARTING LIVE RUNTIME VERIFICATION ===")
    port = 64823
    state = RelayState(port=port)
    server = RelayServer(port=port, relay_state=state)
    server.start()

    token = state.session_token
    print(f"1. RelayServer started on port {port}. Session token: {token}")

    scripts_dir = get_libresprite_scripts_dir()
    roaming_dir = scripts_dir.parent

    # Also write token for the test runner script name so storage.load("session_token") works
    test_script_name = "test_runtime_bridge_exec.js"
    (roaming_dir / f"{test_script_name}.session_token").write_text(token, encoding="utf-8")

    js_code = f"""
// 1. Auto-load session token from LibreSprite native storage
var tok = "";
if (storage.load("session_token")) {{
    tok = storage.get("session_token");
}}
if (!tok) {{
    tok = "{token}";
}}
console.log("[JS-BRIDGE] Session token successfully loaded: " + tok.substring(0, 8) + "...");

var pollKey = "mcp_poll_test";
var resultKey = "mcp_result_test";

function poll() {{
    var body = JSON.stringify({{
        session_token: tok,
        client_info: {{ version: "1.1-dev", runtime_test: true, os: "windows" }}
    }});
    var url = "http://127.0.0.1:{port}/poll?token=" + encodeURIComponent(tok);
    console.log("[JS-BRIDGE] Initiating poll request to " + url);
    storage.fetch(url, pollKey, "", "POST", body, "Content-Type", "application/json");
}}

function onEvent(ev) {{
    console.log("[JS-BRIDGE] onEvent called with: " + ev);
    if (ev === "init") {{
        poll();
    }} else if (ev === pollKey + "_fetch") {{
        var raw = storage.get(pollKey);
        console.log("[JS-BRIDGE] Poll response received: " + raw);
        try {{
            var data = JSON.parse(raw);
            if (data && data.command) {{
                console.log("[JS-BRIDGE] Command dispatched: " + data.command.type + " (ID: " + data.command.command_id + ")");
                var resBody = JSON.stringify({{
                    session_token: tok,
                    command_id: data.command.command_id,
                    status: "success",
                    result: {{
                        message: "Live roundtrip command executed successfully in LibreSprite engine!",
                        executed_type: data.command.type,
                        timestamp: Date.now()
                    }}
                }});
                var resUrl = "http://127.0.0.1:{port}/result?token=" + encodeURIComponent(tok);
                console.log("[JS-BRIDGE] Sending result to " + resUrl);
                storage.fetch(resUrl, resultKey, "", "POST", resBody, "Content-Type", "application/json");
            }} else {{
                console.log("[JS-BRIDGE] Empty command queue. Yielding tick...");
                app.yield("next_tick", 6);
            }}
        }} catch(e) {{
            console.log("[JS-BRIDGE] Error processing command: " + e);
        }}
    }} else if (ev === "next_tick") {{
        poll();
    }} else if (ev === resultKey + "_fetch") {{
        console.log("[JS-BRIDGE] Result delivered and acknowledged. Calling app.command.Exit()...");
        app.command.Exit();
    }}
}}
"""
    test_script_path = Path(test_script_name).resolve()
    test_script_path.write_text(js_code, encoding="utf-8")

    received_response = {}

    def queue_worker():
        print("2. Queue worker waiting for LibreSprite connection...")
        for i in range(80):
            if state.is_alive():
                break
            time.sleep(0.1)

        if not state.is_alive():
            print("ERROR: LibreSprite did not connect within 8 seconds.")
            return

        print("3. LibreSprite connected! Queueing harmless command...")
        res = state.queue_command({"type": "live_ping_check", "params": {}}, timeout=10.0)
        received_response.update(res)
        print("4. Queue command unblocked with response:", res)

    t = threading.Thread(target=queue_worker)
    t.start()

    exe_path = r"E:\course\04_Learning_Career\pixel_art\libresprite-development-windows-x86_64\libresprite.exe"
    print(f"5. Launching LibreSprite: {exe_path} --script {test_script_path}")

    proc = subprocess.run(
        [exe_path, "--script", str(test_script_path)],
        capture_output=True,
        text=True,
        timeout=25,
    )

    t.join(timeout=3.0)
    server.stop()
    test_script_path.unlink(missing_ok=True)
    (roaming_dir / f"{test_script_name}.session_token").unlink(missing_ok=True)
    Path("test_gui.py").unlink(missing_ok=True)

    print(f"6. LibreSprite process finished with return code {proc.returncode}.")
    print("--- STDOUT ---")
    print(proc.stdout)
    if proc.stderr:
        print("--- STDERR ---")
        print(proc.stderr)

    print("=== LIVE VERIFICATION RESULT ===")
    print("Received Response in Python:", received_response)

    assert received_response.get("status") == "success", f"Live execution failed: {received_response}"
    assert "Live roundtrip command executed successfully" in received_response.get("result", {}).get("message", "")
    print("SUCCESS: Live LibreSprite bridge roundtrip verified with 100% evidence!")


if __name__ == "__main__":
    main()
