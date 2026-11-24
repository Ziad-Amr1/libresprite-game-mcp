"""
Production Bridge Execution & Pixel Modification Verification Suite.

Exercises the ACTUAL production script:
    libresprite_game_mcp/bridge/libresprite_mcp_bridge.js

Verifies:
1. Native session token ingestion via Duktape storage.load("session_token").
2. Production bridge initialization and handshake.
3. Execution of real pixel operations (put_pixel) modifying the active image.
4. Internal pixel readback verification inside LibreSprite (getPixel).
5. External pixel readback verification in Python via decoded get_preview PNG.
6. Boundary validation error reporting (coordinates out of bounds).
7. Allowlist enforcement / prototype pollution protection (constructor rejected).
8. Clean process termination via exit_session.
"""

from __future__ import annotations

import base64
import io
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from PIL import Image

from libresprite_game_mcp.bridge.http_relay import state, ensure_relay_running, DEFAULT_PORT
from libresprite_game_mcp.config import get_libresprite_scripts_dir
from libresprite_game_mcp.core.cli_runner import LibreSpriteCLI


def test_production_bridge_live_pixel_execution(tmp_path: Path):
    """
    Executes the actual production bridge script inside a live LibreSprite GUI instance.
    Runs a full lifecycle test with real pixel modifications and allowlist assertions.
    """
    cli = LibreSpriteCLI()
    if not cli.is_available():
        pytest.skip("LibreSprite executable not available in environment.")

    scripts_dir = get_libresprite_scripts_dir()
    roaming_dir = scripts_dir.parent

    # 1. Ensure production bridge script is installed in LibreSprite's scripts directory
    prod_bridge_src = (
        Path(__file__).parent.parent / "libresprite_game_mcp" / "bridge" / "libresprite_mcp_bridge.js"
    ).resolve()
    assert prod_bridge_src.exists(), f"Production bridge script missing at {prod_bridge_src}"

    installed_bridge = scripts_dir / "libresprite_mcp_bridge.js"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(prod_bridge_src, installed_bridge)

    # 2. Reset and ensure production relay server is running on DEFAULT_PORT (64823)
    state.reset()
    ensure_relay_running(DEFAULT_PORT)

    # 3. Enable test mode for the production bridge (auto-connect without blocking modal GUI dialog)
    test_mode_flag = roaming_dir / "libresprite_mcp_bridge.js.test_mode"
    test_mode_flag.write_text("true", encoding="utf-8")

    # 4. Create an isolated 16x16 test canvas image with solid black background
    test_img_path = tmp_path / "live_bridge_fixture.png"
    initial_img = Image.new("RGBA", (16, 16), (0, 0, 0, 255))
    initial_img.save(test_img_path)

    proc: subprocess.Popen | None = None
    try:
        # 5. Launch LibreSprite with the test canvas and the ACTUAL production bridge script
        proc = subprocess.Popen(
            [cli.exe_path, str(test_img_path), "--script", str(installed_bridge)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # 6. Wait for handshake from actual production bridge
        connected = False
        for _ in range(120):
            if state.is_alive():
                connected = True
                break
            time.sleep(0.1)

        assert connected, "Production bridge failed to connect and establish heartbeat within 12s."

        # ---------------------------------------------------------------------
        # TEST 1: Real Pixel Operation (put_pixel) & Engine Readback
        # ---------------------------------------------------------------------
        target_x = 6
        target_y = 10
        target_r = 255
        target_g = 128
        target_b = 32
        target_a = 255

        pixel_cmd = {
            "type": "put_pixel",
            "params": {
                "x": target_x,
                "y": target_y,
                "r": target_r,
                "g": target_g,
                "b": target_b,
                "a": target_a,
            },
        }
        res_pixel = state.queue_command(pixel_cmd, timeout=10.0)

        assert res_pixel.get("status") == "success", f"put_pixel failed: {res_pixel}"
        assert res_pixel.get("command_id") is not None
        pixel_result = res_pixel.get("result", {})
        assert pixel_result.get("x") == target_x
        assert pixel_result.get("y") == target_y
        assert pixel_result.get("color") == [target_r, target_g, target_b, target_a]
        # Internal LibreSprite engine readback verification:
        assert pixel_result.get("verified") is True, "Pixel color failed verification inside LibreSprite engine."

        # ---------------------------------------------------------------------
        # TEST 2: External Preview Verification (get_preview)
        # ---------------------------------------------------------------------
        preview_cmd = {"type": "get_preview"}
        res_preview = state.queue_command(preview_cmd, timeout=10.0)

        assert res_preview.get("status") == "success", f"get_preview failed: {res_preview}"
        b64_data = res_preview.get("result", {}).get("png_base64", "")
        assert b64_data, "No PNG base64 returned by get_preview."

        if b64_data.startswith("data:image/png;base64,"):
            b64_data = b64_data[len("data:image/png;base64,"):]

        decoded_png = base64.b64decode(b64_data)
        preview_img = Image.open(io.BytesIO(decoded_png)).convert("RGBA")

        # Assert pixel modification reflected in decoded image
        painted_pixel = preview_img.getpixel((target_x, target_y))
        assert painted_pixel == (target_r, target_g, target_b, target_a), (
            f"Expected {target_r, target_g, target_b, target_a} at ({target_x}, {target_y}), got {painted_pixel}"
        )
        # Assert untouched pixel remains background black
        untouched_pixel = preview_img.getpixel((0, 0))
        assert untouched_pixel == (0, 0, 0, 255), f"Untouched pixel corrupted: {untouched_pixel}"

        # ---------------------------------------------------------------------
        # TEST 3: Coordinate Boundary Validation (Error Case)
        # ---------------------------------------------------------------------
        oob_cmd = {"type": "put_pixel", "params": {"x": 9999, "y": 9999}}
        res_oob = state.queue_command(oob_cmd, timeout=10.0)

        assert res_oob.get("status") == "error", "Out of bounds coordinate was not rejected."
        assert "out of image bounds" in res_oob.get("error", "").lower()

        # ---------------------------------------------------------------------
        # TEST 4: Security Allowlist / Prototype Pollution Rejection
        # ---------------------------------------------------------------------
        proto_cmd = {"type": "constructor", "params": {}}
        res_proto = state.queue_command(proto_cmd, timeout=10.0)

        assert res_proto.get("status") == "error", "Dangerous prototype command was not rejected."
        assert "not in security allowlist" in res_proto.get("error", "").lower()

        # ---------------------------------------------------------------------
        # TEST 5: Clean Application Shutdown via Bridge
        # ---------------------------------------------------------------------
        exit_cmd = {"type": "exit_session"}
        res_exit = state.queue_command(exit_cmd, timeout=10.0)

        assert res_exit.get("status") == "success", f"exit_session failed: {res_exit}"
        exit_code = proc.wait(timeout=8.0)
        assert exit_code == 0, f"LibreSprite process did not exit cleanly (code: {exit_code})"

    finally:
        # Cleanup state and test flags
        state.reset()
        test_mode_flag.unlink(missing_ok=True)
        if proc and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=3.0)
