# LibreSprite Game MCP: Bridge Security Model & Architecture

**Document:** `docs/security/BRIDGE_SECURITY.md`  
**Version:** 2.2 (Body-Only Authentication, Token Storage Hardening & Masking)  
**Threat Model & Implementation Standards**  

---

## 1. Threat Model & Attack Vectors

The LibreSprite Live GUI bridge operates via a local HTTP relay daemon listening strictly on loopback (`127.0.0.1:64823`) to communicate with the JavaScript scripting engine inside LibreSprite.

### Threat Vectors Analyzed:
1. **Cross-Origin Browser Hijacking (CSRF / DNS Rebinding)**:
   - *Risk*: A malicious website opened in a developer's browser could issue background requests to `http://127.0.0.1:64823`.
   - *Exploit*: With wildcard CORS (`Access-Control-Allow-Origin: *`), the browser permits cross-origin reading and command execution.
2. **Session Hijacking & Unauthorized Local Access**:
   - *Risk*: Other untrusted processes running on the local host attempting to inject commands into the LibreSprite workspace.
3. **URL Query Parameter Credential Leakage**:
   - *Risk*: Passing authentication tokens in URL query strings exposes credentials in HTTP server access logs, reverse proxies, and error traces.
4. **Prototype Pollution / Object Property Exploitation**:
   - *Risk*: JavaScript objects check properties up the prototype chain.
   - *Exploit*: Sending `cmdType: "constructor"`, `"toString"`, or `"__proto__"` passes standard `cmdType in ALLOWED_COMMANDS` checks and executes native object prototypes.
5. **Race Conditions, Command Overwriting & Stale Response Captures**:
   - *Risk*: Concurrent tool invocations overwriting pending commands, or delayed responses from timed-out commands being mistakenly consumed by a subsequent command.
6. **Deadlocks in Multithreaded Relay**:
   - *Risk*: Nested lock acquisition within the relay daemon freezing the MCP server and hanging tool requests.
7. **Denial of Service via Unbounded Dimensions**:
   - *Risk*: Passing coordinates or dimensions like `w: 10000000` causes huge pixel iteration loops, hanging the LibreSprite UI.
8. **Arbitrary Filesystem Write**:
   - *Risk*: Unvalidated `save_sprite` with `path: "C:\\Windows\\System32\\..."` allows saving over critical system files.
9. **Memory Exhaustion via Oversized Payloads**:
   - *Risk*: Sending gigabyte-sized payloads to `/poll` or `/result` exhausts daemon heap space.
10. **Silent Token Storage Failure**:
    - *Risk*: Swallowing filesystem or permission errors during token generation leads to broken or unauthenticated states that falsely appear operational.

---

## 2. Hardened Mitigations & Protocol Specification

### A. Per-Session Local Trust Token Lifecycle
* **Cryptographic Generation**:
  On daemon initialization, `http_relay.py` generates a cryptographically secure 128-bit hex token:
  ```python
  session_token = secrets.token_hex(16)
  ```
* **Dual Storage Channels & Domain Binding**:
  The token is written to two locations inside the user's private application roaming directory (`%APPDATA%\LibreSprite\`):
  1. `%APPDATA%\LibreSprite\libresprite_mcp_bridge.js.session_token`:
     Directly ingested by LibreSprite's Duktape native `storage.load("session_token", SCRIPT_DOMAIN)`.
  2. `%APPDATA%\LibreSprite\mcp_session_token.json`:
     Structured JSON document containing `{ "session_token": "...", "port": 64823 }` for external tools.
* **Storage Reliability Enforcement**:
  `_write_session_token()` validates the directory path, captures permissions or I/O errors, records them in `state.token_error`, and sets `state.token_provisioned = False`. If provisioning fails, all requests are rejected and tools report provisioning errors explicitly.
* **Body-Only & Header Authentication**:
  LibreSprite's C++ `storage.fetch` supports only a single header key/value pair (reserved for `Content-Type: application/json`). The relay accepts the session token strictly via:
  1. `X-MCP-Token` HTTP Header (for standard HTTP clients/tests)
  2. `{"session_token": "<token>"}` in JSON request body (for LibreSprite `storage.fetch`)
  *URL query parameters (`?token=`) are strictly forbidden and rejected with 401.*
* **Constant-Time Verification**:
  Tokens are verified using `secrets.compare_digest` to prevent timing side-channel attacks.
* **Credential Masking**:
  All logs, diagnostics, and documentation mask tokens (e.g. `26239d...[MASKED]`).
* **Token Rotation**:
  Calling `state.rotate_session_token()` updates disk credentials and immediately invalidates any connection presenting the old token.

### B. Concurrency Architecture & Deadlock Prevention
* **Locking Strategy**:
  State synchronization uses a non-reentrant `threading.Lock()` rather than `RLock`.
* **Explicit Locked Boundary Helpers**:
  Methods requiring the lock are explicitly named `_method_locked` (e.g. `_is_alive_locked`). Public methods acquire `self.lock` and delegate to locked helpers, eliminating recursive self-deadlocks.
* **Out-of-Lock Network Wait**:
  In `queue_command()`, `self.lock` is released before calling `self.command_event.wait(timeout=timeout)`. This allows incoming HTTP request handler threads to acquire `self.lock` and deliver results without contention.

### C. Command Lifecycle Reliability & Correlation
* **UUID Correlation (`command_id`)**:
  Every queued command is assigned a unique UUID `command_id = str(uuid.uuid4())`. Responses must echo this exact UUID.
* **Concurrency Guard (No Overwrites)**:
  If a command is already in-flight (`self.active_command_id is not None`), subsequent commands are rejected with:
  `"A command is already pending execution in LibreSprite. Concurrent execution is rejected."`
* **Stale Response Discarding**:
  If a command times out, `self.active_command_id` is reset to `None`. Late-arriving responses are safely rejected with `{"status": "ignored", "reason": "stale_or_invalid_command_id"}` and cannot corrupt future commands.
* **Duplicate Result Handling**:
  Once a matching result unblocks `queue_command()`, `self.active_command_id` is cleared. Any duplicate delivery of the same result is ignored.

### D. Network & Payload Security
* **Strict Loopback Binding**:
  The HTTP relay binds strictly to `127.0.0.1`. It never binds to `0.0.0.0`.
* **CORS Elimination**:
  Cross-origin headers (`Access-Control-Allow-Origin`) are completely removed, neutralizing web browser CSRF and DNS rebinding attacks.
* **Nosniff Header**:
  Every response emits `X-Content-Type-Options: nosniff`.
* **Payload Size Limits**:
  `Content-Length` is validated before reading bodies. Payloads exceeding **5 MB** (`MAX_PAYLOAD_BYTES = 5 * 1024 * 1024`) are rejected with `413 Payload Too Large` and connection close.
* **Malformed JSON Validation**:
  Malformed or non-object payloads return `400 Bad Request`.

### E. Safe Own-Property Command Allowlist
Commands in `libresprite_mcp_bridge.js` are validated using strict own-property checks:
```javascript
if (!Object.prototype.hasOwnProperty.call(ALLOWED_COMMANDS, cmdType)) {
    throw new Error("Command not in allowlist");
}
```
Properties inherited from prototypes (`constructor`, `toString`, `valueOf`, `__proto__`) are rejected.

### F. Parameter Typing & Boundary Constraints
* **`create_canvas`**: $1 \le \text{width}, \text{height} \le 2048$, `colorMode` in `{"rgba", "indexed"}`.
* **`put_pixel`**: $0 \le x < \text{width}$, $0 \le y < \text{height}$, $r, g, b, a \in [0, 255]$. Returns internal readback verification.
* **`draw_rect`**: $1 \le w, h \le 2048$, coordinates clamped to image dimensions.
* **`save_sprite`**: Traversal sequences (`..`) strictly rejected; workspace boundaries enforced.
* **`exit_session`**: Closes the active session and exits LibreSprite cleanly.
