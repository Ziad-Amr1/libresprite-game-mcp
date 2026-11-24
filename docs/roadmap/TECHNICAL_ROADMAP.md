# Technical Roadmap: LibreSprite Professional Game MCP

**Strategic Plan for Production-Grade AI Pixel Art Architecture**  
**Version:** 1.0  

---

## 1. Roadmap Overview

```
┌─────────────────────────────────┐
│ Phase 0: Audit & Foundation     │ ◄── [COMPLETED IN SPRINT 0]
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Phase 1: Hardening & Schemas    │ ◄── [CURRENT SPRINT]
│ - Security: Allowlist bridge    │
│ - Godot 4: Valid SubResources   │
│ - Pydantic: ArtProfile & Specs  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Phase 2: Decoupled Studios      │
│ - Character Studio & Blueprints │
│ - 47-Blob Autotile Generator    │
│ - Hue-Shifted Color Engine      │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Phase 3: Automated QA Suite     │
│ - Palette Compliance Checker    │
│ - Cluster & Jaggy Analyzer      │
│ - Godot Resource Verifier       │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│ Phase 4: Bi-Directional GUI Sync│
│ - Real-time LibreSprite Canvas  │
│ - In-Editor Layer Selection     │
│ - Godot Live Project Importer   │
└─────────────────────────────────┘
```

---

## 2. Detailed Phase Breakdown

### Phase 0: Audit & Art Foundation (Sprint 0 — Completed)
* [x] Full repository audit (`docs/audit/INITIAL_AUDIT.md`).
* [x] Pixel Art Bible with evidence-based rules (`docs/art-bible/PIXEL_ART_BIBLE.md`).
* [x] AI Art Team Architecture and role contracts (`docs/architecture/AI_ART_TEAM.md`).
* [x] Asset Specification schemas (`docs/architecture/ASSET_SPECIFICATION.md`).
* [x] 10-Step Production Workflow (`docs/workflows/AI_ASSET_WORKFLOW.md`).

### Phase 1: Security Hardening & Engine Fixes (Sprint 0 / 1 — In Progress)
* [x] **Bridge Security**: Eliminate arbitrary `eval()`; introduce typed command dispatch.
* [x] **Path Traversal Protection**: Guard file exports against directory traversal attacks.
* [x] **Godot 4 Sub-Resource Fix**: Generate valid `[sub_resource type="AtlasTexture"]` declarations with correct `region = Rect2(...)` bounds.
* [x] **Pydantic Schema Models**: Implement `ArtProfile`, `CharacterBlueprint`, `TilesetSpec`, `ItemSpec`, and `ValidationReport` in Python code.
* [x] **Clean Aseprite Layers**: Eliminate orphan `Layer 1` from generated project files.

### Phase 2: Decoupled Studio Generators (Sprint 1)
* [ ] **Character Studio**:
  * Replace hardcoded knight with blueprint-driven procedural generator.
  * Proportions: Chibi (1:2), Super-Deformed (1:1), Heroic (1:3).
  * 4-directional turnaround views (`down`, `left`, `right`, `up`).
* [ ] **Environment Studio**:
  * Implement standard **47-Blob Autotile system** compatible with Godot 4 Terrain bitmasking.
  * Procedural organic cluster placement (eliminating single-pixel random noise).
* [ ] **Color Engine**:
  * Procedural hue shifting for dynamic lights and shadows.
  * Palette-swapping matrixes for elemental/tier asset variants.

### Phase 3: Automated QA & Validation Engine (Sprint 2)
* [ ] Pre-export automated pixel analyzer:
  * Detect unauthorized colors outside ArtProfile palette.
  * Detect semi-transparent outer boundary pixels.
  * Detect baseline foot drift across animation frames.
* [ ] Structured QA reports with actionable correction suggestions.

### Phase 4: Live GUI & Engine Integration (Sprint 3)
* [ ] Non-blocking WebSocket / HTTP event bridge inside LibreSprite.
* [ ] Direct import trigger into Godot project directory with auto-generated `.import` files.
