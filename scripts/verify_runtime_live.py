"""
Live Runtime Verification of LibreSprite MCP Production Bridge.
Executes the ACTUAL production script (libresprite_mcp_bridge.js) inside LibreSprite,
performs real pixel operations, asserts pixel readback and decoded preview,
and cleanly shuts down the session.
"""

from __future__ import annotations

import base64
import io
import shutil
import subprocess
import time
from pathlib import Path
from PIL import Image

from libresprite_game_mcp.bridge.http_relay import RelayServer, RelayState, DEFAULT_PORT
from libresprite_game_mcp.config import get_libresprite_scripts_dir
from libresprite_game_mcp.core.cli_runner import LibreSpriteCLI


def main():
    print("=== STARTING PRODUCTION BRIDGE RUNTIME VERIFICATION ===")
    cli = LibreSpriteCLI()
    if not cli.is_available():
        print("ERROR: LibreSprite executable not found.")
        return

    scripts_dir = get_libresprite_scripts_dir()
    roaming_dir = scripts_dir.parent

    # 1. Install production bridge
    prod_bridge_src = (
        Path(__file__).parent.parent / "libresprite_game_mcp" / "bridge" / "libresprite_mcp_bridge.js"
    ).resolve()
    installed_bridge = scripts_dir / "libresprite_mcp_bridge.js"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prod_bridge_src, installed_bridge)
    print(f"1. Production bridge synchronized: {installed_bridge}")

    # 2. Start relay server
    state = RelayState(port=DEFAULT_PORT)
    server = RelayServer(port=DEFAULT_PORT, relay_state=state)
    server.start()
    print(f"2. RelayServer listening on port {DEFAULT_PORT}. Session token: {state.masked_token()}")

    # 3. Enable test mode flag
    test_mode_flag = roaming_dir / "libresprite_mcp_bridge.js.test_mode"
    test_mode_flag.write_text("true", encoding="utf-8")

    # 4. Create test canvas fixture
    fixture_path = Path("live_verify_fixture.png").resolve()
    Image.new("RGBA", (16, 16), (0, 0, 0, 255)).save(fixture_path)

    proc: subprocess.Popen | None = None
    try:
        # 5. Launch LibreSprite with fixture and production bridge
        print(f"3. Launching LibreSprite with production bridge...")
        proc = subprocess.Popen(
            [cli.exe_path, str(fixture_path), "--script", str(installed_bridge)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 6. Wait for handshake
        print("4. Waiting for production bridge connection...")
        for _ in range(80):
            if state.is_alive():
                break
            time.sleep(0.1)

        assert state.is_alive(), "LibreSprite production bridge failed to connect within 8 seconds."
        print("5. Production bridge connected! Dispatching put_pixel command...")

        # 7. Execute real put_pixel
        tx, ty = 7, 11
        r, g, b, a = 255, 160, 40, 255
        pixel_cmd = {
            "type": "put_pixel",
            "params": {"x": tx, "y": ty, "r": r, "g": g, "b": b, "a": a},
        }
        res_pixel = state.queue_command(pixel_cmd, timeout=10.0)
        printable_res = dict(res_pixel)
        if "session_token" in printable_res:
            printable_res["session_token"] = printable_res["session_token"][:6] + "...[MASKED]"
        print("6. put_pixel response received:", printable_res)
        assert res_pixel.get("status") == "success"
        assert res_pixel.get("result", {}).get("verified") is True, "Engine pixel readback failed"

        # 8. Execute get_preview and verify in Python
        print("7. Dispatching get_preview command...")
        res_preview = state.queue_command({"type": "get_preview"}, timeout=10.0)
        b64 = res_preview.get("result", {}).get("png_base64", "")
        if b64.startswith("data:image/png;base64,"):
            b64 = b64[len("data:image/png;base64,"):]
        decoded = base64.b64decode(b64)
        preview_img = Image.open(io.BytesIO(decoded)).convert("RGBA")
        actual_pixel = preview_img.getpixel((tx, ty))
        print(f"8. Preview decoded in Python. Pixel at ({tx}, {ty}) is: {actual_pixel}")
        assert actual_pixel == (r, g, b, a), f"Preview pixel mismatch: {actual_pixel}"

        # 9. Clean shutdown
        print("9. Dispatching exit_session command...")
        res_exit = state.queue_command({"type": "exit_session"}, timeout=10.0)
        printable_exit = dict(res_exit)
        if "session_token" in printable_exit:
            printable_exit["session_token"] = printable_exit["session_token"][:6] + "...[MASKED]"
        print("10. exit_session response received:", printable_exit)
        exit_code = proc.wait(timeout=5.0)
        print(f"11. LibreSprite process exited cleanly with code: {exit_code}")
        assert exit_code == 0

        print("=== SUCCESS: PRODUCTION BRIDGE AND PIXEL MODIFICATION 100% VERIFIED ===")

    finally:
        server.stop()
        test_mode_flag.unlink(missing_ok=True)
        fixture_path.unlink(missing_ok=True)
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3.0)


if __name__ == "__main__":
    main()
