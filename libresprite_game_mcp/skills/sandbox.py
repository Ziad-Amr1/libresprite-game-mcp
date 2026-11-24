"""
Sandbox Evaluator.
Executes test cases, benchmarks performance, and evaluates candidate Skills in an isolated sandbox.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
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
    qa_must_pass: bool = True


class SandboxEvaluator:
    """Runs test cases against candidate Skills and scores their quality."""

    def __init__(
        self,
        repository: SkillRepository,
        tool_executor: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    ):
        self.repository = repository
        self.tool_executor = tool_executor or self._default_mock_executor

    def _default_mock_executor(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Default deterministic mock executor for sandbox testing."""
        if tool_name == "generate_character":
            return {
                "character_id": params.get("character_id", "test_char"),
                "frames": 2,
                "resolution": params.get("size", (16, 16)),
                "qa_passed": True,
            }
        elif tool_name == "apply_outline":
            return {"outline_applied": True, "mode": params.get("mode", "colored"), "qa_passed": True}
        elif tool_name == "export_godot_spritesheet":
            return {"exported": True, "target": "godot_4", "frame_count": 2, "qa_passed": True}
        return {"status": "ok", "qa_passed": True}

    def evaluate_skill(
        self,
        skill: SkillDefinition,
        test_cases: List[SkillTestCase],
    ) -> SkillEvaluationRecord:
        """Runs test suite against a skill and records evaluation telemetry."""
        if not test_cases:
            raise ValueError("Evaluation requires at least one test case.")

        passed_count = 0
        details: Dict[str, Any] = {"test_results": []}

        for tc in test_cases:
            start_time = time.perf_counter()
            step_outputs: Dict[str, Any] = {}
            test_passed = True
            error_msg: Optional[str] = None

            try:
                # Execute workflow steps
                for step in skill.workflow:
                    # Merge step parameters with test case input parameters
                    merged_params = dict(step.parameters)
                    merged_params.update(tc.input_parameters)
                    result = self.tool_executor(step.tool_name, merged_params)
                    step_outputs[step.step_id] = result

                # Validate expected outputs
                for expected_k, expected_v in tc.expected_outputs.items():
                    # Check across step outputs
                    found = False
                    for out in step_outputs.values():
                        if isinstance(out, dict) and out.get(expected_k) == expected_v:
                            found = True
                            break
                    if not found:
                        test_passed = False
                        error_msg = f"Expected output {expected_k}={expected_v} not found."
                        break

            except Exception as ex:
                test_passed = False
                error_msg = str(ex)

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if test_passed:
                passed_count += 1

            # Record individual execution telemetry
            exec_record = SkillExecutionResult(
                skill_id=skill.skill_id,
                skill_version=skill.version,
                execution_context={"test_case": tc.name, "inputs": tc.input_parameters},
                status="success" if test_passed else "failed",
                outputs=step_outputs,
                qa_passed=test_passed,
                execution_duration_ms=round(elapsed_ms, 2),
            )
            self.repository.save_execution_result(exec_record)

            details["test_results"].append({
                "test_case": tc.name,
                "passed": test_passed,
                "duration_ms": round(elapsed_ms, 2),
                "error": error_msg,
            })

        total = len(test_cases)
        score = round(passed_count / total, 3)
        summary = (
            f"Skill '{skill.skill_id}' v{skill.version} evaluated: "
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
