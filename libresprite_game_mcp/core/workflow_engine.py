"""
Workflow Execution Engine for LibreSprite Production Art System.
Provides deterministic DAG execution, input/output dependency binding,
lifecycle status tracking, and strict failure/QA halt policies.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from libresprite_game_mcp.core.dispatcher import (
    BaseToolDispatcher,
    ExecutionMode,
    ProductionToolDispatcher,
    ToolExecutionError,
)

if TYPE_CHECKING:
    from libresprite_game_mcp.skills.models import SkillDefinition, WorkflowStep


class WorkflowStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepResult(BaseModel):
    """Detailed execution telemetry for an individual workflow step."""
    model_config = ConfigDict(extra="forbid")

    step_id: str
    tool_name: str
    status: str = "success"  # "success", "failed", "skipped"
    duration_ms: float = 0.0
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowExecutionResult(BaseModel):
    """Structured result of a completed or halted workflow execution."""
    model_config = ConfigDict(extra="forbid")

    execution_id: str
    skill_id: str
    version: str
    project_id: str
    mode: ExecutionMode
    status: WorkflowStatus
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    generated_artifacts: List[str] = Field(default_factory=list)
    qa_report: Optional[Dict[str, Any]] = None
    execution_duration_ms: float = 0.0
    error_details: Optional[str] = None
    experience_id: Optional[str] = None


class WorkflowEngine:
    """Executes validated DAG workflows against registered tool dispatchers."""

    def __init__(
        self,
        dispatcher: Optional[BaseToolDispatcher] = None,
        mode: ExecutionMode = ExecutionMode.PRODUCTION,
    ):
        self.mode = mode
        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            if mode == ExecutionMode.MOCK:
                from libresprite_game_mcp.core.dispatcher import MockToolDispatcher
                self.dispatcher = MockToolDispatcher()
            else:
                self.dispatcher = ProductionToolDispatcher()

    def validate_dag(self, workflow: List[WorkflowStep]) -> Tuple[bool, List[str]]:
        """Validates acyclic ordering, unique step IDs, and dependency references."""
        errors: List[str] = []
        if not workflow:
            return False, ["Workflow contains no steps."]

        seen_steps: Set[str] = set()
        for idx, step in enumerate(workflow):
            if not step.step_id:
                errors.append(f"Step at index {idx} has missing step_id.")
            elif step.step_id in seen_steps:
                errors.append(f"Duplicate step_id '{step.step_id}' at index {idx}.")
            seen_steps.add(step.step_id)

            # Check source_step reference
            source_step = step.parameters.get("source_step")
            if source_step:
                if source_step not in seen_steps or source_step == step.step_id:
                    errors.append(
                        f"Step '{step.step_id}' references 'source_step': '{source_step}' which is not a preceding step."
                    )

        return len(errors) == 0, errors

    def execute(
        self,
        skill: SkillDefinition,
        parameters: Optional[Dict[str, Any]] = None,
        workspace: Optional[Path] = None,
        project_id: str = "default",
    ) -> WorkflowExecutionResult:
        """
        Executes workflow steps deterministically:
        - Resolves dependencies and output bindings.
        - Halts immediately on step failure or critical QA rejection.
        - Captures all generated artifacts.
        """
        is_valid, dag_errors = self.validate_dag(skill.workflow)
        if not is_valid:
            return WorkflowExecutionResult(
                execution_id=str(uuid.uuid4()),
                skill_id=skill.skill_id,
                version=skill.version,
                project_id=project_id,
                mode=self.mode,
                status=WorkflowStatus.FAILED,
                error_details=f"DAG Validation failed: {'; '.join(dag_errors)}",
            )

        exec_id = str(uuid.uuid4())
        initial_params = parameters or {}
        ws = workspace or (Path.cwd() / "game_assets")
        ws.mkdir(parents=True, exist_ok=True)

        overall_start = time.perf_counter()
        step_results: Dict[str, StepResult] = {}
        generated_artifacts: List[str] = []
        qa_report: Optional[Dict[str, Any]] = None
        halted = False
        final_status = WorkflowStatus.SUCCESS
        error_summary: Optional[str] = None

        require_qa_pass = skill.validation_rules.get("require_qa_pass", True)

        for idx, step in enumerate(skill.workflow):
            if halted:
                # Mark remaining steps as skipped
                step_results[step.step_id] = StepResult(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status="skipped",
                    duration_ms=0.0,
                )
                continue

            # Resolve step parameters from step definition, initial inputs, and predecessor outputs
            step_inputs = self._resolve_step_inputs(
                step=step,
                initial_params=initial_params,
                step_results=step_results,
            )

            step_start = time.perf_counter()
            try:
                outputs = self.dispatcher.dispatch(step.tool_name, step_inputs, ws)
                duration_ms = (time.perf_counter() - step_start) * 1000.0

                # Track generated artifacts
                for k in ("project_path", "preview_path", "sheet_png", "tres_file", "saved_path"):
                    if k in outputs and outputs[k]:
                        artifact_p = str(outputs[k])
                        if artifact_p not in generated_artifacts:
                            generated_artifacts.append(artifact_p)

                # Check QA report
                if step.tool_name == "validate_asset" or "critical_errors" in outputs or "passed" in outputs:
                    qa_report = outputs
                    if require_qa_pass and not outputs.get("passed", True):
                        halted = True
                        final_status = WorkflowStatus.FAILED
                        criticals = outputs.get("critical_errors", [])
                        error_summary = f"QA Validation failed with {len(criticals)} critical error(s): {criticals}. Dependent steps halted."

                step_results[step.step_id] = StepResult(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status="success" if not (step.tool_name == "validate_asset" and not outputs.get("passed", True)) else "failed",
                    duration_ms=round(duration_ms, 2),
                    inputs=step_inputs,
                    outputs=outputs,
                )

            except Exception as ex:
                duration_ms = (time.perf_counter() - step_start) * 1000.0
                halted = True
                final_status = WorkflowStatus.FAILED
                error_summary = f"Step '{step.step_id}' ({step.tool_name}) failed: {ex}"
                step_results[step.step_id] = StepResult(
                    step_id=step.step_id,
                    tool_name=step.tool_name,
                    status="failed",
                    duration_ms=round(duration_ms, 2),
                    inputs=step_inputs,
                    outputs={},
                    error=str(ex),
                )

        overall_duration = (time.perf_counter() - overall_start) * 1000.0

        return WorkflowExecutionResult(
            execution_id=exec_id,
            skill_id=skill.skill_id,
            version=skill.version,
            project_id=project_id,
            mode=self.mode,
            status=final_status,
            step_results=step_results,
            generated_artifacts=generated_artifacts,
            qa_report=qa_report,
            execution_duration_ms=round(overall_duration, 2),
            error_details=error_summary,
        )

    def _resolve_step_inputs(
        self,
        step: WorkflowStep,
        initial_params: Dict[str, Any],
        step_results: Dict[str, StepResult],
    ) -> Dict[str, Any]:
        """Binds initial parameters and previous step outputs into step inputs."""
        resolved: Dict[str, Any] = dict(step.parameters)

        # 1. Forward relevant initial user parameters
        for k, v in initial_params.items():
            if k not in resolved:
                resolved[k] = v

        # 2. Resolve source_step artifact binding
        source_step_id = step.parameters.get("source_step")
        if source_step_id and source_step_id in step_results:
            prev_out = step_results[source_step_id].outputs
            # Bind project artifact path forward
            for path_key in ("project_path", "saved_path", "sheet_png"):
                if path_key in prev_out and path_key not in resolved:
                    resolved["project_path"] = prev_out[path_key]
                    resolved["input_file"] = prev_out[path_key]
                    break
        if "project_path" not in resolved and "input_file" not in resolved and step_results:
            # Fallback to most recent preceding step output that produced an artifact
            for prev_res in reversed(list(step_results.values())):
                for path_key in ("project_path", "saved_path", "sheet_png"):
                    if path_key in prev_res.outputs and prev_res.outputs[path_key]:
                        resolved["project_path"] = prev_res.outputs[path_key]
                        resolved["input_file"] = prev_res.outputs[path_key]
                        break
                if "project_path" in resolved:
                    break

        return resolved
