"""
Tests for Sprint 0.5: Skill Registry & Skill Builder MVP.
Verifies SkillBuilder draft composition, tool validation, security checks,
SkillRegistry querying, trigger matching, and filesystem serialization.
"""

import json
from pathlib import Path
import pytest

from libresprite_game_mcp.learning.models import ExperienceRecord, OutcomeType
from libresprite_game_mcp.skills.builder import (
    APPROVED_MCP_TOOLS,
    InvalidWorkflowError,
    SkillBuilder,
)
from libresprite_game_mcp.skills.models import SkillDefinition, SkillStatus, WorkflowStep
from libresprite_game_mcp.skills.registry import SkillRegistry
from libresprite_game_mcp.skills.repository import ImmutableSkillError, SkillRepository
from libresprite_game_mcp.skills.versioning import bump_semver
from libresprite_game_mcp.storage.database import DatabaseManager


@pytest.fixture
def skill_system(tmp_path):
    db = DatabaseManager(":memory:")
    repo = SkillRepository(db)
    registry = SkillRegistry(repo, skills_dir=tmp_path / "skills")
    builder = SkillBuilder()
    yield registry, builder, repo
    db.close()


# -----------------------------------------------------------------------------
# 1. Skill Builder & Tool Allowlist Tests
# -----------------------------------------------------------------------------
def test_skill_builder_valid_draft(skill_system):
    _registry, builder, _repo = skill_system

    workflow = [
        WorkflowStep(
            step_id="step_gen",
            tool_name="generate_character",
            parameters={"size": [16, 16], "proportion": "chibi_1_2"},
        ),
        WorkflowStep(
            step_id="step_outline",
            tool_name="apply_outline",
            parameters={"mode": "colored", "source_step": "step_gen"},
        ),
        WorkflowStep(
            step_id="step_export",
            tool_name="export_godot_spritesheet",
            parameters={"source_step": "step_outline"},
        ),
    ]

    skill = builder.create_draft(
        skill_id="chibi_godot_pipeline",
        name="Chibi Character Godot Pipeline",
        description="Generates chibi character and exports to Godot",
        workflow=workflow,
        trigger_conditions={"task_category": "character", "proportion": "chibi_1_2"},
    )

    assert skill.skill_id == "chibi_godot_pipeline"
    assert skill.status == SkillStatus.DRAFT
    assert set(skill.required_tools) == {"generate_character", "apply_outline", "export_godot_spritesheet"}


def test_skill_builder_rejects_unapproved_tools(skill_system):
    _registry, builder, _repo = skill_system

    unauthorized_workflow = [
        WorkflowStep(
            step_id="step_evil",
            tool_name="unauthorized_custom_eval_tool",
            parameters={},
        ),
    ]

    with pytest.raises(InvalidWorkflowError) as exc_info:
        builder.create_draft(
            skill_id="malicious_skill",
            name="Malicious Skill",
            description="Tries to run unauthorized tool",
            workflow=unauthorized_workflow,
        )
    assert "not in the approved tool allowlist" in str(exc_info.value)


def test_skill_builder_security_rejection(skill_system):
    _registry, builder, _repo = skill_system

    injected_workflow = [
        WorkflowStep(
            step_id="step_inject",
            tool_name="generate_character",
            parameters={"extra_code": "eval('import os; os.system(...)')"},
        ),
    ]

    with pytest.raises(InvalidWorkflowError) as exc_info:
        builder.create_draft(
            skill_id="injected_skill",
            name="Injection Attempt",
            description="Attempts code injection in parameters",
            workflow=injected_workflow,
        )
    assert "forbidden keyword" in str(exc_info.value)


def test_skill_builder_invalid_step_dependency(skill_system):
    _registry, builder, _repo = skill_system

    bad_order_workflow = [
        WorkflowStep(
            step_id="step_1",
            tool_name="apply_outline",
            parameters={"source_step": "step_future"},  # References step that hasn't run!
        ),
        WorkflowStep(
            step_id="step_future",
            tool_name="generate_character",
            parameters={},
        ),
    ]

    with pytest.raises(InvalidWorkflowError) as exc_info:
        builder.create_draft(
            skill_id="bad_order_skill",
            name="Bad Order",
            description="Invalid dependency reference",
            workflow=bad_order_workflow,
        )
    assert "references previous step 'step_future' which has not executed yet" in str(exc_info.value)


# -----------------------------------------------------------------------------
# 2. Skill Registry & Matching Tests
# -----------------------------------------------------------------------------
def test_skill_registry_matching_and_approval_filtering(skill_system):
    registry, builder, repo = skill_system

    workflow = [
        WorkflowStep(step_id="step_1", tool_name="generate_item", parameters={"category": "potion"}),
    ]
    skill = builder.create_draft(
        skill_id="potion_crafting",
        name="Potion Crafter",
        description="Generates standard 16x16 potions",
        workflow=workflow,
        version="1.0.0",
        trigger_conditions={"task_category": "item", "item_type": "potion"},
        art_profile_compatibility=["RetroFantasy"],
    )

    # 1. Register as DRAFT
    registry.register_skill(skill)

    # In production mode (allow_unapproved=False), DRAFT skills should NOT match
    matches_prod = registry.find_matching_skills(
        context={"task_category": "item", "item_type": "potion"},
        art_profile_name="RetroFantasy",
        allow_unapproved=False,
    )
    assert len(matches_prod) == 0

    # In sandbox/testing mode (allow_unapproved=True), it should match
    matches_sandbox = registry.find_matching_skills(
        context={"task_category": "item", "item_type": "potion"},
        art_profile_name="RetroFantasy",
        allow_unapproved=True,
    )
    assert len(matches_sandbox) == 1
    assert matches_sandbox[0].skill_id == "potion_crafting"

    # 2. Promote to APPROVED
    repo.update_skill_status(
        skill_id="potion_crafting",
        version="1.0.0",
        new_status=SkillStatus.APPROVED,
        reviewer="LeadArtist",
    )

    # Now production query finds it
    matches_prod_after = registry.find_matching_skills(
        context={"task_category": "item", "item_type": "potion"},
        art_profile_name="RetroFantasy",
        allow_unapproved=False,
    )
    assert len(matches_prod_after) == 1
    assert matches_prod_after[0].skill_id == "potion_crafting"

    # Incompatible art profile fails match
    matches_wrong_profile = registry.find_matching_skills(
        context={"task_category": "item", "item_type": "potion"},
        art_profile_name="SciFiNeon",
        allow_unapproved=False,
    )
    assert len(matches_wrong_profile) == 0


def test_skill_filesystem_sync(skill_system):
    registry, builder, _repo = skill_system

    workflow = [WorkflowStep(step_id="step_1", tool_name="generate_tileset", parameters={})]
    skill = builder.create_draft(
        skill_id="forest_tileset",
        name="Forest Tileset Generator",
        description="Creates 16x16 autotile forest",
        workflow=workflow,
        version="1.0.0",
    )

    manifest_path = registry.export_to_filesystem(skill)
    assert manifest_path.exists()
    assert manifest_path.name == "skill.json"

    # Re-import into a clean repository
    new_db = DatabaseManager(":memory:")
    new_repo = SkillRepository(new_db)
    new_registry = SkillRegistry(new_repo)

    imported_skill = new_registry.import_from_filesystem(manifest_path)
    assert imported_skill.skill_id == "forest_tileset"
    assert imported_skill.version == "1.0.0"
    assert imported_skill.name == "Forest Tileset Generator"
    new_db.close()
