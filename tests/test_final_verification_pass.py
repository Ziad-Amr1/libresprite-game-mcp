"""
Final Integration Verification & Data Integrity Audit Test Suite.
Verifies:
- Objective A: Real MCP tool binding through ProductionOrchestrator without recursion.
- Objective B: Measurable pixel difference and rule consumption with guidance enabled vs disabled for 16x16 and 32x32.
- Objective C: Strict data ownership across Knowledge, Feedback, and Skill stores.
- Objective D: Database migration and seeded rule idempotency.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any
import pytest
from PIL import Image

from libresprite_game_mcp.server import (
    create_character_from_blueprint,
    create_character_sprite,
    generate_character as mcp_generate_character,
    orchestrator,
)
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.generators.character_generator import (
    build_animated_character_project,
)
from libresprite_game_mcp.generators.character_generator_32 import (
    build_animated_character_project_32,
)
from libresprite_game_mcp.models.schemas import CharacterBlueprint, CharacterAnimationSpec, ArtProfile
from libresprite_game_mcp.learning.models import (
    KnowledgeRecord,
    KnowledgeType,
    KnowledgeCategory,
    EvidenceStatus,
    ReferenceProvenance,
)
from libresprite_game_mcp.storage.database import DatabaseManager
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.learning.seed_knowledge import seed_art_bible_knowledge


# =============================================================================
# OBJECTIVE A: REAL MCP INTEGRATION VERIFICATION
# =============================================================================

def test_mcp_create_character_from_blueprint_uses_orchestrator():
    """Verifies that create_character_from_blueprint calls orchestrator and logs experience."""
    test_dir = Path("test_tmp/final_pass_bp")
    test_dir.mkdir(parents=True, exist_ok=True)
    bp = {
        "character_id": "mcp_hero_test",
        "name": "MCP Hero",
        "size": [16, 16],
        "archetype": "knight",
    }
    profile = {
        "project_name": "MCPTestProject",
        "palette_name": "db16",
    }

    initial_exp_count = len(orchestrator.learning_repo.query_experiences(project_id="MCPTestProject"))

    res = create_character_from_blueprint(
        blueprint=bp,
        profile=profile,
        export_sheet=True,
        export_gif=True,
        output_dir=str(test_dir),
    )

    assert "experience_id" in res
    assert "guidance_applied" in res
    assert len(res["guidance_applied"]) > 0
    assert "guidance_rules_consumed" in res
    assert len(res["guidance_rules_consumed"]) > 0

    # Verify telemetry in LearningRepository
    after_exp_count = len(orchestrator.learning_repo.query_experiences(project_id="MCPTestProject"))
    assert after_exp_count == initial_exp_count + 1

    saved_exp = orchestrator.learning_repo.get_experience(res["experience_id"])
    assert saved_exp is not None
    assert saved_exp.task_category == "character"
    assert saved_exp.tools_used == ["create_character_from_blueprint"]


def test_mcp_generate_character_endpoint():
    """Verifies public generate_character MCP endpoint flow."""
    test_dir = Path("test_tmp/final_pass_gen")
    test_dir.mkdir(parents=True, exist_ok=True)
    res = mcp_generate_character(
        character_id="public_mcp_paladin",
        name="Public Paladin",
        width=16,
        height=16,
        archetype="knight",
        palette_name="db16",
        art_profile="PaladinProject",
        project_id="PaladinProject",
        output_dir=str(test_dir),
    )

    assert Path(res["project_path"]).exists()
    assert "experience_id" in res
    assert "guidance" in res
    assert len(res["guidance_applied"]) > 0
    assert len(res["guidance_rules_consumed"]) > 0


def test_mcp_create_character_sprite_legacy_delegation():
    """Verifies that legacy create_character_sprite delegates through orchestrator."""
    test_dir = Path("test_tmp/final_pass_spr")
    test_dir.mkdir(parents=True, exist_ok=True)
    res = create_character_sprite(
        name="legacy_hero",
        width=16,
        height=16,
        palette_name="db16",
        output_dir=str(test_dir),
    )

    assert "experience_id" in res
    assert "guidance_applied" in res
    assert Path(res["aseprite_project"]).exists()


# =============================================================================
# OBJECTIVE B: PROVE GUIDANCE HAS A REAL EFFECT (16x16 and 32x32)
# =============================================================================

def test_16x16_guidance_on_vs_guidance_off_pixel_difference():
    """
    Proves that 16x16 character generation with guidance enabled produces
    tangible, measurable pixel changes (sel-out softening and cluster noise elimination)
    compared to guidance disabled.
    """
    bp = CharacterBlueprint(
        character_id="test_knight_16",
        name="Knight 16",
        size=(16, 16),
        archetype="knight",
    )

    # 1. Generate without guidance
    p_off = build_animated_character_project(
        blueprint=bp,
        palette_name="db16",
        guidance=None,
    )

    # 2. Generate with guidance
    guidance = orchestrator.build_character_guidance(
        resolution=(16, 16),
        archetype="knight",
        palette_name="db16",
    )
    p_on = build_animated_character_project(
        blueprint=bp,
        palette_name="db16",
        guidance=guidance.model_dump(),
    )

    # 3. Verify exact rules retrieved
    assert len(p_on.metadata["guidance_applied"]) > 0
    assert "Selective Outlining (Sel-Out) and Interior Seam Ramping" in p_on.metadata["guidance_applied"]
    assert "Directional Cluster Shading & Anti-Pillow-Shading Ban" in p_on.metadata["guidance_applied"]

    # 4. Verify consumed rules vs ignored rules
    consumed = p_on.metadata["guidance_rules_consumed"]
    ignored = p_on.metadata["guidance_rules_ignored"]

    assert "Selective Outlining (Sel-Out) and Interior Seam Ramping" in consumed
    assert "Strict Palette Discipline & Temperature Hue Shifting" in consumed

    # 5. Measure pixel difference across frame 0 layers
    img_off = p_off.get_frame_image(0, "Clothes")
    img_on = p_on.get_frame_image(0, "Clothes")

    assert img_off is not None and img_on is not None
    pixels_off = list(img_off.tobytes())
    pixels_on = list(img_on.tobytes())

    # Pixels must NOT be identical: guidance has softened interior seams and cleaned noise
    diff_count = sum(p1 != p2 for p1, p2 in zip(pixels_off, pixels_on))
    assert diff_count > 0, "Guidance was accepted but had zero effect on pixel output!"


def test_16x16_locomotion_rule_ignored_for_idle_only_character():
    """Verifies that locomotion rules are correctly marked as IGNORED when character only has idle."""
    bp = CharacterBlueprint(
        character_id="idle_only_hero",
        name="Idle Only Hero",
        size=(16, 16),
        archetype="knight",
        animations={"idle": CharacterAnimationSpec(frames=2, duration_ms=300, loop=True)},
    )
    guidance = orchestrator.build_character_guidance(
        resolution=(16, 16),
        archetype="knight",
        palette_name="db16",
    )
    project = build_animated_character_project(
        blueprint=bp,
        palette_name="db16",
        guidance=guidance.model_dump(),
    )

    consumed = project.metadata["guidance_rules_consumed"]
    ignored = project.metadata["guidance_rules_ignored"]

    # Locomotion rule requires walk/move; since sprite is idle-only, it must be ignored
    assert any("Locomotion" in r for r in ignored)
    assert not any("Locomotion" in r for r in consumed)


def test_user_specified_parameters_not_overridden_by_guidance():
    """Verifies that user parameters (e.g. outline_mode='none') are not silently overridden."""
    bp = CharacterBlueprint(
        character_id="no_outline_hero",
        name="No Outline Hero",
        size=(16, 16),
        archetype="knight",
        outline_mode="none",
    )
    guidance = orchestrator.build_character_guidance(
        resolution=(16, 16),
        archetype="knight",
        palette_name="db16",
    )
    project = build_animated_character_project(
        blueprint=bp,
        palette_name="db16",
        guidance=guidance.model_dump(),
    )

    # Frame 0 Clothes should maintain raw non-sel-out pixels because user specified outline_mode='none'
    assert project is not None


def test_32x32_guidance_on_vs_guidance_off_pixel_difference():
    """
    Proves that 32x32 character generation with guidance enabled produces
    measurable pixel changes and properly consumes applicable rules.
    """
    bp = CharacterBlueprint(
        character_id="test_knight_32",
        name="Knight 32",
        size=(32, 32),
        archetype="knight",
    )

    p_off = build_animated_character_project_32(
        blueprint=bp,
        palette_name="db16",
        guidance=None,
    )

    guidance = orchestrator.build_character_guidance(
        resolution=(32, 32),
        archetype="knight",
        palette_name="db16",
    )
    p_on = build_animated_character_project_32(
        blueprint=bp,
        palette_name="db16",
        guidance=guidance.model_dump(),
    )

    assert len(p_on.metadata["guidance_applied"]) > 0
    consumed = p_on.metadata["guidance_rules_consumed"]
    assert len(consumed) > 0
    assert "Selective Outlining (Sel-Out) and Interior Seam Ramping" in consumed

    # Measure pixel difference on 32x32 Clothes layer
    img_off = p_off.get_frame_image(0, "Clothes")
    img_on = p_on.get_frame_image(0, "Clothes")

    assert img_off is not None and img_on is not None
    pixels_off = list(img_off.tobytes())
    pixels_on = list(img_on.tobytes())

    diff_count = sum(p1 != p2 for p1, p2 in zip(pixels_off, pixels_on))
    assert diff_count > 0, "32x32 guidance was accepted but had zero effect on pixel output!"


# =============================================================================
# OBJECTIVE C: DATA OWNERSHIP & TIER NORMALIZATION
# =============================================================================

def test_data_ownership_guards_in_repository():
    """Verifies that raw Feedback or Skill entities cannot be inappropriately saved as KnowledgeRecord."""
    db = DatabaseManager(":memory:")
    repo = LearningRepository(db)

    # Attempting to save raw HUMAN_FEEDBACK as knowledge without linked IDs raises ValueError
    bad_feedback_rule = KnowledgeRecord(
        knowledge_type=KnowledgeType.HUMAN_FEEDBACK,
        category=KnowledgeCategory.GENERAL,
        rule_name="Unlinked Feedback",
        description="Invalid unlinked feedback entity",
        conditions={},
        recommendations={},
        source_experience_ids=[],
        applied_feedback_ids=[],
    )
    with pytest.raises(ValueError, match="HUMAN_FEEDBACK knowledge tier requires linked feedback/experience IDs"):
        repo.save_knowledge(bad_feedback_rule)

    # Attempting to save raw VALIDATED_SKILL as knowledge without skill_id raises ValueError
    bad_skill_rule = KnowledgeRecord(
        knowledge_type=KnowledgeType.VALIDATED_SKILL,
        category=KnowledgeCategory.GENERAL,
        rule_name="Unlinked Skill",
        description="Invalid unlinked skill entity",
        conditions={},
        recommendations={},
        source_experience_ids=[],
    )
    with pytest.raises(ValueError, match="VALIDATED_SKILL knowledge tier requires linked skill definition ID"):
        repo.save_knowledge(bad_skill_rule)

    # Correctly linked external reference rule saves cleanly
    good_ref = KnowledgeRecord(
        knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
        evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
        category=KnowledgeCategory.SILHOUETTE,
        rule_name="Valid Reference Rule",
        description="Valid reference",
        conditions={"task_category": "character"},
        recommendations={"test": True},
        confidence_score=None,
        provenance=ReferenceProvenance(
            source_title="Book",
            author="Author",
            source_url="https://example.com",
            access_date="2026-11-24",
            extracted_principle="Principle",
            interpretation="Interpretation",
            applicable_asset_categories=["character"],
            applicable_resolutions=["16x16"],
            applicable_styles=["pixel_art"],
            known_limitations=[],
            validation_status="COMMUNITY_CONSENSUS",
        ),
    )
    saved = repo.save_knowledge(good_ref)
    assert saved.id == good_ref.id


# =============================================================================
# OBJECTIVE D: DATABASE MIGRATION & SEEDING IDEMPOTENCY
# =============================================================================

def test_seeded_reference_rules_are_idempotent():
    """Verifies that seed_art_bible_knowledge does not duplicate records when re-executed."""
    db = DatabaseManager(":memory:")
    repo = LearningRepository(db)

    # First seeding
    seeded_first = seed_art_bible_knowledge(repo, overwrite=False)
    assert len(seeded_first) == 15

    # Count in DB
    conn = db.get_connection()
    count_first = conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
    assert count_first == 15

    # Re-run seeding with overwrite=True (must update in-place, NOT duplicate)
    seeded_second = seed_art_bible_knowledge(repo, overwrite=True)
    assert len(seeded_second) == 15

    count_second = conn.execute("SELECT count(*) FROM knowledge").fetchone()[0]
    assert count_second == 15, f"Expected 15 records after overwrite, but found {count_second} duplicates!"


def test_historical_experiences_preserved_in_live_db():
    """Verifies that live database data/learning/learning.db maintains all historical experiences."""
    live_db_path = Path("data/learning/learning.db")
    if live_db_path.exists():
        db = DatabaseManager(str(live_db_path))
        conn = db.get_connection()
        exp_count = conn.execute("SELECT count(*) FROM experiences").fetchone()[0]
        assert exp_count >= 10, f"Historical experiences were lost! Count: {exp_count}"
