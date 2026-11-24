"""
Sandbox Evaluator.
Executes test cases, benchmarks performance, and evaluates candidate Skills in an isolated sandbox.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

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
from libresprite_game_mcp.skills.models import (
    SkillDefinition,
    SkillEvaluationRecord,
    SkillExecutionResult,
)
from libresprite_game_mcp.skills.repository import SkillRepository


class SkillTestCase(BaseModel):
    """Test case specification for sandbox evaluation."""
    model_config = ConfigDict(extra="forbid")

    name: str
    input_parameters: Dict[str, Any] = Field(default_factory=dict)
    expected_outputs: Dict[str, Any] = Field(default_factory=dict)
    expected_step_outputs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    qa_must_pass: bool = True


class SandboxEvaluator:
    """Runs test cases against candidate Skills in isolated workspaces and scores their quality."""

    def __init__(
        self,
        repository: SkillRepository,
        mode: ExecutionMode = ExecutionMode.SANDBOX,
        dispatcher: Optional[BaseToolDispatcher] = None,
        workflow_engine: Optional[WorkflowEngine] = None,
        sandbox_base_dir: Optional[Path] = None,
    ):
        self.repository = repository
        self.mode = mode
        self.sandbox_base_dir = sandbox_base_dir or (Path("data/sandbox_workspaces"))
        self.sandbox_base_dir.mkdir(parents=True, exist_ok=True)

        if workflow_engine is not None:
            self.engine = workflow_engine
        else:
            if dispatcher is not None:
                self.engine = WorkflowEngine(dispatcher=dispatcher, mode=mode)
            else:
                if mode == ExecutionMode.MOCK:
                    self.engine = WorkflowEngine(dispatcher=MockToolDispatcher(), mode=mode)
                else:
                    self.engine = WorkflowEngine(dispatcher=ProductionToolDispatcher(), mode=mode)

    def evaluate_skill(
        self,
        skill: SkillDefinition,
        test_cases: List[SkillTestCase],
        isolated_dir: Optional[Path] = None,
    ) -> SkillEvaluationRecord:
        """
        Runs test suite against a candidate Skill in an isolated workspace.
        Enforces step-specific output checks and QA validation rules.
        """
        if not test_cases:
            raise ValueError("Evaluation requires at least one test case.")

        run_id = f"eval_{int(time.time())}"
        eval_ws = isolated_dir or (self.sandbox_base_dir / skill.skill_id / skill.version / run_id)
        eval_ws.mkdir(parents=True, exist_ok=True)

        passed_count = 0
        details: Dict[str, Any] = {
            "execution_mode": self.mode.value,
            "test_results": [],
            "failed_assertions": [],
        }

        for tc in test_cases:
            tc_ws = eval_ws / tc.name.replace(" ", "_")
            tc_ws.mkdir(parents=True, exist_ok=True)

            wf_result: WorkflowExecutionResult = self.engine.execute(
                skill=skill,
                parameters=tc.input_parameters,
                workspace=tc_ws,
                project_id="sandbox_eval",
            )

            test_passed = (wf_result.status == WorkflowStatus.SUCCESS)
            assertion_failures: List[str] = []

            if not test_passed and wf_result.error_details:
                assertion_failures.append(wf_result.error_details)

            # Check QA requirement
            if tc.qa_must_pass and skill.validation_rules.get("require_qa_pass", False):
                if not wf_result.qa_report or not wf_result.qa_report.get("passed", False):
                    test_passed = False
                    assertion_failures.append(f"Test case '{tc.name}' required QA pass, but QA passed is False or missing.")
            elif wf_result.qa_report and not wf_result.qa_report.get("passed", True):
                test_passed = False
                assertion_failures.append(f"Test case '{tc.name}' QA validation failed.")

            # Validate expected outputs (global fallback)
            for expected_k, expected_v in tc.expected_outputs.items():
                found = False
                for step_res in wf_result.step_results.values():
                    if step_res.outputs.get(expected_k) == expected_v:
                        found = True
                        break
                if not found:
                    test_passed = False
                    assertion_failures.append(
                        f"Expected output key '{expected_k}'='{expected_v}' was not found in any step output."
                    )

            # Validate expected_step_outputs (step-specific binding)
            for step_id, expected_dict in tc.expected_step_outputs.items():
                if step_id not in wf_result.step_results:
                    test_passed = False
                    assertion_failures.append(f"Expected step '{step_id}' was not executed.")
                else:
                    actual_out = wf_result.step_results[step_id].outputs
                    for k, v in expected_dict.items():
                        if actual_out.get(k) != v:
                            test_passed = False
                            assertion_failures.append(
                                f"Step '{step_id}' output mismatch: expected '{k}'='{v}', got '{actual_out.get(k)}'"
                            )

            if test_passed:
                passed_count += 1
            else:
                details["failed_assertions"].extend(assertion_failures)

            # Save execution telemetry
            exec_record = SkillExecutionResult(
                skill_id=skill.skill_id,
                skill_version=skill.version,
                project_id="sandbox_eval",
                execution_context={"test_case": tc.name, "inputs": tc.input_parameters, "mode": self.mode.value},
                status="success" if test_passed else "failed",
                outputs={sid: sr.outputs for sid, sr in wf_result.step_results.items()},
                qa_passed=bool(wf_result.qa_report and wf_result.qa_report.get("passed", False)),
                execution_duration_ms=wf_result.execution_duration_ms,
            )
            self.repository.save_execution_result(exec_record)

            details["test_results"].append({
                "test_case": tc.name,
                "passed": test_passed,
                "duration_ms": wf_result.execution_duration_ms,
                "failures": assertion_failures,
            })

        total = len(test_cases)
        score = round(passed_count / total, 3)
        summary = (
            f"Skill '{skill.skill_id}' v{skill.version} evaluated in [{self.mode.value}] mode: "
            f"{passed_count}/{total} test cases passed (score: {score:.1%})"
        )

        eval_record = SkillEvaluationRecord(
            skill_id=skill.skill_id,
            skill_version=skill.version,
            test_cases_run=total,
            test_cases_passed=passed_count,
            score=score,
            evaluation_summary=summary,
            details=details,
        )

        return self.repository.save_evaluation(eval_record)
