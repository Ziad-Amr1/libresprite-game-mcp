"""
Production Orchestrator for LibreSprite Game MCP.
Integrates MCP tools with the Learning Layer, Knowledge Retrieval, and Skill Registry.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from libresprite_game_mcp.learning.collector import ExperienceCollector, FeedbackCollector
from libresprite_game_mcp.learning.evaluator import OutcomeEvaluator
from libresprite_game_mcp.learning.knowledge import KnowledgeManager, KnowledgeRetriever
from libresprite_game_mcp.learning.models import (
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    OutcomeType,
)
from libresprite_game_mcp.learning.normalizer import ExperienceNormalizer
from libresprite_game_mcp.learning.repository import LearningRepository
from libresprite_game_mcp.skills.lifecycle import SkillLifecycleManager
from libresprite_game_mcp.skills.models import (
    SkillDefinition,
    SkillExecutionResult,
    SkillStatus,
    WorkflowStep,
)
from libresprite_game_mcp.skills.registry import SkillRegistry
from libresprite_game_mcp.skills.repository import SkillRepository
from libresprite_game_mcp.storage.database import DatabaseManager


class ProductionOrchestrator:
    """Coordinates skill execution, automated QA, experience recording, and knowledge retrieval."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        skills_dir: Optional[Path] = None,
        tool_dispatcher: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self.db = DatabaseManager(db_path)
        self.learning_repo = LearningRepository(self.db)
        self.skill_repo = SkillRepository(self.db)
        self.skill_registry = SkillRegistry(self.skill_repo, skills_dir=skills_dir)
        self.lifecycle = SkillLifecycleManager(self.skill_repo)

        self.normalizer = ExperienceNormalizer()
        self.evaluator = OutcomeEvaluator()
        self.experience_collector = ExperienceCollector(self.learning_repo, self.normalizer, self.evaluator)
        self.feedback_collector = FeedbackCollector(self.learning_repo)
        self.knowledge_manager = KnowledgeManager(self.learning_repo)
        self.knowledge_retriever = KnowledgeRetriever(self.learning_repo)

        self.tool_dispatcher = tool_dispatcher or self._default_tool_dispatcher
        self._seed_reference_skills()

    def _default_tool_dispatcher(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Default mock dispatcher if live tools are not passed."""
        if tool_name == "generate_character":
            return {
                "character_id": params.get("character_id", "hero"),
                "frames": 2,
                "resolution": params.get("size", (16, 16)),
                "qa_passed": True,
            }
        elif tool_name == "apply_outline":
            return {"outline_applied": True, "mode": params.get("mode", "colored"), "qa_passed": True}
        elif tool_name == "validate_asset":
            return {"passed": True, "critical_errors": [], "warnings": []}
        elif tool_name == "export_godot_spritesheet":
            return {"exported": True, "engine": "godot_4", "frame_count": 2, "qa_passed": True}
        elif tool_name == "export_pixilart_project":
            return {"exported": True, "format": "pixil", "saved": True, "qa_passed": True}
        return {"status": "ok", "qa_passed": True}

    def _seed_reference_skills(self) -> None:
        """Seeds the standard 'Pixel Character Consistency' reference skill if not present."""
        existing = self.skill_repo.get_skill_version("pixel_character_consistency", "1.0.0")
        if not existing:
            workflow = [
                WorkflowStep(
                    step_id="step_1_generate",
                    tool_name="generate_character",
                    description="Generates base character anatomy and palette",
                    parameters={"size": [16, 16], "proportion": "chibi_1_2"},
                ),
                WorkflowStep(
                    step_id="step_2_outline",
                    tool_name="apply_outline",
                    description="Applies stylized outline and cleans isolated orphan pixels",
                    parameters={"mode": "colored", "source_step": "step_1_generate"},
                ),
                WorkflowStep(
                    step_id="step_3_validate",
                    tool_name="validate_asset",
                    description="Performs automated Art QA validation checks",
                    parameters={"source_step": "step_2_outline"},
                ),
                WorkflowStep(
                    step_id="step_4_export",
                    tool_name="export_godot_spritesheet",
                    description="Packs sprite sheet and generates Godot 4 SpriteFrames resource",
                    parameters={"source_step": "step_3_validate"},
                ),
            ]

            ref_skill = SkillDefinition(
                skill_id="pixel_character_consistency",
                version="1.0.0",
                name="Pixel Character Consistency",
                description="Production workflow generating consistent chibi character sprites with outlines and Godot 4 exports.",
                status=SkillStatus.APPROVED,
                trigger_conditions={"task_category": "character", "perspective": "top_down"},
                required_tools=["generate_character", "apply_outline", "validate_asset", "export_godot_spritesheet"],
                parameters_schema={
                    "character_id": {"type": "string", "description": "Character ID"},
                    "name": {"type": "string", "description": "Character Name"},
                    "size": {"type": "array", "default": [16, 16]},
                    "proportion": {"type": "string", "default": "chibi_1_2"},
                    "outline_mode": {"type": "string", "default": "colored"},
                },
                workflow=workflow,
                validation_rules={"require_qa_pass": True, "max_color_count": 16},
                art_profile_compatibility=["DefaultGame", "RetroFantasy"],
                author="ArtDirector_Lead",
            )
            self.skill_registry.register_skill(ref_skill, sync_fs=True, force=True)

        existing_pixil = self.skill_repo.get_skill_version("pixilart_clean_pixel_art", "1.0.0")
        if not existing_pixil:
            pixil_workflow = [
                WorkflowStep(
                    step_id="step_1_sketch_and_block",
                    tool_name="generate_character",
                    description="Blocks out character anatomy avoiding jaggies and double pixels",
                    parameters={"size": [16, 16], "proportion": "chibi_1_2"},
                ),
                WorkflowStep(
                    step_id="step_2_clean_lines_outline",
                    tool_name="apply_outline",
                    description="Applies selective 1px outline and eliminates orphan stray pixels",
                    parameters={"mode": "colored", "source_step": "step_1_sketch_and_block"},
                ),
                WorkflowStep(
                    step_id="step_3_art_qa_check",
                    tool_name="validate_asset",
                    description="Performs Art QA audit verifying palette, contrast, and zero orphan pixels",
                    parameters={"source_step": "step_2_clean_lines_outline"},
                ),
                WorkflowStep(
                    step_id="step_4_export_pixilart",
                    tool_name="export_pixilart_project",
                    description="Exports and safely saves project to Pixilart .pixil JSON format",
                    parameters={"source_step": "step_3_art_qa_check"},
                ),
                WorkflowStep(
                    step_id="step_5_export_spritesheet",
                    tool_name="export_godot_spritesheet",
                    description="Packs final sprite sheet and engine animation metadata",
                    parameters={"source_step": "step_4_export_pixilart"},
                ),
            ]

            pixil_skill = SkillDefinition(
                skill_id="pixilart_clean_pixel_art",
                version="1.0.0",
                name="Pixilart Clean Art & Export Pipeline",
                description="Pixilart drawing skill: generates clean silhouettes avoiding jaggies, applies cluster shading, enforces Art QA without orphan pixels, and safely saves .pixil project files and game sprite sheets.",
                status=SkillStatus.APPROVED,
                trigger_conditions={"task_category": "character", "style": "pixilart"},
                required_tools=["generate_character", "apply_outline", "validate_asset", "export_pixilart_project", "export_godot_spritesheet"],
                parameters_schema={
                    "character_id": {"type": "string", "description": "Character ID"},
                    "name": {"type": "string", "description": "Character Name"},
                    "size": {"type": "array", "default": [16, 16]},
                    "proportion": {"type": "string", "default": "chibi_1_2"},
                    "outline_mode": {"type": "string", "default": "colored"},
                },
                workflow=pixil_workflow,
                validation_rules={
                    "require_qa_pass": True,
                    "no_jaggies": True,
                    "no_orphan_pixels": True,
                    "safe_save": True,
                },
                art_profile_compatibility=["DefaultGame", "RetroFantasy", "PixilartCommunity"],
                author="Pixilart_ArtDirector",
            )
            self.skill_registry.register_skill(pixil_skill, sync_fs=True, force=True)

    def get_knowledge_guidance(
        self,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
        resolution: Optional[Tuple[int, int]] = None,
        min_confidence: float = 0.3,
    ) -> Dict[str, Any]:
        """Retrieves and consolidates applicable knowledge rules into guidance."""
        rules = self.knowledge_retriever.retrieve_applicable_rules(
            project_id=project_id,
            task_category=task_category,
            resolution=resolution,
            min_confidence=min_confidence,
        )
        return self.knowledge_retriever.format_guidance(rules)

    def find_applicable_skills(
        self,
        context: Dict[str, Any],
        art_profile_name: Optional[str] = None,
    ) -> List[SkillDefinition]:
        """Finds approved production skills matching the task context."""
        return self.skill_registry.find_matching_skills(
            context=context,
            art_profile_name=art_profile_name,
            allow_unapproved=False,
        )

    def execute_skill(
        self,
        skill_id: str,
        version: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        project_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Executes an APPROVED production skill, records the experience, and performs QA.
        """
        skill = self.skill_registry.get_skill(skill_id, version=version, allow_unapproved=False)
        if not skill:
            raise ValueError(
                f"Production skill '{skill_id}' (version: {version or 'latest'}) is not available or not APPROVED."
            )

        start_time = time.perf_counter()
        params = parameters or {}
        step_outputs: Dict[str, Any] = {}
        qa_report: Optional[Dict[str, Any]] = None
        tools_executed: List[str] = []

        # Execute workflow
        for step in skill.workflow:
            step_params = dict(step.parameters)
            step_params.update(params)
            step_res = self.tool_dispatcher(step.tool_name, step_params)
            step_outputs[step.step_id] = step_res
            tools_executed.append(step.tool_name)

            if step.tool_name == "validate_asset" or "passed" in step_res:
                qa_report = step_res

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Record Experience
        exp_record = self.experience_collector.record_task_run(
            task_id=f"skill_run_{skill_id}_{int(time.time())}",
            task_category=skill.trigger_conditions.get("task_category", "character"),
            asset_category="sprite",
            resolution=params.get("size", (16, 16)),
            input_context=params,
            output_summary=step_outputs,
            tools_used=tools_executed,
            execution_time_ms=elapsed_ms,
            qa_report=qa_report,
            art_profile={"name": skill.art_profile_compatibility[0] if skill.art_profile_compatibility else "default"},
            project_id=project_id,
        )

        return {
            "status": "success",
            "skill_id": skill.skill_id,
            "version": skill.version,
            "experience_id": exp_record.id,
            "outcome": exp_record.outcome.value,
            "execution_time_ms": round(elapsed_ms, 2),
            "step_outputs": step_outputs,
            "qa_report": qa_report,
        }

    def record_feedback(
        self,
        experience_id: str,
        feedback_type: str = "approval",
        user_rating: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> FeedbackRecord:
        """Records user feedback and updates knowledge confidence accordingly."""
        fb_enum = FeedbackType(feedback_type)
        feedback = self.feedback_collector.record_feedback(
            experience_id=experience_id,
            feedback_type=fb_enum,
            user_rating=user_rating,
            notes=notes,
        )

        # Retrieve related knowledge rules and update confidence
        exp = self.learning_repo.get_experience(experience_id)
        if exp:
            rules = self.knowledge_retriever.retrieve_applicable_rules(
                project_id=exp.project_id,
                task_category=exp.task_category,
            )
            for rule in rules:
                self.knowledge_manager.update_confidence(
                    knowledge_id=rule.id,
                    outcome=exp.outcome,
                    feedback=feedback,
                    experience_id=experience_id,
                )

        return feedback
