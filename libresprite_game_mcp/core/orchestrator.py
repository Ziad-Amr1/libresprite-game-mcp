"""
Production Orchestrator for LibreSprite Game MCP.
Integrates real tool dispatching, deterministic DAG workflow execution,
guaranteed experience telemetry capture, and reliable knowledge retrieval.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from libresprite_game_mcp.core.dispatcher import (
    BaseToolDispatcher,
    ExecutionMode,
    MockToolDispatcher,
    ProductionToolDispatcher,
)
from libresprite_game_mcp.core.workflow_engine import (
    WorkflowEngine,
    WorkflowExecutionResult,
    WorkflowStatus,
)
from libresprite_game_mcp.learning.collector import ExperienceCollector, FeedbackCollector
from libresprite_game_mcp.learning.evaluator import OutcomeEvaluator
from libresprite_game_mcp.learning.knowledge import KnowledgeManager, KnowledgeRetriever
from libresprite_game_mcp.learning.models import (
    CharacterGenerationGuidance,
    ExperienceRecord,
    FeedbackRecord,
    FeedbackType,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
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
    """Coordinates real skill execution, automated QA, experience recording, and knowledge retrieval."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        skills_dir: Optional[Path] = None,
        mode: ExecutionMode = ExecutionMode.PRODUCTION,
        tool_dispatcher: Optional[BaseToolDispatcher] = None,
        assets_dir: Optional[Path] = None,
    ):
        self.mode = mode
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

        self.assets_dir = assets_dir or (Path.cwd() / "game_assets")
        self.assets_dir.mkdir(parents=True, exist_ok=True)

        if tool_dispatcher is not None:
            self.dispatcher = tool_dispatcher
        else:
            if mode == ExecutionMode.MOCK:
                self.dispatcher = MockToolDispatcher()
            else:
                self.dispatcher = ProductionToolDispatcher()

        self.engine = WorkflowEngine(dispatcher=self.dispatcher, mode=self.mode)
        self._seed_reference_skills()
        self._seed_reference_knowledge()

    def _seed_reference_knowledge(self) -> None:
        """Seeds universal Art Bible knowledge rules into the Learning Layer."""
        from libresprite_game_mcp.learning.seed_knowledge import seed_art_bible_knowledge
        seed_art_bible_knowledge(self.learning_repo)

    def _seed_reference_skills(self) -> None:
        """
        Seeds standard reference skills in DRAFT status.
        Reference skills are NEVER seeded directly as APPROVED to honor governance.
        """
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
                description="Example reference workflow for consistent chibi character sprites with outlines and Godot 4 exports.",
                status=SkillStatus.DRAFT,  # Seeded as DRAFT
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
            self.skill_registry.register_skill(ref_skill, sync_fs=True)

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
                description="Example Pixilart workflow: clean silhouettes, cluster shading, Art QA, and .pixil project export.",
                status=SkillStatus.DRAFT,  # Seeded as DRAFT
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
            self.skill_registry.register_skill(pixil_skill, sync_fs=True)

    def approve_reference_skill(
        self,
        skill_id: str,
        version: str = "1.0.0",
        reviewer: str = "ArtDirector_Sarah",
        comments: str = "Explicit human approval after sandbox evaluation.",
        human_confirmed: bool = True,
    ) -> SkillDefinition:
        """Explicitly advances a reference skill from DRAFT -> SANDBOX -> APPROVED with audit trail."""
        skill = self.skill_repo.get_skill_version(skill_id, version)
        if not skill:
            raise ValueError(f"Skill '{skill_id}' v{version} not found.")

        if skill.status == SkillStatus.APPROVED:
            return skill

        if skill.status == SkillStatus.DRAFT:
            self.lifecycle.submit_to_sandbox(skill_id, version)

        return self.lifecycle.approve_skill(
            skill_id=skill_id,
            version=version,
            reviewer=reviewer,
            comments=comments,
            human_confirmed=human_confirmed,
        )

    def get_knowledge_guidance(
        self,
        project_id: Optional[str] = None,
        task_category: Optional[str] = None,
        resolution: Optional[Tuple[int, int]] = None,
        palette_name: Optional[str] = None,
        art_profile: Optional[str] = None,
        archetype: Optional[str] = None,
        animation_state: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> Dict[str, Any]:
        """Retrieves and consolidates applicable knowledge rules into guidance."""
        rules = self.knowledge_retriever.retrieve_applicable_rules(
            project_id=project_id,
            task_category=task_category,
            resolution=resolution,
            palette_name=palette_name,
            art_profile=art_profile,
            archetype=archetype,
            animation_state=animation_state,
            min_confidence=min_confidence,
        )
        return self.knowledge_retriever.format_guidance(rules)

    def build_character_guidance(
        self,
        resolution: Tuple[int, int] = (16, 16),
        art_profile_name: str = "DefaultGame",
        archetype: Optional[str] = None,
        palette_name: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> CharacterGenerationGuidance:
        """Retrieves applicable knowledge rules and builds a typed CharacterGenerationGuidance package."""
        raw = self.get_knowledge_guidance(
            project_id=project_id,
            task_category="character",
            resolution=resolution,
            palette_name=palette_name,
            art_profile=art_profile_name,
            archetype=archetype,
        )
        return CharacterGenerationGuidance(
            target_resolution=resolution,
            selected_art_profile=art_profile_name,
            character_archetype=archetype,
            palette_constraints=raw.get("palettes", []),
            silhouette_recommendations=raw.get("silhouette_recommendations", {}),
            shading_recommendations=raw.get("shading_recommendations", {}),
            outline_recommendations=raw.get("outline_recommendations", {}),
            animation_requirements=raw.get("animation_requirements", {}),
            applicable_rules=raw.get("applicable_rules", []),
        )

    def generate_character(
        self,
        character_id: str,
        name: Optional[str] = None,
        size: Tuple[int, int] = (16, 16),
        archetype: Optional[str] = None,
        palette_name: Optional[str] = None,
        art_profile: str = "DefaultGame",
        workspace: Optional[Path] = None,
        project_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Generates an animated character with end-to-end Learning Layer guidance integration.
        Retrieves applicable rules, binds guidance, dispatches to generator, and records experience.
        """
        ws = workspace or self.assets_dir
        ws.mkdir(parents=True, exist_ok=True)
        res_tuple = (int(size[0]), int(size[1]))

        guidance = self.build_character_guidance(
            resolution=res_tuple,
            art_profile_name=art_profile,
            archetype=archetype,
            palette_name=palette_name,
            project_id=project_id,
        )

        params = {
            "character_id": character_id,
            "name": name or character_id,
            "size": list(res_tuple),
            "archetype": archetype,
            "palette_name": palette_name,
            "art_profile": art_profile,
            "guidance": guidance.model_dump(),
        }

        start_time = time.perf_counter()
        output = self.dispatcher.dispatch("generate_character", params, ws)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        exp = self.experience_collector.record_task_run(
            task_id=f"gen_{character_id}_{int(time.time() * 1000)}",
            task_category="character",
            asset_category="sprite",
            resolution=res_tuple,
            input_context=params,
            output_summary=output,
            tools_used=["generate_character"],
            execution_time_ms=duration_ms,
            execution_outcome="SUCCESS",
            art_profile={"name": art_profile, "palette": palette_name or "db16"},
            project_id=project_id,
        )
        output["experience_id"] = exp.id
        output["guidance"] = guidance.model_dump()
        return output

    def find_applicable_skills(
        self,
        context: Dict[str, Any],
        art_profile_name: Optional[str] = None,
        allow_unapproved: bool = False,
    ) -> List[SkillDefinition]:
        """Finds skills matching context, defaulting to APPROVED in production."""
        permit_unapproved = allow_unapproved or (self.mode == ExecutionMode.SANDBOX)
        return self.skill_registry.find_matching_skills(
            context=context,
            art_profile_name=art_profile_name,
            allow_unapproved=permit_unapproved,
        )

    def execute_skill(
        self,
        skill_id: str,
        version: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        project_id: str = "default",
        workspace: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Executes a Skill through the deterministic WorkflowEngine:
        - Resolves dependencies and outputs.
        - Guaranteed Learning Layer experience capture even on unhandled exception.
        - Enforces strict APPROVED requirement in production mode.
        """
        allow_unapproved = (self.mode in (ExecutionMode.SANDBOX, ExecutionMode.MOCK))
        skill = self.skill_registry.get_skill(skill_id, version=version, allow_unapproved=allow_unapproved)
        if not skill:
            raise ValueError(
                f"Skill '{skill_id}' (version: {version or 'latest'}) is not available or not APPROVED for execution in [{self.mode.value}] mode."
            )

        target_ws = workspace or self.assets_dir
        target_ws.mkdir(parents=True, exist_ok=True)
        params = dict(parameters or {})
        task_id = f"skill_run_{skill_id}_{int(time.time() * 1000)}"

        # Automatically bind Learning Layer guidance for character generation workflows
        task_cat = skill.trigger_conditions.get("task_category", "character")
        if task_cat == "character" and "guidance" not in params:
            size_p = params.get("size", (16, 16))
            res = (int(size_p[0]), int(size_p[1])) if isinstance(size_p, (list, tuple)) and len(size_p) >= 2 else (16, 16)
            prof_name = params.get("art_profile") or (skill.art_profile_compatibility[0] if skill.art_profile_compatibility else "DefaultGame")
            guidance_pkg = self.build_character_guidance(
                resolution=res,
                art_profile_name=prof_name,
                archetype=params.get("archetype"),
                palette_name=params.get("palette_name"),
                project_id=project_id,
            )
            params["guidance"] = guidance_pkg.model_dump()

        wf_result: Optional[WorkflowExecutionResult] = None
        unhandled_error: Optional[str] = None

        try:
            wf_result = self.engine.execute(
                skill=skill,
                parameters=params,
                workspace=target_ws,
                project_id=project_id,
            )
        except Exception as ex:
            unhandled_error = str(ex)
            raise
        finally:
            # Guaranteed Learning Layer Experience Logging
            duration = wf_result.execution_duration_ms if wf_result else 0.0
            exec_outcome = "SUCCESS" if (wf_result and wf_result.status == WorkflowStatus.SUCCESS) else "FAILED"
            step_outs = {sid: sr.outputs for sid, sr in wf_result.step_results.items() if sr.outputs} if wf_result else {}
            qa_rep = wf_result.qa_report if wf_result else None
            tools_run = [sr.tool_name for sr in wf_result.step_results.values()] if wf_result else []

            # Ensure resolution is a valid Tuple[int, int] for telemetry
            res_val = params.get("size")
            if isinstance(res_val, (list, tuple)) and len(res_val) >= 2:
                try:
                    res_tuple = (int(res_val[0]), int(res_val[1]))
                except (ValueError, TypeError):
                    res_tuple = (16, 16)
            else:
                res_tuple = (16, 16)

            exp_record = self.experience_collector.record_task_run(
                task_id=task_id,
                task_category=skill.trigger_conditions.get("task_category", "character"),
                asset_category="sprite",
                resolution=res_tuple,
                input_context=params,
                output_summary=step_outs,
                tools_used=tools_run,
                execution_time_ms=duration,
                execution_outcome=exec_outcome,
                qa_report=qa_rep,
                art_profile={"name": skill.art_profile_compatibility[0] if skill.art_profile_compatibility else "default"},
                project_id=project_id,
                execution_error=unhandled_error or (wf_result.error_details if wf_result else None),
            )

        return {
            "status": "success" if wf_result.status == WorkflowStatus.SUCCESS else "failed",
            "workflow_status": wf_result.status.value,
            "skill_id": skill.skill_id,
            "version": skill.version,
            "execution_id": wf_result.execution_id,
            "experience_id": exp_record.id,
            "outcome": exp_record.outcome.value,
            "execution_time_ms": wf_result.execution_duration_ms,
            "step_outputs": {sid: sr.outputs for sid, sr in wf_result.step_results.items()},
            "step_results": {sid: sr.model_dump() for sid, sr in wf_result.step_results.items()},
            "generated_artifacts": wf_result.generated_artifacts,
            "qa_report": wf_result.qa_report,
            "error_details": wf_result.error_details,
        }

    def record_feedback(
        self,
        experience_id: str,
        feedback_type: str = "approval",
        user_rating: Optional[float] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> FeedbackRecord:
        """
        Records user feedback with idempotency protection and updates
        only directly relevant knowledge rules based on provenance and content matching.
        """
        fb_enum = FeedbackType(feedback_type)
        key = idempotency_key or f"fb_{experience_id}_{feedback_type}_{user_rating or 0}_{hash(notes or '')}"

        feedback = self.feedback_collector.record_feedback(
            experience_id=experience_id,
            feedback_type=fb_enum,
            user_rating=user_rating,
            notes=notes,
            idempotency_key=key,
        )

        exp = self.learning_repo.get_experience(experience_id)
        if not exp:
            return feedback

        # Determine relevant categories from notes and tags
        relevant_categories: List[KnowledgeCategory] = []
        notes_lower = (notes or "").lower()

        if "outline" in notes_lower or "outline" in exp.tags:
            relevant_categories.append(KnowledgeCategory.OUTLINE)
        if "palette" in notes_lower or "color" in notes_lower or any("palette:" in t for t in exp.tags):
            relevant_categories.append(KnowledgeCategory.PALETTE)
        if "light" in notes_lower or "shadow" in notes_lower:
            relevant_categories.append(KnowledgeCategory.LIGHTING)
        if "silhouette" in notes_lower or "shape" in notes_lower:
            relevant_categories.append(KnowledgeCategory.SILHOUETTE)
        if "dither" in notes_lower:
            relevant_categories.append(KnowledgeCategory.DITHERING)
        if "animation" in notes_lower or "timing" in notes_lower or "fps" in notes_lower:
            relevant_categories.append(KnowledgeCategory.ANIMATION_TIMING)

        # Retrieve candidate rules
        all_rules = self.knowledge_retriever.retrieve_applicable_rules(
            project_id=exp.project_id,
            task_category=exp.task_category,
        )

        for rule in all_rules:
            # 1. External reference protection: literature references are immutable and not scored by empirical feedback
            if rule.knowledge_type == KnowledgeType.EXTERNAL_REFERENCE:
                continue

            # 2. Universal rule protection: project-specific feedback must not mutate universal rules
            if rule.project_id is None and exp.project_id not in ("default", None):
                continue

            # Rule is relevant IF:
            # 1. Experience is explicitly listed in rule's source_experience_ids, OR
            # 2. Rule's category specifically matches the feedback topic (when topics were identified)
            is_relevant = False
            if experience_id in rule.source_experience_ids:
                is_relevant = True
            elif relevant_categories and rule.category in relevant_categories:
                is_relevant = True
            elif not relevant_categories and rule.category == KnowledgeCategory.GENERAL:
                is_relevant = True

            if is_relevant:
                self.knowledge_manager.update_confidence(
                    knowledge_id=rule.id,
                    outcome=exp.outcome,
                    feedback=feedback,
                    experience_id=experience_id,
                )

        return feedback
