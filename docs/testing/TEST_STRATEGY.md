# Test Strategy: LibreSprite Production Verification

**Document:** `docs/testing/TEST_STRATEGY.md`  
**Version:** 2.0 (Corrective Sprint)  

---

## 1. Testing Philosophy

In game toolchains, unit test green checks must correlate with real engine behavior and strict security invariants.

Every test must:
1. **Assert Negative Cases**: Verify that illegal paths, invalid commands, and corrupt data fail with explicit typed exceptions.
2. **Assert Data Integrity**: Verify mathematical coordinates, frame durations, and color hex values rather than simple file existence.
3. **Isolate Fixtures**: Never pollute production project folders with temporary test outputs.

---

## 2. Test Suites

### Suite 1: Security & Filesystem Boundary (`tests/test_corrective_suite.py::test_workspace_policy`)
* **Path Traversal**: Verifies that relative paths attempting `../` escape outside approved roots raise `PermissionError`.
* **Absolute Path Escaping**: Verifies that unauthorized drive roots (e.g. `C:\Windows`) raise `PermissionError`.
* **Symlink Resolution**: Verifies that symlinks resolving outside approved boundaries are rejected.
* **Bridge Allowlist & Prototype Pollution**: Verifies that `constructor`, `__proto__`, and unknown commands are rejected without evaluating object prototypes.
* **Payload Size Limits**: Verifies HTTP relay rejection of payloads exceeding 5 MB.

### Suite 2: Godot 4.x Exporter Timing & Atlas Regions (`test_godot_exporter_timing_and_atlas`)
* **Duration Preservation**: Verifies that non-uniform frame durations (e.g., 300ms, 120ms, 100ms) export accurate float duration factors relative to base frame time ($1000/\text{fps}$).
* **Atlas Boundary Checks**: Verifies that `Rect2` regions exceeding total sheet dimensions throw `ValueError`.
* **Tag Range Clamping**: Verifies that inverted (`from > to`) or out-of-bounds tags are safely clamped.
* **SubResource Syntax**: Verifies all `[sub_resource type="AtlasTexture"]` blocks match `SubResource("AtlasTexture_{i}")` references in animations.

### Suite 3: Art QA Validator (`test_qa_validator_enhancements`)
* **Anchor Pivot Baseline**: Verifies that foot baseline calculation restricts evaluation to the central contact zone, avoiding false drift warnings from side weapons or dust.
* **Configurable Alpha**: Verifies that `allow_translucent=False` flags `0 < a < 255` as critical errors, whereas `allow_translucent=True` accepts them with a warning.
* **Orphan Cluster Detection**: Verifies detection of isolated single pixels with 0 orthogonal neighbors.
* **Custom Palettes**: Verifies validation against arbitrary user-provided hex lists.

### Suite 4: Blueprint & ArtProfile Integration (`test_blueprint_pipeline`)
* **Pydantic Validation**: Verifies that malformed blueprints fail schema validation before touching generators.
* **Blueprint to Asset**: Verifies that `create_character_from_blueprint` renders animations and tags matching the blueprint specification.
* **Legacy Compatibility**: Verifies that `create_character_sprite` translates legacy arguments to `CharacterBlueprint` without breaking older clients.

---

## 3. Engine Environment Verification Note

* **Godot 4 Engine Status**: Not installed in local environment (`Get-Command godot` is null).
* **Test Policy**: All Godot tests in this suite are **Static Syntax & Structural Verification Tests**. They guarantee 100% adherence to the Godot 4 text resource specification (`.tres` format version 3). Engine runtime validation must be performed in an environment hosting `godot.exe`.
