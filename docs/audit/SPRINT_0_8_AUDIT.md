# Sprint 0.8 — Corrective Engineering Audit & Defect Reproduction

**Date:** 2026-11-24  
**Branch:** `feature/production-art-system`  
**Starting Commit:** `c123aa6f4eb26dab13d9bd2db755484d8af4aff1`  
**Status:** Defect Reproduction Verified — Stage 1 Complete  

---

## 1. Executive Summary

An independent architectural audit of the Learning Layer, Skill Builder, and Production Orchestrator (implemented during Sprints 0.3–0.7) revealed several critical gaps between the declared production architecture and actual execution behavior:

1. **Simulated Execution (Mock by Default):** `ProductionOrchestrator` defaulted to a simulated mock dispatcher, meaning production skill execution did not invoke real asset generators, did not create files, and did not run actual Art QA validation.
2. **Missing Dependency & Output Resolution:** Skill workflows declared `source_step` dependencies, but the workflow runner did not pass outputs from predecessor steps to successor steps. All input parameters were blindly merged into every step.
3. **Failure Propagation Failure:** If a tool or QA check failed in a multi-step workflow, the loop did not halt; it continued straight to dependent export steps.
4. **Approval Governance Bypass:** Reference skills (`pixel_character_consistency` and `pixilart_clean_pixel_art`) were seeded directly into the database as `APPROVED` with `force=True`, bypassing the mandatory `DRAFT → SANDBOX → HUMAN APPROVAL` lifecycle.
5. **Loss of Telemetry on Crash:** If a tool threw an unhandled exception, `execute_skill` failed before reaching `record_task_run`, completely omitting the failed experience from the Learning Layer.
6. **Broad Feedback Updates & Lack of Idempotency:** Submitting feedback updated all knowledge rules in the task category (regardless of relevance), and repeat submissions inflated confidence multiple times.
7. **Single-Sample Skill Synthesis:** `synthesize_draft_from_experiences()` inspected only the first successful experience, failing to evaluate multiple experiences or detect conflicting evidence.

All defects were isolated and verified via `tests/reproduce_sprint_0_8_defects.py`.

---

## 2. Detailed Defect Analysis & Reproduction Evidence

### Defect 1: Mock Tool Dispatcher Used by Default in Production
- **Location:** `libresprite_game_mcp/core/orchestrator.py` (`ProductionOrchestrator._default_tool_dispatcher`, lines 62–77).
- **Reproduction:** `tests/reproduce_sprint_0_8_defects.py::test_defect_1_production_orchestrator_uses_mock_dispatcher_by_default`.
- **Finding:** In `server.py`, `orchestrator = ProductionOrchestrator()` was instantiated without passing a real tool dispatcher. When `execute_production_skill` was called, it executed `_default_tool_dispatcher`, returning simulated dictionaries (`{"status": "ok", "qa_passed": True}`). No Aseprite file was generated, no pixel data was rendered, and no texture atlas was created.

### Defect 2: Unresolved `source_step` Dependencies
- **Location:** `libresprite_game_mcp/core/orchestrator.py` (`execute_skill`, lines 182–205).
- **Reproduction:** `tests/reproduce_sprint_0_8_defects.py::test_defect_2_dependency_resolution_unresolved`.
- **Finding:** Steps declared dependencies (e.g., `step_2_outline` had `"source_step": "step_1_generate"`), but the execution loop executed:
  ```python
  step_params = dict(step.parameters)
  step_params.update(params)
  ```
  The outputs of predecessor steps were never bound to successor inputs. Successor steps had no reference to the artifacts or objects created earlier in the workflow.

### Defect 3: Reference Skills Seeded as `APPROVED` with `force=True`
- **Location:** `libresprite_game_mcp/core/orchestrator.py` (`_seed_reference_skills`, lines 110–130).
- **Reproduction:** `tests/reproduce_sprint_0_8_defects.py::test_defect_3_reference_skill_seeded_approved`.
- **Finding:** The specification states that all Skills must strictly originate in `DRAFT`, undergo `SANDBOX` evaluation, and require explicit human review before becoming `APPROVED`. Seeding reference skills directly as `APPROVED` with `force=True` silently bypassed the human governance model and immutability controls.

### Defect 4: Unhandled Tool Failures Escape Without Experience Records
- **Location:** `libresprite_game_mcp/core/orchestrator.py` (`execute_skill`, lines 180–215).
- **Reproduction:** `tests/reproduce_sprint_0_8_defects.py::test_defect_4_unhandled_failure_escapes_without_experience_record`.
- **Finding:** When a step raised an exception, `execute_skill()` failed immediately. Line 208 (`self.experience_collector.record_task_run(...)`) was never reached, causing execution failures and tool crashes to leave zero trace in the Learning Layer.

### Defect 5: Unrelated Knowledge Updates & Missing Feedback Idempotency
- **Location:** `libresprite_game_mcp/core/orchestrator.py` (`record_feedback`, lines 230–252).
- **Reproduction:** `tests/reproduce_sprint_0_8_defects.py::test_defect_5_feedback_updates_unrelated_rules_and_lacks_idempotency`.
- **Finding:** When feedback was recorded, `orchestrator.record_feedback` queried all rules matching the broad task category (`task_category="character"`) and indiscriminately bumped confidence on all of them (e.g., feedback on outline updated unrelated palette rules). Furthermore, repeated submissions of the same feedback incremented confidence unbounded.

---

## 3. Corrective Plan of Action

We will execute the remediation in 6 controlled stages:

1. **Stage 2 (Objective A & B):** Tool Contracts & Execution Engine.
   - Refactor `ProductionOrchestrator` to implement an explicit, real production dispatcher connecting to actual generators, QA validators, and exporters.
   - Implement `WorkflowEngine` with DAG dependency resolution, step output binding, cycle detection, and failure halting.
2. **Stage 3 (Objective C & D):** Real QA & Sandbox Separation.
   - Implement real file inspection in QA steps using `AssetValidator`.
   - Separate execution modes (`MOCK`, `SANDBOX`, `PRODUCTION`, `LIVE_RUNTIME`) and sandbox workspaces.
3. **Stage 4 (Objective E):** Governance & Immutability.
   - Seed reference skills as `DRAFT` (or `SANDBOX`).
   - Implement an explicit human review boundary.
   - Enforce immutability without `force=True`.
4. **Stage 5 (Objective F):** Learning Layer Reliability.
   - Expand `ExperienceRecord` to track execution, validation, QA, and human acceptance outcomes separately.
   - Guarantee experience logging inside `try/finally` blocks so failures are recorded.
   - Implement feedback provenance filtering and idempotency keys.
5. **Stage 6 (Objective G):** Evidence-Based Skill Synthesis.
   - Synthesize skills from multi-experience consensus, conservative conflict detection, and explicit provenance.
6. **Stage 7:** Full verification across all execution modes and comprehensive documentation.
