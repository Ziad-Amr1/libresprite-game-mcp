# Test Strategy: LibreSprite Production Verification

**Document:** `docs/testing/TEST_STRATEGY.md`  
**Version:** 2.1 (Live Bridge Runtime Verification & Reliability)  

---

## 1. Testing Philosophy

In game toolchains and live engine bridges, unit test green checks must correlate with real engine behavior and strict security invariants.

Every test tier must:
1. **Assert Negative Cases**: Verify that illegal paths, invalid commands, expired tokens, oversized payloads, and corrupt data fail with explicit typed exceptions or HTTP error codes.
2. **Assert Data Integrity**: Verify mathematical coordinates, frame durations, and color hex values rather than simple file existence.
3. **Execute Real Integration**: Network and bridge layers must run against real TCP sockets and real binaries, not solely mocked wrappers.
4. **Isolate Fixtures**: Never pollute production project folders with temporary test outputs.

---

## 2. Test Suites & Verification Tiers

### Suite 1: Security & Filesystem Boundary (`tests/test_corrective_suite.py::test_workspace_policy`)
* **Path Traversal**: Verifies that relative paths attempting `../` escape outside approved roots raise `PermissionError`.
* **Absolute Path Escaping**: Verifies that unauthorized drive roots (e.g. `C:\Windows`) raise `PermissionError`.
* **Symlink Resolution**: Verifies that symlinks resolving outside approved boundaries are rejected.
* **Bridge Allowlist & Prototype Pollution**: Verifies that `constructor`, `__proto__`, and unknown commands are rejected without evaluating object prototypes.
* **Payload Size Limits**: Verifies HTTP relay rejection of payloads exceeding 5 MB.

### Suite 2: Godot 4.x Exporter Timing & Atlas Regions (`test_godot_exporter_timing_and_atlas`)
* **Duration Preservation**: Verifies that non-uniform frame durations (e.g., 300ms, 150ms, 100ms) export accurate float duration factors relative to base frame time ($1000/\text{fps}$).
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

### Suite 5: Real HTTP Relay Integration (`tests/test_relay_http_integration.py`)
* **Authentication**: Verifies that `/poll` and `/result` return 401 for unauthenticated requests and 200 for valid tokens across HTTP headers, query params (`?token=`), and JSON body (`session_token`).
* **Command Lifecycle**: Verifies queuing, popping, execution correlation, and result delivery over real TCP HTTP connections.
* **Concurrency Safety**: Verifies that concurrent `queue_command` calls are rejected rather than overwriting in-flight commands.
* **Timeout & Stale Responses**: Verifies that timed-out commands do not capture later delayed responses and late responses are flagged as `ignored`.
* **Duplicate Result Handling**: Verifies that duplicate delivery of matching command results is ignored.
* **Payload Bounds**: Verifies that payloads $> 5$ MB return 413, and malformed JSON returns 400.
* **Token Rotation**: Verifies that `rotate_session_token()` invalidates old credentials immediately.
* **Server Lifecycle**: Verifies clean shutdown, port release, and restart on the same port.

### Suite 6: Live Engine Runtime Verification (`tests/test_libresprite_live_runtime.py`)
* **Live Binary Execution**: Spawns actual `libresprite.exe --script <test_script.js>`.
* **Token Handshake**: Verifies that LibreSprite loads the session token from `%APPDATA%\LibreSprite\`, authenticates with the relay, retrieves queued commands, executes them, returns correlated results, and shuts down cleanly via `app.command.Exit()`.

---

## 3. Engine Environment Verification Matrix

| Engine | Local Environment Status | Test Tier Applied | Outcome |
| :--- | :--- | :--- | :---: |
| **LibreSprite 1.1-dev** | Installed (`libresprite.exe` detected) | Live Process & TCP Roundtrip | **PASS** |
| **Godot 4.x** | Not installed (`godot` command not found) | Static Syntax & Resource Structural Analysis | **NOT EXECUTED** (Syntax: **PASS**) |

*Note: Godot engine syntax and resource files (`.tres`) have passed 100% structural verification according to the Godot 4.x text resource specification. Headless engine import testing must be executed in a CI/CD environment equipped with `godot.exe`.*
