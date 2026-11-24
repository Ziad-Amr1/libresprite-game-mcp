"""
Regression and validation test suite for LibreSprite Game MCP Production System.
"""

from pathlib import Path
import json
from PIL import Image

from libresprite_game_mcp.models import (
    ArtProfile,
    CharacterBlueprint,
    CharacterAnimationSpec,
    TilesetSpec,
    ItemSpec,
)
from libresprite_game_mcp.server import (
    create_character_sprite,
    create_game_item,
    validate_game_asset,
    live_execute_safe_command,
)
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.palettes import GamePalette


def test_pydantic_schemas():
    print("Testing Pydantic Schemas...")
    profile = ArtProfile(
        project_name="PixelRpg",
        native_resolution=(320, 180),
        palette_name="db16",
    )
    assert profile.project_name == "PixelRpg"
    assert profile.palette_name == "db16"

    blueprint = CharacterBlueprint(
        character_id="hero_warrior",
        name="Warrior",
        size=(16, 16),
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=250),
            "walk": CharacterAnimationSpec(frames=4, duration_ms=120),
        }
    )
    assert blueprint.character_id == "hero_warrior"
    assert blueprint.animations["walk"].frames == 4
    print("  -> Schemas validated successfully.")


def test_clean_aseprite_layers():
    print("Testing Clean Aseprite Layers (No orphan 'Layer 1')...")
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    torch = create_game_item("torch", "clean_torch", size=16, output_dir=str(test_dir))
    proj = AsepriteProject.load(torch["aseprite_project"])
    layers = [l.name for l in proj.sprite.layers]
    print("  Torch Layers:", layers)
    assert "Layer 1" not in layers, "Default 'Layer 1' should not remain an orphan layer!"
    assert "Torch" in layers


def test_godot_spriteframes_syntax():
    print("Testing Godot 4.x SpriteFrames Sub-Resource Syntax...")
    test_dir = Path("test_output")
    char_res = create_character_sprite(
        name="paladin",
        width=16,
        height=16,
        export_godot=True,
        output_dir=str(test_dir),
    )
    tres_path = Path(char_res["godot_spriteframes"])
    assert tres_path.exists()

    content = tres_path.read_text(encoding="utf-8")
    assert '[sub_resource type="AtlasTexture" id="AtlasTexture_0"]' in content
    assert 'atlas = ExtResource("1_texture")' in content
    assert 'region = Rect2(' in content
    assert 'SubResource("AtlasTexture_0")' in content
    print("  -> Godot 4.x SpriteFrames syntax verified with full AtlasTexture subresources!")


def test_qa_validation_engine():
    print("Testing Automated QA Validation Engine...")
    test_dir = Path("test_output")

    # 1. Validate valid asset
    valid_report = validate_game_asset(
        str(test_dir / "paladin.aseprite"),
        palette_name="db16",
        expected_width=16,
        expected_height=16,
    )
    print("  Valid Asset QA Result:", valid_report["passed"], "Warnings:", valid_report["warnings"])
    assert valid_report["passed"] is True
    assert valid_report["checks"]["dimensions"]["passed"] is True
    assert valid_report["checks"]["alpha_hygiene"]["passed"] is True

    # 2. Test intentionally invalid asset (dimension mismatch)
    invalid_report = validate_game_asset(
        str(test_dir / "paladin.aseprite"),
        palette_name="db16",
        expected_width=32,
        expected_height=32,
    )
    assert invalid_report["passed"] is False
    assert len(invalid_report["critical_errors"]) > 0
    print("  -> QA Validator correctly flagged dimension defect.")


def test_safe_command_allowlist():
    print("Testing Safe Command Allowlist...")
    # Attempt unauthorized command
    resp = live_execute_safe_command("eval", {"code": "alert(1)"})
    assert resp["status"] == "error"
    assert "not in the safe allowlist" in resp["error"]
    print("  -> Unauthorized command blocked successfully.")


def run_all():
    test_pydantic_schemas()
    test_clean_aseprite_layers()
    test_godot_spriteframes_syntax()
    test_qa_validation_engine()
    test_safe_command_allowlist()
    print("\n>>> ALL REGRESSION & VALIDATION TESTS PASSED! <<<")


if __name__ == "__main__":
    run_all()
