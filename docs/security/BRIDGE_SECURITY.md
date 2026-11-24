# LibreSprite Game MCP: Bridge Security Model & Architecture

**Document:** `docs/security/BRIDGE_SECURITY.md`  
**Version:** 2.0 (Hardened)  
**Threat Model & Implementation Standards**  

---

## 1. Threat Model & Attack Vectors

The LibreSprite Live GUI bridge operates via a local HTTP relay daemon listening on `127.0.0.1:64823` to communicate with the JavaScript scripting engine inside LibreSprite.

### Threat Vectors Analyzed:
1. **Cross-Origin Browser Hijacking (CSRF / DNS Rebinding)**:
   - *Risk*: A malicious website opened in any web browser could issue background `fetch("http://127.0.0.1:64823/execute", ...)` requests.
   - *Exploit*: With wildcard CORS (`Access-Control-Allow-Origin: *`), the browser would allow arbitrary command transmission.
2. **Prototype Pollution / Object Property Exploitation**:
   - *Risk*: JavaScript objects check properties up the prototype chain.
   - *Exploit*: Sending `cmdType: "constructor"`, `"toString"`, or `"__proto__"` passes `cmdType in ALLOWED_COMMANDS` and executes native object prototypes.
3. **Denial of Service via Unbounded Dimensions**:
   - *Risk*: Passing coordinates or dimensions like `w: 10000000` causes huge pixel iteration loops, hanging the LibreSprite UI.
4. **Arbitrary Filesystem Write**:
   - *Risk*: Unvalidated `save_sprite` with `path: "C:\\Windows\\System32\\..."` allows saving over critical system files.
5. **Memory Exhaustion via Oversized Payloads**:
   - *Risk*: Sending gigabyte-sized payloads to `/poll` or `/result` exhausts daemon heap space.

---

## 2. Hardened Mitigations & Protocol Specification

### A. Per-Session Local Trust Token
* On server initialization, `http_relay.py` generates a cryptographically secure 128-bit hex token:
  ```python
  SESSION_TOKEN = secrets.token_hex(16)
  ```
* The token is written to a user-private configuration file (`mcp_session_token.json`) inside LibreSprite's secure roaming directory (`%APPDATA%\LibreSprite\`).
* Every request to `/poll` or `/result` must provide this token via the `X-MCP-Token` header or `?token=` query parameter.
* Unauthenticated requests are rejected immediately with HTTP `401 Unauthorized`.

### B. CORS Elimination
* Cross-Origin headers are restricted. Because LibreSprite's C++ `storage.fetch()` engine is a native client and not a browser webview, wildcard `Access-Control-Allow-Origin: *` is completely removed.

### C. Request Payload Limit
* HTTP request bodies are limited to a strict maximum of **5 MB** (`5 * 1024 * 1024` bytes).
* Any request specifying `Content-Length > 5MB` receives HTTP `413 Payload Too Large`.

### D. Safe Own-Property Command Dispatch
* Commands inside `libresprite_mcp_bridge.js` are validated using strict prototype-safe checks:
  ```javascript
  if (!Object.prototype.hasOwnProperty.call(ALLOWED_COMMANDS, cmdType)) {
      throw new Error("Command not in allowlist");
  }
  ```

### E. Parameter Typing & Boundary Constraints
* **`create_canvas`**:
  * Width: $1 \le \text{width} \le 2048$
  * Height: $1 \le \text{height} \le 2048$
  * ColorMode: only `"rgba"` or `"indexed"`
* **`put_pixel`**:
  * $x, y \ge 0$ and bounded by active image dimensions
  * $r, g, b, a \in [0, 255]$
* **`draw_rect`**:
  * $w, h \ge 1$ and bounded by active image dimensions
* **`save_sprite`**:
  * Path must not contain `..` or unapproved absolute directory structures.
