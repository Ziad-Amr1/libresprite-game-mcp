"""
Generates the 32x32 experimental character batch into game_assets/experimental_32x32/
Covers 4 archetypes:
1. exp_32_knight: Knight in polished plate armor, flowing crimson plume, heater shield, longsword.
2. exp_32_mage: Arcane Mage with pointed wizard hat, wide draped brim, flowing cascading robes, crystal staff.
3. exp_32_goblin: Goblin Rogue with hunched organic posture, 18px lateral pointed ears, crooked nose, poison dagger.
4. exp_32_heavy_brute: Dwarf Heavy Brute with colossal 18px barrel chest, horned brow, bushy braided beard, double battleaxe.

Exports:
- .aseprite source
- Individual animation frames
- _preview.png
- _idle.gif & _move.gif & _preview.gif
- _sheet.png & _sheet.json
- Godot 4.x SpriteFrames .tres with 'idle' and 'move' animations
- Validates each asset through Art QA.
"""

from pathlib import Path
import json
from PIL import Image

from libresprite_game_mcp.models.schemas import (
    ArtProfile,
    CharacterBlueprint,
    CharacterAnimationSpec,
)
from libresprite_game_mcp.server import create_character_from_blueprint, validate_game_asset
from libresprite_game_mcp.core.aseprite_file import AsepriteProject

def generate_32x32_batch():
    output_dir = Path("game_assets/experimental_32x32")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating 32x32 experimental batch into: {output_dir.resolve()}")

    profile = ArtProfile(
        project_name="Experimental32x32",
        native_resolution=(320, 180),
        character_base_size=(32, 32),
        palette_name="db16",
    )

    blueprints = [
        CharacterBlueprint(
            character_id="exp_32_knight",
            name="Knight 32",
            size=(32, 32),
            proportion="heroic_1_3",
            archetype="knight",
            colors={
                "skin": "#d2aa99",
                "armor": "#8595a1",
                "highlight": "#deeed6",
                "shadow": "#4e4a4e",
                "surcoat": "#597dce",
                "plume": "#d04648",
                "leather": "#854c30",
                "buckle": "#dad45e",
                "outline": "#140c1c",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=6, duration_ms=150, loop=True),
                "move": CharacterAnimationSpec(frames=8, duration_ms=120, loop=True),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_32_mage",
            name="Arcane Mage 32",
            size=(32, 32),
            proportion="heroic_1_3",
            archetype="mage",
            colors={
                "skin": "#d2aa99",
                "robe": "#30346d",
                "robe_highlight": "#597dce",
                "stole": "#dad45e",
                "orb_core": "#deeed6",
                "orb_glow": "#6dc2ca",
                "staff": "#854c30",
                "accent": "#d04648",
                "outline": "#140c1c",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=6, duration_ms=180, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=130, loop=True),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_32_goblin",
            name="Goblin Rogue 32",
            size=(32, 32),
            proportion="chibi_1_2",
            archetype="goblin",
            colors={
                "skin": "#6daa2c",
                "skin_shadow": "#346524",
                "tunic": "#854c30",
                "eyes": "#dad45e",
                "dagger": "#8595a1",
                "poison": "#6daa2c",
                "pants": "#4e4a4e",
                "outline": "#140c1c",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=6, duration_ms=130, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=100, loop=True),
            },
            pivot=(0.5, 0.9),
        ),
        CharacterBlueprint(
            character_id="exp_32_heavy_brute",
            name="Dwarf Brute 32",
            size=(32, 32),
            proportion="heroic_1_3",
            archetype="heavy_brute",
            colors={
                "skin": "#d2aa99",
                "beard": "#d27d2c",
                "beard_shadow": "#854c30",
                "armor": "#757161",
                "axe_head": "#8595a1",
                "axe_edge": "#deeed6",
                "haft": "#854c30",
                "belt": "#140c1c",
                "buckle": "#dad45e",
                "outline": "#140c1c",
            },
            animations={
                "idle": CharacterAnimationSpec(frames=6, duration_ms=200, loop=True),
                "move": CharacterAnimationSpec(frames=6, duration_ms=140, loop=True),
            },
            pivot=(0.5, 0.9),
        ),
    ]

    manifest = {}

    for bp in blueprints:
        print(f"\n--- Generating 32x32 {bp.name} ({bp.character_id}) ---")
        export_res = create_character_from_blueprint(
            blueprint=bp.model_dump(),
            profile=profile.model_dump(),
            export_sheet=True,
            export_gif=True,
            export_godot=True,
            output_dir=str(output_dir),
        )

        ase_path = Path(export_res["aseprite_project"])
        proj = AsepriteProject.load(str(ase_path))

        # Save Preview PNG (first frame)
        preview_png = output_dir / f"{bp.character_id}_preview.png"
        first_frame = proj.get_frame_image(0)
        first_frame.save(preview_png)
        export_res["preview_png"] = str(preview_png)

        # Export individual animation frame PNGs
        frames_dir = output_dir / f"{bp.character_id}_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_paths = []
        all_frames = proj.get_all_frame_images()
        for idx, f_img in enumerate(all_frames):
            f_path = frames_dir / f"frame_{idx:02d}.png"
            f_img.save(f_path)
            frame_paths.append(str(f_path))
        export_res["individual_frames"] = frame_paths

        # Verify Art QA
        qa_report = validate_game_asset(
            str(ase_path),
            palette_name="db16",
            expected_width=32,
            expected_height=32,
        )
        print(f"  Art QA Passed: {qa_report['passed']}")
        if not qa_report["passed"]:
            print(f"  Critical Errors: {qa_report['critical_errors']}")
        assert qa_report["passed"], f"Asset {bp.character_id} failed Art QA: {qa_report['critical_errors']}"

        # Verify Godot SpriteFrames .tres content
        tres_path = Path(export_res["godot_spriteframes"])
        assert tres_path.exists(), "Godot .tres file not found"
        tres_content = tres_path.read_text(encoding="utf-8")
        assert '&"idle"' in tres_content, "Missing 'idle' animation in Godot .tres"
        assert '&"move"' in tres_content, "Missing 'move' animation in Godot .tres"
        print("  Godot 4.x SpriteFrames confirmed: 'idle' & 'move' animations registered.")

        manifest[bp.character_id] = {
            "name": bp.name,
            "export": export_res,
            "qa": qa_report,
            "frames_count": len(all_frames),
            "tags": [t.name for t in proj.sprite.tags],
        }

    manifest_path = output_dir / "experimental_32x32_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nAll 32x32 experimental assets generated successfully. Manifest written to {manifest_path}")

if __name__ == "__main__":
    generate_32x32_batch()
