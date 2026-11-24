"""
Tests for Learning Layer Art Bible Knowledge Ingestion & Retrieval.
Verifies that foundational pixel art rules (derived from Sandro Maglione, vysnvnt,
Brandon James Greer, MortMort, and Saint11) are properly seeded, retrieved,
and dynamically updated through feedback.
"""

import pytest
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.learning.models import KnowledgeCategory, KnowledgeType
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.learning.seed_knowledge import (
    get_pixel_art_knowledge_rules,
    seed_art_bible_knowledge,
)
from libresprite_game_mcp.storage.database import DatabaseManager


@pytest.fixture
def memory_repo():
    db = DatabaseManager(":memory:")
    yield LearningRepository(db)
    db.close()


@pytest.fixture
def memory_orchestrator(tmp_path):
    orch = ProductionOrchestrator(
        db_path=":memory:",
        skills_dir=tmp_path / "skills",
    )
    yield orch
    orch.db.close()


def test_seed_art_bible_knowledge_idempotency(memory_repo):
    """Verifies that seeding populates foundational rules (including VFX/spells) and repeated execution is idempotent."""
    rules_init = memory_repo.query_knowledge(limit=100)
    assert len(rules_init) == 0

    # First seeding
    seeded_1 = seed_art_bible_knowledge(memory_repo)
    assert len(seeded_1) == 15

    rules_after_1 = memory_repo.query_knowledge(limit=100)
    assert len(rules_after_1) == 15

    # Verify categories present
    categories = {r.category for r in rules_after_1}
    assert KnowledgeCategory.SILHOUETTE in categories
    assert KnowledgeCategory.PALETTE in categories
    assert KnowledgeCategory.LIGHTING in categories
    assert KnowledgeCategory.OUTLINE in categories
    assert KnowledgeCategory.COMPOSITION in categories
    assert KnowledgeCategory.ANIMATION_TIMING in categories
    assert KnowledgeCategory.DITHERING in categories
    assert KnowledgeCategory.VFX_SPELLS in categories
    assert KnowledgeCategory.GENERAL in categories

    # Second seeding (must not duplicate)
    seeded_2 = seed_art_bible_knowledge(memory_repo)
    assert len(seeded_2) == 15

    rules_after_2 = memory_repo.query_knowledge(limit=100)
    assert len(rules_after_2) == 15


def test_orchestrator_guidance_includes_art_bible_rules(memory_orchestrator):
    """Verifies ProductionOrchestrator automatically seeds rules and returns actionable guidance."""
    guidance = memory_orchestrator.get_knowledge_guidance(
        task_category="character",
        resolution=(32, 32),
    )

    assert "db16" in guidance["palettes"]
    assert "colored" in guidance["outlines"]
    assert len(guidance["constraints"]) >= 8

    # Verify recommendations contain key Art Bible parameters
    recs = guidance["recommendations"]
    assert recs.get("recommended_palette") == "db16"
    assert recs.get("silhouette_test") == "black_mask"
    assert recs.get("light_source") == "top_left_45_deg"
    assert recs.get("disallow_jaggies") is True
    assert recs.get("purge_doubles") is True
    assert recs.get("pillow_shading_allowed") is False


def test_knowledge_rule_confidence_propagation_with_feedback(memory_orchestrator, tmp_path):
    """Verifies that user feedback on a task updates confidence on the relevant seeded Art Bible rule."""
    memory_orchestrator.approve_reference_skill("pixel_character_consistency")
    ws = tmp_path / "art_output"

    # Execute reference skill
    result = memory_orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "test_paladin"},
        project_id="ProjectArtBible",
        workspace=ws,
    )
    assert result["status"] == "success"
    exp_id = result["experience_id"]

    # Locate seeded lighting rule
    lighting_rules = [
        r for r in memory_orchestrator.learning_repo.query_knowledge()
        if r.category == KnowledgeCategory.LIGHTING
    ]
    assert len(lighting_rules) >= 1
    target_rule = lighting_rules[0]
    initial_score = target_rule.confidence_score

    # Submit user feedback targeting lighting
    fb = memory_orchestrator.record_feedback(
        experience_id=exp_id,
        feedback_type="approval",
        user_rating=5.0,
        notes="Directional lighting and cluster drop shadows are crisp and well-placed.",
        idempotency_key="lighting_fb_key_001",
    )
    assert fb.id is not None

    # Verify confidence or protected status
    updated_rule = memory_orchestrator.learning_repo.get_knowledge(target_rule.id)
    if target_rule.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE:
        # Seeded literature citations are protected immutable references
        assert updated_rule.confidence_score is None
    else:
        assert updated_rule.confidence_score >= (initial_score or 0.5)


def test_project_isolation_with_seeded_universal_rules(memory_orchestrator):
    """Verifies universal Art Bible rules coexist with project-specific overrides."""
    # Add a project-specific palette override for ProjectMonochrome
    custom_rule = memory_orchestrator.knowledge_manager.add_rule(
        rule_name="Monochrome 1-Bit Palette Rule",
        category=KnowledgeCategory.PALETTE,
        description="Strict 1-bit black and white palette for ProjectMonochrome",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "1bit_bw"},
        project_id="ProjectMonochrome",
        initial_confidence=0.99,
    )

    # Query guidance for ProjectMonochrome
    guidance = memory_orchestrator.get_knowledge_guidance(
        project_id="ProjectMonochrome",
        task_category="character",
    )
    # The highest confidence palette recommendation takes precedence
    assert guidance["recommendations"]["recommended_palette"] == "1bit_bw"
    assert "1bit_bw" in guidance["palettes"]
    assert "db16" in guidance["palettes"]

    # Query guidance for DefaultProject (must NOT contain ProjectMonochrome rules)
    default_guidance = memory_orchestrator.get_knowledge_guidance(
        project_id="DefaultProject",
        task_category="character",
    )
    assert "1bit_bw" not in default_guidance["palettes"]
    assert "db16" in default_guidance["palettes"]
