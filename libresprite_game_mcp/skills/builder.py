"""
Skill Builder MVP.
Creates, validates, and composes Skill definitions with strict tool allowlist enforcement.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple
from libresprite_game_mcp.learning.models import ExperienceRecord, OutcomeType
from libresprite_game_mcp.skills.models import SkillDefinition, SkillStatus, WorkflowStep

# Approved production MCP tool contracts
APPROVED_MCP_TOOLS: Set[str] = {
    "generate_character",
    "generate_tileset",
    "generate_item",
    "validate_asset",
    "export_godot_spritesheet",
    "export_pixilart_project",
    "apply_outline",
    "apply_palette",
    "generate_walk_cycle",
    "put_pixel",
    "get_preview",
}

FORBIDDEN_KEYWORDS: Set[str] = {
    "eval",
    "exec",
    "python",
    "shell",
    "bash",
    "cmd",
    "powershell",
    "subprocess",
    "os.system",
}


class InvalidWorkflowError(Exception):
    """Raised when a Skill workflow contains invalid, unbound, or forbidden tools."""
    pass


class SkillBuilder:
    """Composes and validates structured Skill definitions."""

    def __init__(self, allowed_tools: Optional[Set[str]] = None):
        self.allowed_tools = allowed_tools or APPROVED_MCP_TOOLS

    def validate_workflow(self, workflow: List[WorkflowStep]) -> Tuple[bool, List[str]]:
        """
        Validates workflow steps for security, tool bindings, and acyclic ordering.
        """
        errors: List[str] = []
        seen_steps: Set[str] = set()

        if not workflow:
            errors.append("Workflow cannot be empty.")
            return False, errors

        for idx, step in enumerate(workflow):
            # Check unique step_id
            if not step.step_id or step.step_id.strip() == "":
                errors.append(f"Step at index {idx} has an empty step_id.")
            elif step.step_id in seen_steps:
                errors.append(f"Duplicate step_id '{step.step_id}' at index {idx}.")
            seen_steps.add(step.step_id)

            # Check tool allowlist
            if step.tool_name not in self.allowed_tools:
                errors.append(
                    f"Tool '{step.tool_name}' in step '{step.step_id}' is not in the approved tool allowlist."
                )

            # Check forbidden security keywords in parameters
            for key, val in step.parameters.items():
                str_repr = f"{key} {val}".lower()
                for bad_word in FORBIDDEN_KEYWORDS:
                    if bad_word in str_repr:
                        errors.append(
                            f"Security violation in step '{step.step_id}': parameter contains forbidden keyword '{bad_word}'."
                        )

            # Check dependency references
            if "source_step" in step.parameters:
                src = step.parameters["source_step"]
                if src not in seen_steps or src == step.step_id:
                    errors.append(
                        f"Step '{step.step_id}' references previous step '{src}' which has not executed yet."
                    )

        return len(errors) == 0, errors

    def create_draft(
        self,
        skill_id: str,
        name: str,
        description: str,
        workflow: List[WorkflowStep],
        version: str = "0.1.0",
        trigger_conditions: Optional[Dict[str, Any]] = None,
        validation_rules: Optional[Dict[str, Any]] = None,
        art_profile_compatibility: Optional[List[str]] = None,
        parameters_schema: Optional[Dict[str, Any]] = None,
        author: str = "skill_builder",
    ) -> SkillDefinition:
        """
        Creates a validated SkillDefinition in DRAFT status.
        """
        is_valid, errors = self.validate_workflow(workflow)
        if not is_valid:
            raise InvalidWorkflowError(f"Invalid workflow for skill '{skill_id}': {'; '.join(errors)}")

        required_tools = sorted(list({step.tool_name for step in workflow}))

        return SkillDefinition(
            skill_id=skill_id,
            version=version,
            name=name,
            description=description,
            status=SkillStatus.DRAFT,
            trigger_conditions=trigger_conditions or {},
            required_tools=required_tools,
            parameters_schema=parameters_schema or {},
            workflow=workflow,
            validation_rules=validation_rules or {},
            art_profile_compatibility=art_profile_compatibility or [],
            author=author,
        )

    def synthesize_draft_from_experiences(
        self,
        experiences: List[ExperienceRecord],
        skill_id: str,
        name: str,
        description: str,
        min_experiences: int = 3,
    ) -> SkillDefinition:
        """
        Synthesizes a candidate workflow draft from multi-experience consensus.
        Requires minimum experience volume and consistent tool sequences.
        """
        if len(experiences) < min_experiences:
            raise ValueError(
                f"Insufficient evidence: found {len(experiences)} experiences, minimum required is {min_experiences}."
            )

        successful_exps = [e for e in experiences if e.outcome == OutcomeType.SUCCESS]
        if len(successful_exps) < min_experiences:
            raise ValueError(
                f"Insufficient successful evidence: found {len(successful_exps)} successful experiences, minimum required is {min_experiences}."
            )

        # Failure rate check (> 25% failure indicates unstable workflow)
        failure_rate = (len(experiences) - len(successful_exps)) / len(experiences)
        if failure_rate > 0.25:
            raise ValueError(
                f"Workflow instability detected: failure rate {failure_rate:.1%} is too high to synthesize a reliable candidate skill."
            )

        # Check tool sequence consensus across all successful experiences
        consensus_tools = tuple(successful_exps[0].tools_used)
        for exp in successful_exps[1:]:
            if tuple(exp.tools_used) != consensus_tools:
                raise ValueError(
                    f"Conflicting evidence: inconsistent tool sequences detected ({consensus_tools} vs {tuple(exp.tools_used)}). Manual human design required."
                )

        workflow_steps: List[WorkflowStep] = []
        prev_step_id: Optional[str] = None
        for idx, tool in enumerate(consensus_tools):
            step_id = f"step_{idx + 1}_{tool}"
            params: Dict[str, Any] = {}
            if prev_step_id is not None:
                params["source_step"] = prev_step_id

            workflow_steps.append(
                WorkflowStep(
                    step_id=step_id,
                    tool_name=tool,
                    description=f"Synthesized step {idx + 1} invoking {tool}",
                    parameters=params,
                )
            )
            prev_step_id = step_id

        # Inferred triggers
        first_exp = successful_exps[0]
        trigger_conditions = {
            "task_category": first_exp.task_category,
            "resolution": f"{first_exp.resolution[0]}x{first_exp.resolution[1]}",
        }

        source_ids = [e.id for e in successful_exps]

        return self.create_draft(
            skill_id=skill_id,
            name=name,
            description=description,
            workflow=workflow_steps,
            version="0.1.0",
            trigger_conditions=trigger_conditions,
            validation_rules={
                "require_qa_pass": True,
                "synthesized_from_experiences": source_ids,
            },
            author="evidence_synthesizer",
        )
