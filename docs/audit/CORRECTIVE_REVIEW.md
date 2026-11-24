# Corrective Engineering Review: Sprint 0 Foundation Audit

**Document:** `docs/audit/CORRECTIVE_REVIEW.md`  
**Date:** 2026-11-24  
**Audit Team:** Software Architect, Pipeline Engineer, Technical Artist, Art QA Specialist, Godot Specialist  

---

## 1. Executive Summary

Following the push of `feature/production-art-system`, an independent corrective review was conducted on the committed codebase. Rather than relying on passing tests, the code was scrutinized against production failure modes, security vectors, and game engine specifications.

Four major defects were formally reproduced with empirical evidence (`tests/reproduce_defects.py`):
1. **Critical Path Traversal Vulnerability**: `safe_resolve_output_dir` resolved paths without enforcing an approved workspace boundary.
2. **Animation Duration Loss in Godot 4.x Exporter**: All frames were hardcoded to `duration = 1.0`, completely discarding Aseprite frame timing (`duration_ms`).
3. **Flawed Foot Baseline Alignment in QA Validator**: Scanning all opaque pixels across the entire width caused weapons or particle effects to be misdiagnosed as foot drift.
4. **Bridge Command Object Property Pollution**: `cmdType in ALLOWED_COMMANDS` was vulnerable to prototype inheritance keys (`constructor`, `toString`, `__proto__`).

---

## 2. Reproduced Defects & Root Cause Analysis

### Defect 1: Workspace Path Traversal
* **Severity**: **P0 (Security Vulnerability)**
* **Reproduction**: Passing `output_dir = "../../test_escape_dir"` resolved to `E:\course\03_Programming_Data\AI\test_escape_dir` outside the current workspace without throwing an exception.
* **Root Cause**: `safe_resolve_output_dir` called `Path(output_dir).resolve()` and `mkdir()`, lacking any `is_relative_to(approved_root)` check.
* **Fix**: Implement a strict `WorkspacePolicy` class with approved root registries, symlink resolution, and strict containment verification.

### Defect 2: Godot 4.x Frame Duration Factor Loss
* **Severity**: **P0 (Engine Integration Flaw)**
* **Reproduction**: An animation with a 300ms anticipation frame and a 100ms action frame exported both frames as `"duration": 1.0` in the Godot `.tres` resource.
* **Root Cause**: Hardcoded string formatting `f'    {{ "duration": 1.0, "texture": SubResource(...) }},'` in `exporters/game_export.py`.
* **Fix**: Compute Godot duration factor relative to animation speed:
  $$\text{duration\_factor} = \frac{\text{frame.duration\_ms}}{\text{base\_frame\_ms}} = \frac{\text{frame.duration\_ms}}{1000.0 / \text{fps}}$$
  Ensure standard rounding or exact float representation.

### Defect 3: QA Validator Foot Baseline Inaccuracy
* **Severity**: **P1 (Quality Control Flaw)**
* **Reproduction**: A character holding a weapon pointing downward at $y=15$ while feet remained stationary at $y=12$ was falsely flagged with a 3px foot baseline drift warning.
* **Root Cause**: The validator inspected `max(y)` across all columns ($x \in [0, \text{width}]$) instead of anchoring to the character's central foot contact zone.
* **Fix**: Introduce an explicit `anchor_pivot` parameter (default `(0.5, 0.9)`) and evaluate baseline stability only within the foot zone (central 40% of width).

### Defect 4: Bridge Command Property Lookup Vulnerability
* **Severity**: **P0 (Security Vulnerability)**
* **Reproduction**: Calling a command named `"constructor"` or `"__proto__"` passes `in` check on JavaScript objects.
* **Root Cause**: `cmdType in ALLOWED_COMMANDS` checks the prototype chain.
* **Fix**: Use `Object.prototype.hasOwnProperty.call(ALLOWED_COMMANDS, cmdType)` and validate parameter types and bounds strictly.

---

## 3. Corrective Implementation Plan

1. **`libresprite_game_mcp/core/security.py`**:
   - `WorkspacePolicy`: Manage approved roots (`Path.cwd()`, `get_default_assets_dir()`).
   - `safe_resolve_path()`: Enforce containment, reject escapes, handle symlinks.
2. **`libresprite_game_mcp/bridge/http_relay.py` & `libresprite_mcp_bridge.js`**:
   - Add local session authentication token (`X-MCP-Token` header).
   - Restrict CORS (remove wildcard `*`).
   - Enforce 5MB payload limit.
   - Enforce own-property check and parameter typing on bridge commands.
3. **`libresprite_game_mcp/exporters/game_export.py`**:
   - Implement dynamic frame duration calculation for Godot 4.
   - Validate atlas regions against actual PNG dimensions.
4. **`libresprite_game_mcp/qa/validator.py`**:
   - Add foot contact zone filtering based on anchor pivot.
   - Add pixel cluster analysis (orphan pixel detection).
   - Make alpha hygiene rule configurable (`allow_translucent: bool = False`).
5. **`libresprite_game_mcp/server.py`**:
   - Integrate `CharacterBlueprint` with migration adapter from legacy arguments.
   - Replace old path resolver with `WorkspacePolicy`.
