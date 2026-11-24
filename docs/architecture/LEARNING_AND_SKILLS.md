# LibreSprite Game MCP — Learning Layer & Skill Builder Architecture

**Version:** 1.0  
**Target Branch:** `feature/production-art-system`  
**Status:** Implemented & Verified  

---

## 1. Executive Summary

LibreSprite Game MCP has evolved from a tool-driven pixel art generator into an **experience-driven production system** governed by two core subsystems:

1. **Learning Layer:** Captures, structures, evaluates, and retrieves knowledge from production asset generation runs, automated QA audits, and human artist feedback.
2. **Skill Builder & Registry:** Converts validated knowledge and deterministic tool chains into reusable, versioned, testable **Skills** that execute approved workflows.

The operating model is strictly **Hybrid**:
- **Automated:** Experience collection, telemetry logging, QA audits, heuristic rule synthesis, sandbox test execution, and draft creation.
- **Human-in-the-Loop Governance:** Human approval is strictly mandatory before any Skill can transition from `SANDBOX` to `APPROVED`. Autonomous promotion or silent modification of production Skills is strictly forbidden.

---

## 2. System Architecture

```
                      +---------------------------------------+
                      |       MCP Client / Orchestrator      |
                      +-------------------+-------------------+
                                          |
                        +-----------------+-----------------+
                        |                                   |
                        v                                   v
             +--------------------+              +--------------------+
             |   Learning Layer   |              |   Skill Builder    |
             +--------------------+              +--------------------+
             | ExperienceCollector|              | SkillRegistry      |
             | FeedbackCollector  |              | SkillBuilder (MVP) |
             | OutcomeEvaluator   |              | SandboxEvaluator   |
             | KnowledgeManager   |              | LifecycleManager   |
             | KnowledgeRetriever |              +--------------------+
             +---------+----------+                         |
                       |                                    |
                       +-----------------+------------------+
                                         |
                                         v
                         +-------------------------------+
                         |   SQLite Storage + Artifacts  |
                         |   (WAL Mode + Foreign Keys)   |
                         |   - data/learning/learning.db |
                         |   - data/skills/<id>/<ver>/   |
                         +-------------------------------+
```

---

## 3. Learning Layer Architecture

### 3.1 Data Models
- **`ExperienceRecord`:** Captures `task_id`, `task_category`, `resolution`, `art_profile`, `tools_used`, `execution_time_ms`, `outcome` (success/failure/partial), and `qa_report`. Sanitizes all sensitive credentials (`session_token`, passwords).
- **`FeedbackRecord`:** Ingests human ratings (1.0 to 5.0), approval/rejection flags, and correction notes, linked to an `experience_id` with foreign-key cascade.
- **`KnowledgeRecord`:** Relational rules and Art Bible constraints containing conditions, recommendations, confidence scores (0.0 to 1.0), and source experience provenance.

### 3.2 Dynamic Confidence Scoring
Knowledge rule confidence adjusts dynamically based on empirical evidence:
- **QA Success:** `+0.05`
- **Human Approval (Rating 5.0):** `+0.10`
- **Human Correction (Rating 3.0):** `-0.05`
- **QA Critical Failure / Human Rejection:** `-0.15` to `-0.20`
- Scores are strictly clamped between `0.0` and `1.0`.

### 3.3 Multi-Tenant Project Isolation
The knowledge retriever enforces strict project scoping:
- **Universal Art Bible Rules (`project_id = None`):** Visible to all projects.
- **Project-Specific Rules (`project_id = "ProjectAlpha"`):** Isolated; Project Alpha can view universal rules and its own rules, but Project Beta's proprietary constraints are inaccessible.

---

## 4. Skill Builder & Registry

### 4.1 Declarative Manifest & Security Allowlist
Skills are declarative, JSON-serializable manifests (not arbitrary executable code).
Workflow steps invoke only approved MCP tool contracts:
- `generate_character`
- `generate_tileset`
- `generate_item`
- `validate_asset`
- `export_godot_spritesheet`
- `apply_outline`
- `apply_palette`
- `generate_walk_cycle`

**Security Boundary:** Any embedded `eval`, `exec`, `shell`, `cmd`, or arbitrary script parameters are detected and rejected by `SkillBuilder.validate_workflow()`.

### 4.2 Lifecycle State Machine & Human Governance
```
  [DRAFT] -------> [SANDBOX] ------(Human Approval)------> [APPROVED]
     |                |                                        |
     |                +----------(Rejected)--------> [DISABLED]|
     |                                                         v
     +-------------------------------------------------> [DEPRECATED]
```

- **Human Review Gate:** If `reviewer` is identified as `system`, `autonomous_agent`, `llm`, or `bot`, promotion to `APPROVED` raises `AutonomousApprovalError`.
- **Version Immutability:** Once a Skill is `APPROVED`, its database and filesystem manifest are immutable. Overwrites raise `ImmutableSkillError`. Any modification requires creating a bumped semver version (e.g. `1.1.0`).
- **Rollback:** `rollback_skill()` deprecates the flawed version and re-activates the previous stable version while logging full audit justification.

---

## 5. Storage Architecture

### 5.1 SQLite Database Schema (`data/learning/learning.db`)
Configured with `PRAGMA foreign_keys = ON;` and `PRAGMA journal_mode = WAL;`.
- `experiences`: Stores raw execution telemetry, tags, and QA audit results.
- `feedbacks`: Cascades from `experiences`.
- `knowledge`: Rules indexed by `project_id`, `category`, and `confidence_score`.
- `skills`: Master table for registered skills.
- `skill_versions`: Composite primary key `(skill_id, version)` with step workflows and validation criteria.
- `skill_executions`: Telemetry from individual workflow runs.
- `skill_evaluations`: Automated sandbox benchmark scores.
- `skill_approvals`: Audit logs recording human reviews, decisions, and comments.

### 5.2 Filesystem Layout
- `data/skills/<skill_id>/<version>/skill.json`: Versioned immutable skill manifests.
- `data/learning/`: SQLite database and local telemetry artifacts.

---

## 6. Reference Skill: `Pixel Character Consistency`

- **Identifier:** `pixel_character_consistency`
- **Version:** `1.0.0` (Status: `APPROVED`)
- **Manifest Location:** `data/skills/pixel_character_consistency/1.0.0/skill.json`
- **Pipeline:**
  1. `step_1_generate`: Invokes `generate_character` (16x16 chibi proportions).
  2. `step_2_outline`: Invokes `apply_outline` (colored outline, cleans orphan pixels).
  3. `step_3_validate`: Invokes `validate_asset` (QA color count, dimensions, stray pixels).
  4. `step_4_export`: Invokes `export_godot_spritesheet` (packs atlas and writes Godot 4 SpriteFrames).

---

## 7. Verification Evidence & Test Coverage

The test suite provides comprehensive coverage across all components:

| Test File | Description | Test Count | Status |
|-----------|-------------|------------|--------|
| `tests/test_learning_foundation.py` | Pydantic schemas, SQLite foreign keys, transactions, project isolation, semver | 11 | PASSED |
| `tests/test_experience_knowledge.py` | Experience normalization, credential masking, outcome scoring, knowledge confidence | 7 | PASSED |
| `tests/test_skill_registry_builder.py`| Workflow validation, tool allowlist, security injection checks, filesystem export | 6 | PASSED |
| `tests/test_skill_sandbox_approval.py`| Sandbox evaluation, human approval gate, invalid state transitions, rollback | 5 | PASSED |
| `tests/test_orchestrator_skills.py` | End-to-end skill discovery, execution, feedback ingestion, guidance retrieval | 5 | PASSED |
| `tests/test_relay_http_integration.py`| HTTP bridge security, token masking, payload limits | 10 | PASSED |
| `tests/test_corrective_suite.py` | Godot frame timing, workspace path traversal security | 5 | PASSED |
| `tests/test_production_system.py` | Art profiles, palettes, generators, and QA validators | 5 | PASSED |
| `tests/test_libresprite_live_runtime.py`| Production bridge execution inside live LibreSprite engine (`put_pixel`) | 1 | PASSED |
| **Total** | **Full Regression Suite** | **55** | **ALL PASSED** |
