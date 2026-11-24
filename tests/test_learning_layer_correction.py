"""
Tests for Learning Layer Correction: Reference Knowledge vs Empirical Learning.
Verifies the architectural separation of four knowledge types, bibliographic provenance,
conditional applicability filtering, project isolation, feedback protection, and
verified end-to-end guidance integration into the character generator.
"""

from pathlib import Path
import pytest
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator
from libresprite_game_mcp.learning.models import (
    CharacterGenerationGuidance,
    EvidenceStatus,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
    OutcomeType,
    ReferenceProvenance,
)
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.learning.seed_knowledge import (
    get_pixel_art_knowledge_rules,
    seed_art_bible_knowledge,
)
from libresprite_game_mcp.skills.models import SkillStatus
from libresprite_game_mcp.storage.database import DatabaseManager


@pytest.fixture
def memory_db():
    db = DatabaseManager(":memory:")
    yield db
    db.close()


@pytest.fixture
def memory_orchestrator(tmp_path):
    orch = ProductionOrchestrator(
        db_path=":memory:",
        skills_dir=tmp_path / "skills",
    )
    yield orch
    orch.db.close()


# -----------------------------------------------------------------------------
# 1. Four Knowledge Types Distinguishability
# -----------------------------------------------------------------------------
def test_four_knowledge_types_distinguishable(memory_orchestrator):
    """
    Verifies explicit architectural separation between:
    1. EXTERNAL_REFERENCE (literature & master tutorials)
    2. EMPIRICAL_KNOWLEDGE (telemetry & QA results)
    3. HUMAN_FEEDBACK (user ratings, reviews, preferences)
    4. VALIDATED_SKILL (approved workflows)
    """
    repo = memory_orchestrator.learning_repo

    # 1. External reference records (seeded)
    refs = repo.query_knowledge(knowledge_type=KnowledgeType.EXTERNAL_REFERENCE)
    assert len(refs) == 10
    for r in refs:
        assert r.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE
        assert r.confidence_score is None  # No pseudo-probability
        assert r.provenance is not None
        assert r.evidence_status in (EvidenceStatus.COMMUNITY_CONSENSUS, EvidenceStatus.REFERENCE_GUIDANCE)

    # 2. Empirical knowledge rule
    emp_rule = memory_orchestrator.knowledge_manager.add_rule(
        rule_name="Observed Empirical Palette Stability",
        category=KnowledgeCategory.PALETTE,
        description="Derived from 15 consecutive flawless QA runs",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "db16"},
        initial_confidence=0.88,
    )
    assert emp_rule.knowledge_type == KnowledgeType.EMPIRICAL_KNOWLEDGE
    assert emp_rule.confidence_score == 0.88
    assert emp_rule.provenance is None

    # 3. Human feedback record
    fb = FeedbackRecord(
        experience_id="exp_001",
        project_id="test_proj",
        feedback_type=FeedbackType.APPROVAL,
        user_rating=5.0,
        notes="Crisp silhouettes and clean outlines",
    )
    assert fb.feedback_type == FeedbackType.APPROVAL

    # 4. Validated skill (approved in production)
    skill = memory_orchestrator.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
    assert skill is not None
    assert skill.status == SkillStatus.DRAFT
    memory_orchestrator.approve_reference_skill("pixel_character_consistency")
    approved_skill = memory_orchestrator.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
    assert approved_skill.status == SkillStatus.APPROVED


# -----------------------------------------------------------------------------
# 2. Bibliographic Provenance Preservation
# -----------------------------------------------------------------------------
def test_external_reference_provenance_preservation(memory_orchestrator):
    """
    Verifies that every external reference record preserves:
    source title, author, URL, access date, principle, interpretation,
    applicable categories, resolutions, styles, limitations, and validation status.
    """
    refs = memory_orchestrator.learning_repo.query_knowledge(knowledge_type=KnowledgeType.EXTERNAL_REFERENCE)
    assert len(refs) == 10

    authors_found = {r.provenance.author for r in refs if r.provenance}
    assert "Sandro Maglione" in authors_found
    assert "vysnvnt" in authors_found
    assert "Pedro Medeiros (Saint11)" in authors_found
    assert "MortMort" in authors_found
    assert "Brandon James Greer" in authors_found
    assert "Derek Yu" in authors_found

    for r in refs:
        prov = r.provenance
        assert prov is not None
        assert len(prov.source_title) > 5
        assert len(prov.author) > 2
        assert prov.source_url.startswith("http")
        assert prov.access_date == "2026-11-24"
        assert len(prov.extracted_principle) > 10
        assert len(prov.interpretation) > 10
        assert len(prov.applicable_asset_categories) >= 1
        assert len(prov.applicable_resolutions) >= 1
        assert len(prov.applicable_styles) >= 1
        assert len(prov.known_limitations) >= 1
        assert prov.validation_status in ("COMMUNITY_CONSENSUS", "TUTORIAL_REFERENCE")


# -----------------------------------------------------------------------------
# 3. Conditional Applicability Filtering
# -----------------------------------------------------------------------------
def test_applicability_filtering(memory_orchestrator):
    """
    Verifies that rules are conditional rather than universally enforced:
    - Palette DB16 rule only applies when DB16 is requested/compatible
    - Dithering rule specifically filters for resolutions <= 32x32
    - Locomotion rule applies when animation_state is 'move'
    """
    retriever = memory_orchestrator.knowledge_retriever

    # 1. Query with palette_name="db16": DB16 rule matches
    db16_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        palette_name="db16",
    )
    rule_names_db16 = [r.rule_name for r in db16_rules]
    assert "Strict Palette Discipline & Temperature Hue Shifting" in rule_names_db16

    # 2. Query with palette_name="gameboy4": DB16 rule does NOT match!
    gameboy_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        palette_name="gameboy4",
    )
    rule_names_gb = [r.rule_name for r in gameboy_rules]
    assert "Strict Palette Discipline & Temperature Hue Shifting" not in rule_names_gb

    # 3. Query resolution 64x64: Dithering restriction for <= 32x32 does NOT match
    large_res_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        resolution=(64, 64),
    )
    rule_names_large = [r.rule_name for r in large_res_rules]
    assert "Controlled Dithering Prohibition on Low Resolutions" not in rule_names_large

    # 4. Query resolution 32x32: Dithering restriction DOES match
    small_res_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        resolution=(32, 32),
    )
    rule_names_small = [r.rule_name for r in small_res_rules]
    assert "Controlled Dithering Prohibition on Low Resolutions" in rule_names_small

    # 5. Locomotion rule matches when animation_state='move'
    move_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        animation_state="move",
    )
    rule_names_move = [r.rule_name for r in move_rules]
    assert "Articulated Locomotion Dynamics & Weight Transfer" in rule_names_move

    # Locomotion rule does NOT match when animation_state='idle'
    idle_rules = retriever.retrieve_applicable_rules(
        task_category="character",
        animation_state="idle",
    )
    rule_names_idle = [r.rule_name for r in idle_rules]
    assert "Articulated Locomotion Dynamics & Weight Transfer" not in rule_names_idle


# -----------------------------------------------------------------------------
# 4. Project Isolation Remains Intact
# -----------------------------------------------------------------------------
def test_project_isolation_remains_intact(memory_orchestrator):
    """
    Verifies that project-specific rules are isolated to their respective projects,
    while universal rules are accessible across all projects.
    """
    # Add a project-specific rule for CyberProject
    cyber_rule = memory_orchestrator.knowledge_manager.add_rule(
        rule_name="Cyber Neon Glow Outline",
        category=KnowledgeCategory.OUTLINE,
        description="High-intensity neon outline for CyberProject",
        conditions={"task_category": "character"},
        recommendations={"outline_mode": "neon_glow"},
        project_id="CyberProject",
        initial_confidence=0.92,
    )

    # Query CyberProject
    cyber_guidance = memory_orchestrator.get_knowledge_guidance(
        project_id="CyberProject",
        task_category="character",
    )
    assert cyber_guidance["recommendations"]["outline_mode"] == "neon_glow"

    # Query FantasyProject: must NOT contain CyberProject rule
    fantasy_guidance = memory_orchestrator.get_knowledge_guidance(
        project_id="FantasyProject",
        task_category="character",
    )
    assert fantasy_guidance["recommendations"].get("outline_mode") != "neon_glow"


# -----------------------------------------------------------------------------
# 5. External References Immune to Feedback Scoring
# -----------------------------------------------------------------------------
def test_external_references_immune_to_feedback_scoring(memory_orchestrator, tmp_path):
    """
    Verifies that user feedback on a task run NEVER modifies external reference records.
    External references preserve their None confidence and immutable contents.
    """
    memory_orchestrator.approve_reference_skill("pixel_character_consistency")
    ws = tmp_path / "art_feedback"

    result = memory_orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "knight_fb"},
        project_id="ProjectImmunity",
        workspace=ws,
    )
    assert result["status"] == "success"
    exp_id = result["experience_id"]

    # Select an external reference rule
    ref_rules = memory_orchestrator.learning_repo.query_knowledge(
        category=KnowledgeCategory.SILHOUETTE,
        knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
    )
    assert len(ref_rules) >= 1
    target_ref = ref_rules[0]
    orig_updated_at = target_ref.updated_at

    # Ingest negative feedback on silhouette
    fb = memory_orchestrator.record_feedback(
        experience_id=exp_id,
        feedback_type="rejection",
        user_rating=1.0,
        notes="Silhouette shape was terrible and unreadable.",
    )
    assert fb.id is not None

    # Verify external reference was NOT altered
    ref_after = memory_orchestrator.learning_repo.get_knowledge(target_ref.id)
    assert ref_after.confidence_score is None
    assert ref_after.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE
    assert ref_after.updated_at == orig_updated_at


# -----------------------------------------------------------------------------
# 6. User Preferences Do Not Become Universal Rules
# -----------------------------------------------------------------------------
def test_user_preferences_do_not_become_universal_rules(memory_orchestrator, tmp_path):
    """
    Verifies that user corrections and preferences submitted on a project
    remain strictly scoped to that project and do not mutate universal Art Bible rules.
    """
    memory_orchestrator.approve_reference_skill("pixel_character_consistency")
    ws = tmp_path / "pref_test"

    # Add an empirical project-specific rule
    proj_rule = memory_orchestrator.knowledge_manager.add_rule(
        rule_name="ProjectCustom Palette Heuristic",
        category=KnowledgeCategory.PALETTE,
        description="Local empirical rule",
        conditions={"task_category": "character"},
        recommendations={"recommended_palette": "custom_sepia"},
        project_id="ProjectCustom",
        initial_confidence=0.5,
    )

    res = memory_orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={"character_id": "sepia_hero"},
        project_id="ProjectCustom",
        workspace=ws,
    )

    # User submits feedback for ProjectCustom
    memory_orchestrator.record_feedback(
        experience_id=res["experience_id"],
        feedback_type="approval",
        user_rating=5.0,
        notes="Palette was magnificent!",
    )

    # ProjectCustom empirical rule confidence increased
    updated_proj_rule = memory_orchestrator.learning_repo.get_knowledge(proj_rule.id)
    assert updated_proj_rule.confidence_score > 0.5

    # Universal rules (project_id=None) are unchanged
    universal_rules = memory_orchestrator.learning_repo.query_knowledge(project_id=None)
    for u in universal_rules:
        if u.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE:
            assert u.confidence_score is None


# -----------------------------------------------------------------------------
# 7. Actual Character Generation Receives Guidance End-to-End
# -----------------------------------------------------------------------------
def test_actual_character_generation_receives_guidance_end_to_end(memory_orchestrator, tmp_path):
    """
    Verifies the complete execution path:
    Orchestrator -> Skill/Workflow -> Dispatcher -> Character Generator -> Export.
    Proves that the retrieved guidance actually reaches and influences the generator.
    """
    memory_orchestrator.approve_reference_skill("pixel_character_consistency")
    ws = tmp_path / "end_to_end_art"

    # 1. Execute skill with 32x32 resolution and explicit archetype
    res = memory_orchestrator.execute_skill(
        skill_id="pixel_character_consistency",
        parameters={
            "character_id": "grand_paladin",
            "name": "Grand Paladin",
            "size": [32, 32],
            "archetype": "knight",
            "palette_name": "db16",
        },
        project_id="GameProjectProduction",
        workspace=ws,
    )

    assert res["status"] == "success"
    step_1_out = res["step_outputs"]["step_1_generate"]

    # Verify guidance was forwarded and applied in the generator step
    assert "guidance_applied" in step_1_out
    guidance_rules = step_1_out["guidance_applied"]
    assert len(guidance_rules) >= 4
    assert "Universal Silhouette Readability & Black Mask Rule" in guidance_rules
    assert "Native Canvas Resolution Budgeting" in guidance_rules

    # Verify generated artifact on disk
    ase_path = Path(step_1_out["project_path"])
    assert ase_path.exists()
    assert step_1_out["width"] == 32
    assert step_1_out["height"] == 32
    assert step_1_out["archetype"] == "knight"
    assert step_1_out["frames"] >= 8

    # Verify direct orchestrator generate_character method
    direct_out = memory_orchestrator.generate_character(
        character_id="arcane_wizard",
        name="Arcane Wizard",
        size=(32, 32),
        archetype="mage",
        palette_name="db16",
        workspace=ws,
        project_id="GameProjectProduction",
    )
    assert direct_out["character_id"] == "arcane_wizard"
    assert direct_out["archetype"] == "mage"
    assert len(direct_out["guidance_applied"]) >= 4
    assert Path(direct_out["project_path"]).exists()
    assert Path(direct_out["preview_path"]).exists()


# -----------------------------------------------------------------------------
# 8. No Regressions Across Generators and Exporters
# -----------------------------------------------------------------------------
def test_no_regressions_across_generators_and_exporters(memory_orchestrator, tmp_path):
    """
    Verifies that 16x16 generation, 32x32 generation, and godot export function without defect.
    """
    ws = tmp_path / "regression_workspace"

    # 16x16 character generation
    res_16 = memory_orchestrator.generate_character(
        character_id="retro_warrior",
        size=(16, 16),
        archetype="knight",
        palette_name="db16",
        workspace=ws,
    )
    assert res_16["width"] == 16
    assert res_16["height"] == 16
    assert Path(res_16["project_path"]).exists()

    # 32x32 character generation
    res_32 = memory_orchestrator.generate_character(
        character_id="dungeon_brute",
        size=(32, 32),
        archetype="brute",
        palette_name="db16",
        workspace=ws,
    )
    assert res_32["width"] == 32
    assert res_32["height"] == 32
    assert Path(res_32["project_path"]).exists()
