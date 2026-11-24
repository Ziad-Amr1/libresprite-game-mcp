# Phase Zero: Comprehensive Repository & Asset Audit

**Repository:** `libresprite-game-mcp`  
**Date:** 2026-11-24  
**Audit Team:** Software Architect, Art Director, Technical Artist, Art QA Specialist, Pipeline Engineer, Godot Integration Specialist  

---

## 1. Executive Summary

The `libresprite-game-mcp` codebase provides an initial proof-of-concept MCP server connecting AI assistants to **LibreSprite** via both headless batch CLI and an HTTP-bridged live JavaScript script. It also leverages `aseprite` (Python) and `Pillow` to generate `.aseprite` files, packed sprite sheets, and Godot `.tres` resources.

While all unit checks in `tests/test_full_suite.py` pass their assertions, an in-depth code and visual inspection reveals critical architectural limitations, security vulnerabilities, artistic shortcomings, and a broken Godot 4 export syntax.

---

## 2. Architecture & Current Capabilities

```
libresprite-game-mcp/
├── config.py                 # LibreSprite path detection (heuristic & environment)
├── server.py                 # FastMCP server entrypoint & tool declarations
├── bridge/
│   ├── http_relay.py         # HTTP relay daemon on port 64823
│   └── libresprite_mcp_bridge.js # Script intended to run inside LibreSprite
├── core/
│   ├── aseprite_file.py      # Multi-frame, multi-layer Aseprite reader/writer
│   ├── cli_runner.py         # Subprocess runner for `libresprite.exe -b`
│   ├── palettes.py           # Hardcoded hex palettes (PICO-8, DB16, GB, etc.)
│   └── pixel_art_ops.py      # PixelCanvas with line, rect, dither, outline ops
├── generators/
│   ├── character_generator.py# Hardcoded 16x16 knight generator (idle, walk, attack, hurt)
│   ├── tileset_generator.py  # Hardcoded 4x3 autotile sheet (grass/dirt, dungeon, wood)
│   └── item_generator.py     # Hardcoded sword, potion, animated torch, coin
└── exporters/
    └── game_export.py        # Sprite sheet packing, Godot SpriteFrames, animated GIF
```

### Current Tool Capabilities:
1. `get_libresprite_status`: Inspects binary location, version string, scripts directory, and relay status.
2. `install_bridge_script`: Copies `libresprite_mcp_bridge.js` to LibreSprite's roaming scripts folder.
3. `list_game_palettes`: Returns supported built-in palettes.
4. `create_character_sprite`: Generates an animated character with 4 tags, `.aseprite`, sheet, JSON, GIF, and Godot `.tres`.
5. `create_autotile_tileset`: Renders a 4x3 tileset image and metadata JSON.
6. `create_game_item`: Renders swords, potions, torches, and spinning coins.
7. `export_asset_sprite_sheet`: Headless compilation via `libresprite.exe -b`.
8. `live_get_canvas_preview`: Grabs active canvas Base64 PNG via bridge relay.
9. `live_create_canvas` / `live_execute_js`: Executes JS scripts inside running LibreSprite instance.

---

## 3. Working vs. Incomplete / Broken Functionality

| Component | Status | Empirical Finding |
|---|---|---|
| **Python Aseprite Writer** (`core/aseprite_file.py`) | **Working with Flaws** | Creates valid `.aseprite` files readable by LibreSprite. However, leaves an empty orphan `Layer 1` when custom layer sets are created without renaming the initial layer. |
| **Headless CLI Exporter** (`core/cli_runner.py`) | **Working** | Successfully invokes `libresprite.exe -b --sheet ... --data ...` and outputs packed texture atlases. |
| **Godot 4 Exporter** (`exporters/game_export.py`) | **BROKEN at Engine Import** | Emits `{ "texture": SubResource("AtlasTexture_0") }` references in `animations`, but **fails to declare `[sub_resource type="AtlasTexture" id="AtlasTexture_0"]` blocks** with atlas texture and `region = Rect2(...)`! Godot 4 parser fails immediately upon import. |
| **Autotile Generator** (`generators/tileset_generator.py`) | **Incomplete / Toy Implementation** | Produces a 4x3 grid (12 tiles). Real autotiling engines (Godot Terrain, Tiled, RPG Maker) require 16-pipe Wang or 47-blob bitmasked sets to cover all interior/exterior corner combinations. |
| **Live GUI Bridge** (`bridge/libresprite_mcp_bridge.js`) | **High Security Risk** | Exposes unrestricted `eval(params.code)` via unauthenticated HTTP server on `127.0.0.1:64823`. Any local process can execute arbitrary code inside LibreSprite. |
| **Character Generator** (`generators/character_generator.py`) | **Rigid / Hardcoded** | Hardcodes a single 16x16 humanoid blocky knight. Does not support Art Profiles, blueprints, variable proportions, non-humanoid creatures, or custom styles. |
| **Color Quantization & Palettes** (`core/palettes.py`) | **Basic** | Supports Euclidean color distance, but lacks hue-shifting, color ramps, and palette-swapping matrixes. |

---

## 4. Visual Quality Audit (Art Team Perspective)

Our visual inspection of generated assets revealed:

1. **Single-Pixel Noise (Salt-and-Pepper Noise)**:
   - In `dungeon_walls.png`, brick texture is generated via `if rng.random() < 0.15: canvas.put_pixel(...)`.
   - **Art Critique**: This violates the fundamental rule of pixel art. Textures must be composed of deliberate **pixel clusters** (2-4 pixels minimum). Isolated 1-pixel noise makes game textures vibrate and look muddy on screen.
2. **Jaggies & Outline Inconsistencies**:
   - In `iron_blade.png`, diagonal lines contain double pixels where single-pixel steps are expected, creating jagged "steps" (jaggies) and inconsistent outline thickness.
3. **Flat Shading Without Hue Shifting**:
   - Character clothes and skin tones use flat brightness drops without shifting hue (e.g., highlights should shift towards warm yellow/orange, shadows towards cool violet/blue).
4. **No Modular Turnaround Consistency**:
   - The character generator does not produce consistent 4-direction sheets (front, side, back) sharing identical silhouette landmarks.

---

## 5. Security Vulnerabilities & Code Quality

### 🚨 Vulnerability 1: Arbitrary Code Execution in Bridge Relay
- **Location**: `bridge/libresprite_mcp_bridge.js:90` & `bridge/http_relay.py:100`
- **Impact**: `eval(params.code)` executes unvalidated JavaScript inside LibreSprite.
- **Remediation**: Remove unrestricted `eval`. Replace with an explicit **allowlisted command dispatch** (`draw_rect`, `set_palette`, `add_layer`, `save_file`, `get_canvas`).

### ⚠️ Vulnerability 2: Missing Path Traversal Sanitization
- **Location**: `server.py:export_asset_sprite_sheet` and file export tools.
- **Impact**: Unsanitized user-supplied paths can escape project boundaries.
- **Remediation**: Use `Path(resolved).is_relative_to(project_root)` or validate absolute output directories against allowlisted workspaces.

### ⚠️ Vulnerability 3: Orphan Layers in Aseprite Files
- **Location**: `core/aseprite_file.py`
- **Impact**: Default constructor `aseprite.Sprite(w, h)` initializes with `Layer 1`. Projects created via `add_layer` without overriding `Layer 1` carry blank layers into game engines.

---

## 6. Testing Gaps

1. Current test `tests/test_full_suite.py` only asserts file existence (`assert Path(...).exists()`), never validating:
   - Palette color adherence.
   - Godot 4 engine parsing validity.
   - Outline continuity or cluster cohesion.
   - Pixel dimensions or frame alignment across animations.
2. No automated unit tests for `core/pixel_art_ops.py` algorithms (Bresenham, flood fill, Bayer matrix).
3. No schema validation tests for art profiles or character blueprints.

---

## 7. Prioritized Recommendations for Sprint 0 & 1

1. **Immediate P0 Security Fix**: Remove arbitrary `eval` from the bridge; implement a typed, allowlisted command dispatcher.
2. **Immediate P0 Engine Fix**: Fix Godot 4 `SpriteFrames` export by generating full `AtlasTexture` sub-resource blocks with accurate region coordinates.
3. **Art Profile System (P1)**: Decouple generation from hardcoded styles. Define structured Pydantic schemas for `ArtProfile`, `CharacterBlueprint`, `TilesetSpec`, and `ItemSpec`.
4. **Art Bible & Knowledge Base (P1)**: Document pixel clustering, hue shifting, 47-blob autotiling, animation key-poses, and Godot specifications in `PIXEL_ART_BIBLE.md`.
5. **Automated QA Validator (P1)**: Build a dedicated validation module that analyzes pixel scale, color ramps, palette violations, and engine compliance.
