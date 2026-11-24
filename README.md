# LibreSprite Game Asset MCP Server 🎮🎨

A high-performance **Model Context Protocol (MCP)** server specifically engineered for **game developers** and **pixel artists** to generate, animate, edit, and export 2D game assets using **LibreSprite**.

---

## 🌟 Features

* **Multi-Layered Animated Characters**:
  * Procedural generation of 2D heroes, monsters, and NPCs.
  * Standard game animation states with tags: `idle`, `walk`, `attack`, `hurt`.
  * Modular layer structure: `Shadow`, `Body`, `Clothes`, `Gear`.
  * Native `.aseprite` format output for full editing inside LibreSprite.

* **Autotile 3x3 Tilesets**:
  * 3x3 autotile sheets with corners, edges, center, and island tiles.
  * Themes: `grass_dirt`, `stone_dungeon`, `wood_planks`.
  * Exports texture atlas PNG and tile metadata JSON.

* **Game Items & Animated Props**:
  * Weapons: Diagonal RPG swords, staves, daggers.
  * Potions: Flasks with liquid highlights (`health`, `mana`, `stamina`, `elixir`).
  * Animated Props: 4-frame dungeon wall torch (dancing flame) and 4-frame spinning gold coin.

* **Game Engine Exporters**:
  * **Godot 4.x**: Exports `.tres` (`SpriteFrames`) resource ready to drop into `AnimatedSprite2D`.
  * **TexturePacker / Aseprite JSON**: Industry standard JSON Hash/Array sprite sheet format with frame durations, trims, and tags.
  * **Animated GIF**: Scaled pixel-crisp previews for chat and documentation.

* **Curated Retro Game Palettes**:
  * PICO-8 (16 colors)
  * Game Boy Classic / Pocket (4 shades)
  * DawnBringer 16 (DB16) & DawnBringer 32 (DB32)
  * Endesga 32 (EDG32)
  * Sweetie 16
  * Cyberpunk Neon & Monochrome

* **Dual Connection Modes**:
  1. **Headless Batch Pipeline**: Runs in the background with zero GUI friction using LibreSprite's CLI (`libresprite.exe -b`) and native Python generators.
  2. **Live Interactive GUI Bridge**: Connects directly to an open LibreSprite window via `libresprite_mcp_bridge.js` to draw live, inspect canvases, and execute commands in real-time.

---

## 🚀 Quickstart & Setup

### 1. Installation

From the project root:
```bash
pip install -e .
```

### 2. Configure Your MCP Client

Add the following block to your MCP client configuration (e.g., `claude_desktop_config.json`, Cursor `mcp.json`, or Antigravity):

#### Windows
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

*(Optional: If LibreSprite is installed in a non-standard location, set the `LIBRESPRITE_EXE` environment variable to its full path).*

### 3. Optional: Live LibreSprite GUI Mode
The bridge script `libresprite_mcp_bridge.js` is automatically installed into your LibreSprite scripts folder:
* Windows: `%APPDATA%\LibreSprite\scripts\libresprite_mcp_bridge.js`
* Linux: `~/.config/libresprite/scripts/libresprite_mcp_bridge.js`

To use live mode:
1. Open LibreSprite.
2. Go to **File** $\rightarrow$ **Scripts** $\rightarrow$ **libresprite_mcp_bridge.js**.
3. Click **Connect**. The AI can now draw live on your canvas and retrieve live previews!

---

## 🛠️ Tool Reference

| Tool | Description |
|---|---|
| `get_libresprite_status` | Returns LibreSprite installation, CLI batch status, and live GUI connection state. |
| `install_bridge_script` | Re-installs or updates the bridge script in LibreSprite's scripts folder. |
| `list_game_palettes` | Lists all retro game palettes (PICO-8, DB16, DB32, Game Boy, EDG32, etc.). |
| `create_character_sprite` | Generates multi-layered animated character with idle/walk/attack/hurt tags, `.aseprite`, sheet PNG/JSON, and Godot `.tres`. |
| `create_autotile_tileset` | Generates 3x3 autotile sheet and tile coordinate metadata JSON. |
| `create_game_item` | Generates swords, potion flasks, animated torches, or spinning coins. |
| `export_asset_sprite_sheet` | Packs any `.ase` or `.aseprite` file into a padded texture atlas with metadata. |
| `live_get_canvas_preview` | Grabs live canvas snapshot from running LibreSprite as Base64 PNG. |
| `live_create_canvas` | Creates a new canvas inside open LibreSprite GUI. |
| `live_execute_js` | Runs custom JavaScript code inside open LibreSprite session. |

---

## 📂 Example Output Structure

```
game_assets/
├── hero.aseprite              # Native LibreSprite editable project
├── hero_sheet.png             # Packed texture atlas
├── hero_sheet.json            # Frame coordinates, tags, and durations
├── hero_preview.gif           # Crisp 4x animated GIF preview
├── hero_spriteframes.tres     # Godot 4 AnimatedSprite2D resource
├── world_tiles.png            # 3x3 autotile sheet
├── world_tiles.json           # Tile boundary and collision data
└── dungeon_torch.gif          # 4-frame animated prop
```
