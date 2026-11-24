"""
Tests for Sprint 0.4: Experience Collection & Knowledge Management.
Verifies ExperienceCollector, FeedbackCollector, Normalizer, OutcomeEvaluator,
KnowledgeManager, and KnowledgeRetriever.
"""

import pytest
from libresprite_game_mcp.learning.collector import ExperienceCollector, FeedbackCollector
from libresprite_game_mcp.learning.evaluator import OutcomeEvaluator
from libresprite_game_mcp.learning.knowledge import KnowledgeManager, KnowledgeRetriever
from libresprite_game_mcp.learning.models import (
    FeedbackType,
    KnowledgeCategory,
    OutcomeType,
)
from libresprite_game_mcp.learning.normalizer import ExperienceNormalizer
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.storage.database import DatabaseManager


@pytest.fixture
def repo():
    db = DatabaseManager(":memory:")
    yield LearningRepository(db)
    db.close()


# -----------------------------------------------------------------------------
# 1. Experience Normalizer & Credential Cleansing Tests
# -----------------------------------------------------------------------------
def test_normalizer_sanitization():
    normalizer = ExperienceNormalizer()
    payload = {
        "user_id": "artist_1",
        "session_token": "secret_session_token_12345",
        "nested": {
            "api_key": "private_api_key",
            "safe_param": "standard_val",
        },
    }
    cleaned = normalizer.sanitize_payload(payload)
    assert cleaned["user_id"] == "artist_1"
    assert cleaned["session_token"] == "[MASKED]"
    assert cleaned["nested"]["api_key"] == "[MASKED]"
    assert cleaned["nested"]["safe_param"] == "standard_val"


def test_normalizer_resolution_extraction():
    normalizer = ExperienceNormalizer()
    assert normalizer.extract_resolution({"resolution": [32, 64]}) == (32, 64)
    assert normalizer.extract_resolution({"size": (24, 24)}) == (24, 24)
    assert normalizer.extract_resolution({"dimensions": "16x16"}) == (16, 16)
    assert normalizer.extract_resolution({}) == (16, 16)


# -----------------------------------------------------------------------------
# 2. Outcome Evaluator Tests
# -----------------------------------------------------------------------------
def test_outcome_evaluator_qa_report():
    evaluator = OutcomeEvaluator()

    # Clean pass
    outcome, score, notes = evaluator.evaluate(
        qa_report={"passed": True, "critical_errors": [], "warnings": []}
    )
    assert outcome == OutcomeType.SUCCESS
    assert score == 1.0

    # Critical errors -> failure
    outcome, score, notes = evaluator.evaluate(
        qa_report={"passed": False, "critical_errors": ["Floating orphan pixels detected"], "warnings": []}
    )
    assert outcome == OutcomeType.FAILURE
    assert score <= 0.4
    assert any("QA Critical Errors" in n for n in notes)

    # Runtime error
    outcome, score, notes = evaluator.evaluate(execution_error="LibreSprite process timeout")
    assert outcome == OutcomeType.FAILURE
    assert score == 0.0


# -----------------------------------------------------------------------------
# 3. Experience & Feedback Collector Tests
# -----------------------------------------------------------------------------
def test_experience_collector(repo):
    collector = ExperienceCollector(repo)

    exp = collector.record_task_run(
        task_id="task_character_01",
        task_category="character",
        asset_category="sprite",
        input_context={
            "resolution": (16, 16),
            "session_token": "should_be_masked",
            "prompt": "goblin rogue",
        },
        output_summary={"frames": 1},
        tools_used=["generate_character"],
        execution_time_ms=75.0,
        qa_report={"passed": True, "critical_errors": [], "warnings": []},
        art_profile={"palette_name": "db16", "engine": "godot_4"},
    )

    assert exp.id is not None
    assert exp.outcome == OutcomeType.SUCCESS
    assert exp.input_context["session_token"] == "[MASKED]"
    assert "character" in exp.tags
    assert "16x16" in exp.tags
    assert "palette:db16" in exp.tags

    retrieved = repo.get_experience(exp.id)
    assert retrieved is not None
    assert retrieved.task_id == "task_character_01"


def test_feedback_collector(repo):
    collector = ExperienceCollector(repo)
    feedback_collector = FeedbackCollector(repo)

    exp = collector.record_task_run(
        task_id="task_feedback_01",
        task_category="item",
        resolution=(16, 16),
    )

    # Success feedback
    fb = feedback_collector.record_feedback(
        experience_id=exp.id,
        feedback_type=FeedbackType.APPROVAL,
        user_rating=5.0,
        notes="Pixel-perfect weapon",
    )
    assert fb.id is not None
    assert fb.user_rating == 5.0

    feedbacks = repo.get_feedbacks_for_experience(exp.id)
    assert len(feedbacks) == 1
    assert feedbacks[0].notes == "Pixel-perfect weapon"

    # Feedback on non-existent experience must raise ValueError
    with pytest.raises(ValueError):
        feedback_collector.record_feedback(
            experience_id="non_existent",
            feedback_type=FeedbackType.REJECTION,
        )


# -----------------------------------------------------------------------------
# 4. Knowledge Manager & Retriever Tests
# -----------------------------------------------------------------------------
def test_knowledge_manager_and_confidence_adjustments(repo):
    km = KnowledgeManager(repo)

    rule = km.add_rule(
        rule_name="Dithering Prohibition for Small Sprites",
        category=KnowledgeCategory.DITHERING,
        description="Avoid Bayer dithering on <= 16x16 sprites to prevent visual noise.",
        conditions={"resolution": "16x16"},
        recommendations={"dithering": False},
        initial_confidence=0.6,
    )
    assert rule.confidence_score == 0.6

    # Positive evidence (Success)
    rule = km.update_confidence(rule.id, outcome=OutcomeType.SUCCESS)
    assert rule.confidence_score == 0.65

    # Negative evidence (Failure)
    rule = km.update_confidence(rule.id, outcome=OutcomeType.FAILURE)
    assert rule.confidence_score == 0.50

    # Bounds: confidence cannot exceed 1.0 or fall below 0.0
    for _ in range(15):
        rule = km.update_confidence(rule.id, outcome=OutcomeType.SUCCESS)
    assert rule.confidence_score == 1.0


def test_knowledge_retriever_and_guidance(repo):
    km = KnowledgeManager(repo)
    retriever = KnowledgeRetriever(repo)

    # Universal rule
    km.add_rule(
        rule_name="Standard Dark Outline",
        category=KnowledgeCategory.OUTLINE,
        description="Outline rule for sprites",
        conditions={"task_category": "character"},
        recommendations={"outline_mode": "colored"},
        initial_confidence=0.85,
    )

    # Project-specific rule for RPGGame
    km.add_rule(
        rule_name="RPGGame DB16 Rule",
        category=KnowledgeCategory.PALETTE,
        description="Palette for RPGGame",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "db16"},
        project_id="RPGGame",
        initial_confidence=0.90,
    )

    # Project-specific rule for SciFiGame
    km.add_rule(
        rule_name="SciFi Neon Palette",
        category=KnowledgeCategory.PALETTE,
        description="Palette for SciFiGame",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "neon8"},
        project_id="SciFiGame",
        initial_confidence=0.90,
    )

    # Query for RPGGame: must include universal outline + RPGGame DB16, but NOT SciFi Neon
    rpg_rules = retriever.retrieve_applicable_rules(
        project_id="RPGGame",
        task_category="character",
    )
    rule_names = [r.rule_name for r in rpg_rules]
    assert "Standard Dark Outline" in rule_names
    assert "RPGGame DB16 Rule" in rule_names
    assert "SciFi Neon Palette" not in rule_names

    # Format guidance
    guidance = retriever.format_guidance(rpg_rules)
    assert "db16" in guidance["palettes"]
    assert "colored" in guidance["outlines"]
    assert len(guidance["constraints"]) == 2
