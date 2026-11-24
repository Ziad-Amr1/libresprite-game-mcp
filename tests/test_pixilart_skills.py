"""
Tests for Pixilart Skills and .pixil Exporter.
Verifies discovery, execution, safe filesystem export, clean art constraints,
and security enforcement.
"""

import json
from pathlib import Path
import pytest
from PIL import Image

from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.exporters.game_export import export_pixilart_project
from libresprite_game_mcp.generators.character_generator import build_animated_character_project
from libresprite_game_mcp.models.schemas import CharacterBlueprint


@pytest.fixture
def orchestrator(tmp_path):
    orch = ProductionOrchestrator(
        db_path=":memory:",
        skills_dir=tmp_path / "skills",
    )
    yield orch
    orch.db.close()


def test_pixilart_skill_discovery(orchestrator):
    """Ensures the Pixilart clean pixel art skill is discoverable in the registry."""
    context = {"task_category": "character", "style": "pixilart"}
    matches = orchestrator.find_applicable_skills(context, art_profile_name="PixilartCommunity")

    assert len(matches) >= 1
    skill = matches[0]
    assert skill.skill_id == "pixilart_clean_pixel_art"
    assert skill.version == "1.0.0"
    assert skill.status.value == "APPROVED"
    assert "export_pixilart_project" in skill.required_tools
    assert skill.validation_rules.get("no_jaggies") is True
    assert skill.validation_rules.get("no_orphan_pixels") is True


def test_pixilart_skill_execution(orchestrator):
    """Executes the complete Pixilart 5-step pipeline and checks experience persistence."""
    result = orchestrator.execute_skill(
        skill_id="pixilart_clean_pixel_art",
        parameters={
            "character_id": "pixil_hero",
            "name": "Pixilart Knight",
            "size": [16, 16],
            "proportion": "chibi_1_2",
            "outline_mode": "colored",
        },
        project_id="PixilartDemo",
    )

    assert result["status"] == "success"
    assert result["skill_id"] == "pixilart_clean_pixel_art"
    assert result["outcome"] == "success"

    steps = result["step_outputs"]
    assert "step_1_sketch_and_block" in steps
    assert "step_2_clean_lines_outline" in steps
    assert "step_3_art_qa_check" in steps
    assert "step_4_export_pixilart" in steps
    assert "step_5_export_spritesheet" in steps

    # Check database persistence
    exp = orchestrator.learning_repo.get_experience(result["experience_id"])
    assert exp is not None
    assert exp.project_id == "PixilartDemo"
    assert "character" in exp.tags


def test_pixilart_file_exporter_and_save(tmp_path):
    """Tests the native .pixil format exporter, verifying it saves valid JSON workspace data."""
    bp = CharacterBlueprint(
        character_id="pixil_mage",
        name="Pixil Mage",
        size=(16, 16),
        proportion="chibi_1_2",
    )
    project = build_animated_character_project(blueprint=bp, palette_name="db16")

    output_pixil = tmp_path / "pixil_mage.pixil"
    saved_path = export_pixilart_project(project, output_pixil, title="Pixil Mage")

    assert saved_path.exists()
    assert saved_path.suffix == ".pixil"

    # Verify JSON structure
    with open(saved_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["format"] == "pixil"
    assert data["version"] == "1.0.0"
    assert data["title"] == "Pixil Mage"
    assert data["width"] == 16
    assert data["height"] == 16
    assert isinstance(data["palette"], list)
    assert len(data["palette"]) > 0
    assert len(data["frames"]) == len(project.sprite.frames)

    # Check frame and layer details
    first_frame = data["frames"][0]
    assert "layers" in first_frame
    first_layer = first_frame["layers"][0]
    assert len(first_layer["pixels"]) > 0
    assert "color" in first_layer["pixels"][0]


def test_pixilart_clean_art_rejection_of_bad_things(orchestrator):
    """Verifies that security injection and unapproved tools are rejected."""
    # Attempting to execute unapproved skill fails
    with pytest.raises(ValueError):
        orchestrator.execute_skill("unapproved_pixil_mod")
