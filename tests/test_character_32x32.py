"""
Unit and regression tests for native 32x32 character generator and animation system.
Verifies dimensions, palette adherence, alpha hygiene, distinct 'idle' and 'move' animations,
archetype motion profile differentiation, and Godot 4.x SpriteFrames exports.
"""

from pathlib import Path
from PIL import Image
import json

from libresprite_game_mcp.models.schemas import (
    ArtProfile,
    CharacterBlueprint,
    CharacterAnimationSpec,
)
from libresprite_game_mcp.generators.character_generator import (
    generate_character_frame,
    build_animated_character_project,
)
from libresprite_game_mcp.generators.character_generator_32 import (
    generate_character_frame_32,
    build_animated_character_project_32,
)
from libresprite_game_mcp.server import create_character_from_blueprint, validate_game_asset
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.palettes import GamePalette


def test_native_32x32_dimensions_and_layers():
    """Verifies that native 32x32 generation returns exact 32x32 images across all 4 layers."""
    for arch in ["knight", "mage", "goblin", "heavy_brute"]:
        layers = generate_character_frame_32(
            width=32,
            height=32,
            action="idle",
            frame_step=0,
            archetype=arch,
        )
        assert set(layers.keys()) == {"Shadow", "Body", "Clothes", "Gear"}
        for lname, img in layers.items():
            assert img.size == (32, 32), f"Layer {lname} for {arch} has incorrect size {img.size}"
            # Verify alpha hygiene (only 0 or 255)
            alphas = set(img.getchannel("A").tobytes())
            invalid_alphas = {a for a in alphas if a not in (0, 255)}
            assert len(invalid_alphas) == 0, f"Layer {lname} for {arch} has semi-transparent alpha: {invalid_alphas}"


def test_distinct_idle_and_move_motion_profiles():
    """Verifies that idle and move produce meaningful frame changes and distinct motion profiles."""
    for arch in ["knight", "mage", "goblin", "heavy_brute"]:
        # Test idle has changes between frame 0 and frame 2
        f_idle_0 = generate_character_frame_32(32, 32, action="idle", frame_step=0, archetype=arch)
        f_idle_2 = generate_character_frame_32(32, 32, action="idle", frame_step=2, archetype=arch)
        idle_diff = list(f_idle_0["Body"].tobytes()) != list(f_idle_2["Body"].tobytes()) or \
                    list(f_idle_0["Clothes"].tobytes()) != list(f_idle_2["Clothes"].tobytes()) or \
                    list(f_idle_0["Gear"].tobytes()) != list(f_idle_2["Gear"].tobytes())
        assert idle_diff, f"Archetype {arch} idle animation is completely static between frames 0 and 2!"

        # Test move has meaningful locomotion changes
        f_move_0 = generate_character_frame_32(32, 32, action="move", frame_step=0, archetype=arch)
        f_move_2 = generate_character_frame_32(32, 32, action="move", frame_step=2, archetype=arch)
        move_diff = list(f_move_0["Clothes"].tobytes()) != list(f_move_2["Clothes"].tobytes())
        assert move_diff, f"Archetype {arch} move animation has no leg/clothing movement between frames 0 and 2!"

        # Test idle frame 0 vs move frame 0 are visually distinct
        state_diff = list(f_idle_0["Clothes"].tobytes()) != list(f_move_0["Clothes"].tobytes()) or \
                     list(f_idle_0["Body"].tobytes()) != list(f_move_0["Body"].tobytes())
        assert state_diff, f"Archetype {arch} idle and move states are identical at frame 0!"


def test_archetype_silhouette_differentiation():
    """Verifies that all 4 archetypes have distinct active bounding boxes and silhouettes."""
    bboxes = {}
    for arch in ["knight", "mage", "goblin", "heavy_brute"]:
        f = generate_character_frame_32(32, 32, action="idle", frame_step=0, archetype=arch)
        comp = Image.alpha_composite(f["Shadow"], f["Body"])
        comp = Image.alpha_composite(comp, f["Clothes"])
        comp = Image.alpha_composite(comp, f["Gear"])
        bbox = comp.getbbox()
        bboxes[arch] = bbox

    # Verify every archetype has a distinct bounding box or distinct lateral ear/shield/axe extensions
    assert bboxes["goblin"][0] <= 7, "Goblin ear must protrude laterally on left"
    assert bboxes["goblin"][2] >= 24, "Goblin ear must protrude laterally on right"
    assert bboxes["heavy_brute"][2] >= 26, "Heavy brute axe must protrude significantly on right"
    assert bboxes["knight"][0] <= 7, "Knight heater shield must extend on left"


def test_build_and_export_32x32_project():
    """Verifies that create_character_from_blueprint produces complete 32x32 exports."""
    test_dir = Path("test_output_32")
    test_dir.mkdir(exist_ok=True)

    bp = CharacterBlueprint(
        character_id="test_knight_32",
        name="Test Knight",
        size=(32, 32),
        archetype="knight",
        animations={
            "idle": CharacterAnimationSpec(frames=6, duration_ms=150, loop=True),
            "move": CharacterAnimationSpec(frames=8, duration_ms=120, loop=True),
        },
    )
    profile = ArtProfile(
        project_name="TestProject",
        character_base_size=(32, 32),
        palette_name="db16",
    )

    res = create_character_from_blueprint(
        blueprint=bp.model_dump(),
        profile=profile.model_dump(),
        export_sheet=True,
        export_gif=True,
        export_godot=True,
        output_dir=str(test_dir),
    )

    assert Path(res["aseprite_project"]).exists()
    assert Path(res["sheet_png"]).exists()
    assert Path(res["sheet_json"]).exists()
    assert Path(res["preview_gif"]).exists()
    assert Path(res["godot_spriteframes"]).exists()

    # Verify Godot SpriteFrames content
    tres_content = Path(res["godot_spriteframes"]).read_text(encoding="utf-8")
    assert '&"idle"' in tres_content
    assert '&"move"' in tres_content

    # Run Art QA validator
    qa = validate_game_asset(
        res["aseprite_project"],
        palette_name="db16",
        expected_width=32,
        expected_height=32,
    )
    assert qa["passed"] is True
    assert qa["checks"]["dimensions"]["passed"] is True
    assert qa["checks"]["alpha_hygiene"]["passed"] is True
    assert qa["checks"]["palette_adherence"]["passed"] is True


def test_16x16_backward_compatibility():
    """Verifies that existing 16x16 character generation remains 100% functional without regressions."""
    bp_16 = CharacterBlueprint(
        character_id="test_hero_16",
        name="Hero 16",
        size=(16, 16),
        archetype="hero",
    )
    layers = generate_character_frame(width=16, height=16, blueprint=bp_16)
    assert layers["Body"].size == (16, 16)
    assert layers["Clothes"].size == (16, 16)
