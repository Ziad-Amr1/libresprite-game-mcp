# LibreSprite Game Asset MCP Server 🎮🎨

A professional **Model Context Protocol (MCP)** server engineered for **game developers** and **pixel artists** to generate, animate, edit, validate, and export 2D game assets using **LibreSprite** and **Godot 4.x**.

---

## 🌟 Key Capabilities

* **Multi-Layered Animated Characters**:
  * Procedural generation of 2D characters with standard animation tags: `idle`, `walk`, `attack`, `hurt`.
  * Clean, named layer structure: `Shadow`, `Body`, `Clothes`, `Gear`.
  * Native `.aseprite` format output with zero orphan layers for seamless editing inside LibreSprite.

* **Godot 4.x Native Integration**:
  * Generates 100% syntactically valid Godot 4 `.tres` (`SpriteFrames`) resources.
  * Fully declares `[sub_resource type="AtlasTexture"]` blocks with exact `Rect2` regions and frame durations.
  * Direct drop-in compatibility with Godot's `AnimatedSprite2D`.

* **Automated Art QA Validation Engine**:
  * Automated checks for palette compliance, binary alpha hygiene (zero translucent border pixels), dimension checks, and animation foot baseline alignment.
  * Generates structured `ValidationReport` objects prior to export.

* **Autotile 3x3 Tilesets**:
  * Autotile sheets with corners, edges, center, and island tiles.
  * Built-in themes: `grass_dirt`, `stone_dungeon`, `wood_planks`.
  * Exports texture atlas PNG and tile metadata JSON.

* **Curated Retro Game Palettes**:
  * PICO-8 (16 colors), Game Boy Classic / Pocket (4 shades), DawnBringer 16/32, Endesga 32, Sweetie 16, Cyberpunk Neon.

* **Dual Connection Modes & Security Hardening**:
  * **Headless Batch Pipeline**: Runs in the background with zero GUI friction using LibreSprite's CLI (`libresprite.exe -b`) and native Python generators.
  * **Secure Live GUI Bridge**: Communicates with LibreSprite through an allowlisted command dispatcher (`libresprite_mcp_bridge.js`) prohibiting arbitrary code execution.

---

## 📚 Studio Documentation

Comprehensive documentation engineered by the multidisciplinary AI Art & Tech team:

* **[Initial Audit](docs/audit/INITIAL_AUDIT.md)**: Repository code audit, architectural evaluation, security risks, visual quality findings, and testing gaps.
* **[Pixel Art Bible](docs/art-bible/PIXEL_ART_BIBLE.md)**: Technical pixel art principles (pixel clusters, line hygiene, hue shifting, outlines, dithering discipline, character proportions, animation principles, 47-blob autotiling).
* **[AI Art Team Architecture](docs/architecture/AI_ART_TEAM.md)**: Centralized orchestrator workflow, specialist role contracts (Art Director, Character Designer, Pixel Artist, Animator, Technical Artist, QA Specialist, Godot Specialist), and concurrency safeguards.
* **[Asset Specification](docs/architecture/ASSET_SPECIFICATION.md)**: Structured Pydantic schemas for Project Art Profiles, Character Blueprints, Tileset Specs, and Item Specs.
* **[Production Workflow](docs/workflows/AI_ASSET_WORKFLOW.md)**: Standard 10-step asset production lifecycle from game brief to engine import and approval.
* **[Technical Roadmap](docs/roadmap/TECHNICAL_ROADMAP.md)**: Phased development plan from Phase 0 to Phase 4.

---

## 🚀 Quickstart & Setup

### 1. Installation

From the project root:
```bash
pip install -e .
```

### 2. Configure Your MCP Client

Add the following block to your MCP client configuration (e.g., `claude_desktop_config.json`, Cursor `mcp.json`, or Antigravity):

```json
{
  "mcpServers": {
    "libresprite-game": {
      "command": "python",
      "args": ["-m", "libresprite_game_mcp.server"]
    }
  }
}
```

### 3. Optional: Live LibreSprite GUI Mode
The secure bridge script `libresprite_mcp_bridge.js` is automatically installed into your LibreSprite scripts folder:
* Windows: `%APPDATA%\LibreSprite\scripts\libresprite_mcp_bridge.js`
* Linux: `~/.config/libresprite/scripts/libresprite_mcp_bridge.js`

To use live mode:
1. Open LibreSprite.
2. Go to **File** $\rightarrow$ **Scripts** $\rightarrow$ **libresprite_mcp_bridge.js**.
3. Click **Connect**.

---

## 🛠️ Tool Reference

| Tool | Description |
|---|---|
| `get_libresprite_status` | Returns LibreSprite installation, CLI batch status, and live GUI connection state. |
| `install_bridge_script` | Re-installs or updates the secure bridge script in LibreSprite's scripts folder. |
| `list_game_palettes` | Lists all retro game palettes (PICO-8, DB16, DB32, Game Boy, EDG32, etc.). |
| `create_character_sprite` | Generates multi-layered animated character with idle/walk/attack/hurt tags, `.aseprite`, sheet PNG/JSON, GIF, and Godot 4 `.tres`. |
| `create_autotile_tileset` | Generates 3x3 autotile sheet and tile coordinate metadata JSON. |
| `create_game_item` | Generates swords, potion flasks, animated torches, or spinning coins. |
| `export_asset_sprite_sheet` | Packs any `.ase` or `.aseprite` file into a padded texture atlas with metadata. |
| `validate_game_asset` | Runs automated Art QA verifying palette compliance, binary alpha hygiene, and dimensions. |
| `live_get_canvas_preview` | Grabs live canvas snapshot from running LibreSprite as Base64 PNG. |
| `live_create_canvas` | Creates a new canvas inside open LibreSprite GUI. |
| `live_execute_safe_command` | Runs allowlisted operations securely inside open LibreSprite session. |
