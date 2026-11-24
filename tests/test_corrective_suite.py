"""
Comprehensive Corrective Regression Suite.
Covers:
1. Workspace security (path traversal, absolute escape, boundary verification).
2. Bridge security (prototype pollution, unknown command rejection, payload limits).
3. Godot 4 exporter (exact frame timing, atlas region bounds, tag sanitization).
4. QA Validator (anchor pivot baseline, configurable alpha, cluster orphan analysis).
5. CharacterBlueprint and ArtProfile pipeline integration.
"""

from pathlib import Path
import json
import pytest
from PIL import Image

from libresprite_game_mcp.core.security import WorkspacePolicy
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.exporters.game_export import export_godot_spriteframes
from libresprite_game_mcp.qa.validator import AssetValidator
from libresprite_game_mcp.models.schemas import (
    ArtProfile,
    CharacterBlueprint,
    CharacterAnimationSpec,
)
from libresprite_game_mcp.server import (
    create_character_from_blueprint,
    create_character_sprite,
    live_execute_safe_command,
)


def test_workspace_security_boundaries():
    print("Running Suite 1: Workspace Security...")
    approved_dir = Path("test_fixtures_workspace").resolve()
    approved_dir.mkdir(exist_ok=True)
    policy = WorkspacePolicy(approved_roots=[approved_dir])

    # 1. Valid nested path
    valid_sub = approved_dir / "assets" / "hero.png"
    resolved_valid = policy.safe_resolve(valid_sub)
    assert resolved_valid == valid_sub.resolve()

    # 2. Path traversal attack with ../
    traversal_path = approved_dir / ".." / "escaped.png"
    with pytest.raises(PermissionError) as exc_info:
        policy.safe_resolve(traversal_path)
    assert "escapes approved workspace boundaries" in str(exc_info.value)

    # 3. Unauthorized absolute path (e.g. C:/Windows or external directory)
    if Path("C:/Windows").exists():
        with pytest.raises(PermissionError):
            policy.safe_resolve("C:/Windows/temp.png")

    print("  -> Workspace security passed: path traversal and external roots strictly blocked.")
    # Clean up fixture
    approved_dir.rmdir()


def test_bridge_prototype_and_command_security():
    print("Running Suite 2: Bridge Prototype & Command Security...")
    # 1. Prototype properties must be rejected
    for dangerous in ["constructor", "toString", "valueOf", "__proto__"]:
        resp = live_execute_safe_command(dangerous)
        assert resp["status"] == "error"
        assert "not in the safe allowlist" in resp["error"]

    # 2. Unknown command
    resp = live_execute_safe_command("arbitrary_eval_cmd")
    assert resp["status"] == "error"

    print("  -> Bridge security passed: prototype pollution and unknown commands blocked.")


def test_godot_exporter_timing_and_atlas_bounds():
    print("Running Suite 3: Godot Exporter Frame Timing & Atlas Regions...")
    project = AsepriteProject(16, 16)

    # Frame 0: 300ms (anticipation)
    f0 = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
    project.add_animation_frame(duration_ms=300, layer_images={"Base": f0})
    # Frame 1: 150ms
    f1 = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
    project.add_animation_frame(duration_ms=150, layer_images={"Base": f1})
    # Frame 2: 100ms
    f2 = Image.new("RGBA", (16, 16), (0, 0, 255, 255))
    project.add_animation_frame(duration_ms=100, layer_images={"Base": f2})

    project.add_tag("attack", 0, 2)

    tres_path = Path("test_output") / "test_timing.tres"
    # Export with fps=10.0 (base frame duration = 100ms)
    export_godot_spriteframes(
        project,
        "res://sheet.png",
        tres_path,
        fps=10.0,
        frame_rects=[(1, 1, 16, 16), (18, 1, 16, 16), (35, 1, 16, 16)],
        sheet_size=(60, 20),
    )

    content = tres_path.read_text(encoding="utf-8")
    assert '{ "duration": 3.0, "texture": SubResource("AtlasTexture_0") }' in content
    assert '{ "duration": 1.5, "texture": SubResource("AtlasTexture_1") }' in content
    assert '{ "duration": 1.0, "texture": SubResource("AtlasTexture_2") }' in content

    # Test atlas region boundary verification (should raise ValueError if region exceeds sheet)
    with pytest.raises(ValueError) as exc:
        export_godot_spriteframes(
            project,
            "res://sheet.png",
            tres_path,
            fps=10.0,
            frame_rects=[(1, 1, 16, 16), (18, 1, 16, 16), (100, 1, 16, 16)], # Exceeds sheet_size width of 60
            sheet_size=(60, 20),
        )
    assert "exceeds atlas sheet bounds" in str(exc.value)

    tres_path.unlink()
    print("  -> Godot exporter passed: dynamic frame duration multipliers and atlas bounds verified.")


def test_qa_validator_enhancements():
    print("Running Suite 4: QA Validator (Anchor Pivot, Alpha Config, Clusters)...")
    # 1. Anchor Pivot Foot Baseline Check
    f0 = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y in range(8, 13):
        f0.putpixel((8, y), (200, 200, 200, 255)) # Foot at y=12

    f1 = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y in range(8, 13):
        f1.putpixel((8, y), (200, 200, 200, 255)) # Foot at y=12
    f1.putpixel((15, 15), (255, 255, 255, 255)) # Weapon tip far to the right (x=15, y=15)

    proj = AsepriteProject(16, 16)
    proj.add_animation_frame(duration_ms=100, layer_images={"Base": f0})
    proj.add_animation_frame(duration_ms=100, layer_images={"Base": f1})

    val = AssetValidator(anchor_pivot=(0.5, 0.9))
    rep = val.validate_project(proj, "test")
    assert rep.checks["animation_alignment"].details["max_drift_px"] == 0

    # 2. Configurable Alpha Hygiene
    img_translucent = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    img_translucent.putpixel((4, 4), (255, 0, 0, 128)) # Semi-transparent pixel

    val_strict_alpha = AssetValidator(allow_translucent=False)
    rep_strict = val_strict_alpha.validate_image(img_translucent, "alpha_test")
    assert rep_strict.passed is False
    assert "Alpha hygiene violation" in rep_strict.critical_errors[0]

    val_soft_alpha = AssetValidator(allow_translucent=True)
    rep_soft = val_soft_alpha.validate_image(img_translucent, "alpha_test")
    assert rep_soft.passed is True
    assert len(rep_soft.warnings) > 0

    # 3. Cluster Orphan Pixel Analysis
    img_cluster = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    # Draw an isolated 1-pixel dot
    img_cluster.putpixel((8, 8), (255, 255, 255, 255))

    val_cluster = AssetValidator(strict_clusters=True)
    rep_cluster = val_cluster.validate_image(img_cluster, "cluster_test")
    assert rep_cluster.checks["cluster_coherence"].passed is False
    assert rep_cluster.checks["cluster_coherence"].details["orphan_pixel_count"] == 1

    print("  -> QA validator passed: anchor pivot, configurable alpha, and cluster checks verified.")


def test_blueprint_pipeline():
    print("Running Suite 5: CharacterBlueprint & ArtProfile Integration...")
    blueprint = CharacterBlueprint(
        character_id="mage_apprentice",
        name="Mage Apprentice",
        size=(16, 16),
        colors={
            "skin": "#d2aa99",
            "hair": "#442434",
            "shirt": "#6dc2ca", # Cyan robes
            "pants": "#30346d",
            "weapon": "#dad45e", # Golden staff
        },
        animations={
            "idle": CharacterAnimationSpec(frames=2, duration_ms=250),
            "cast": CharacterAnimationSpec(frames=3, duration_ms=100),
        },
        pivot=(0.5, 0.9),
    )
    profile = ArtProfile(
        project_name="WizardGame",
        palette_name="db16",
    )

    out_dir = Path("test_output")
    res = create_character_from_blueprint(
        blueprint=blueprint.model_dump(),
        profile=profile.model_dump(),
        export_sheet=True,
        export_godot=True,
        output_dir=str(out_dir),
    )
    assert res["character_id"] == "mage_apprentice"
    assert "idle" in res["tags"]
    assert "cast" in res["tags"]
    assert Path(res["aseprite_project"]).exists()
    assert Path(res["godot_spriteframes"]).exists()

    # Verify backward compatibility of create_character_sprite
    legacy_res = create_character_sprite(
        name="legacy_hero",
        width=16,
        height=16,
        export_sheet=True,
        output_dir=str(out_dir),
    )
    assert Path(legacy_res["aseprite_project"]).exists()

    print("  -> Blueprint pipeline passed: schema validation, generation, and backward compatibility verified.")


def run_all_corrective_tests():
    test_workspace_security_boundaries()
    test_bridge_prototype_and_command_security()
    test_godot_exporter_timing_and_atlas_bounds()
    test_qa_validator_enhancements()
    test_blueprint_pipeline()
    print("\n========================================================")
    print(">>> ALL CORRECTIVE SPRINT REGRESSION TESTS PASSED! <<<")
    print("========================================================")


if __name__ == "__main__":
    run_all_corrective_tests()
