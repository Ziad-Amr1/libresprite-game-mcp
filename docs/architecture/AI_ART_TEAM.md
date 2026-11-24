# AI Art Team Architecture & Contracts

**Centralized Orchestrator & Specialist Workflows for Pixel Art Production**  
**Version:** 1.0  

---

## 1. Architectural Philosophy

Rather than spawning independent, uncoordinated conversational LLM agents that lead to token bloat, conflicting art decisions, and asset file race conditions, the system utilizes a **Centralized Orchestrator with Modular Specialist Roles**.

* **Single Source of Truth**: The **Art Profile** and **Art Director Decisions** govern all operations.
* **Deterministic Contracts**: Every specialist takes typed inputs and produces verified outputs.
* **Asset Isolation**: Specialists work on staged memory buffers or dedicated draft workspaces; an asset is never written to project runtime directories until passing Art QA validation.

```
                    ┌───────────────────────────┐
                    │       User / Game Brief   │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │       Art Director        │
                    │   (Owns Art Profile & QA) │
                    └──────┬─────────────┬──────┘
                           │             │
        ┌──────────────────┴──┐       ┌──┴──────────────────┐
        │ Character & Items   │       │ Environment & World │
        ▼                     ▼       ▼                     ▼
┌───────────────┐     ┌─────────────┐┌─────────────────┐ ┌───────────────┐
│  Character    │     │ Game Asset  ││   Environment   │ │   Technical   │
│   Designer    │     │  Designer   ││     Artist      │ │    Artist     │
└───────┬───────┘     └──────┬──────┘└────────┬────────┘ └───────┬───────┘
        │                    │                │                  │
        └──────────────┬─────┴────────────────┴──────────────────┘
                       ▼
        ┌───────────────────────────┐
        │       Pixel Artist        │
        │ (Clusters, Ramps, Edges)  │
        └──────────────┬────────────┘
                       │
                       ▼
        ┌───────────────────────────┐
        │         Animator          │
        │ (Key Poses, Cycles, Tags) │
        └──────────────┬────────────┘
                       │
                       ▼
        ┌───────────────────────────┐
        │    Art QA Specialist      │
        │ (Palette, Scale, Seams)   │
        └──────────────┬────────────┘
                       │
          [Approved]   ▼   [Rejected -> Revision Loop]
        ┌───────────────────────────┐
        │ Godot/Pipeline Engineer   │
        │ (Atlas, Tres, Metadata)   │
        └───────────────────────────┘
```

---

## 2. Specialist Roles & Input/Output Contracts

### 1. Art Director
* **Role**: Owns game visual identity, palette cohesion, resolution rules, and final sign-off.
* **Inputs**: User prompt, game concept, target platform, visual references.
* **Outputs**: `ArtProfile` (dimensions, palette, lighting direction, outline rules, mood).
* **Authority**: Rejects any asset violating the Art Bible or Art Profile.

### 2. Character Designer
* **Role**: Defines silhouette, proportions, anatomy, costume layers, and color identity.
* **Inputs**: Character concept brief, `ArtProfile`.
* **Outputs**: `CharacterBlueprint` (proportions, color mapping for skin/hair/clothes/gear, signature silhouette landmarks).

### 3. Pixel Artist
* **Role**: Translates concepts into native-resolution pixel matrices. Enforces clean clusters, eliminates jaggies, and constructs hue-shifted color ramps.
* **Inputs**: `CharacterBlueprint` or `ItemSpec` or `TileSpec`, `ArtProfile`.
* **Outputs**: Layered `PixelCanvas` buffers (`Shadow`, `Body`, `Costume`, `Gear`) conforming to palette constraints.

### 4. Animator
* **Role**: Plans key poses, timing, frame durations, and motion curves.
* **Inputs**: Still base sprite from Pixel Artist, animation request (e.g. `walk`, `attack`, `jump`), `ArtProfile`.
* **Outputs**: Multi-frame sequence with loop settings, frame duration in milliseconds, and tag definitions.

### 5. Environment Artist
* **Role**: Designs modular terrain, autotile bitmasks, seamless backgrounds, and scenery props.
* **Inputs**: `TilesetSpec` (tile size, terrain types, e.g., grass/dirt/stone), `ArtProfile`.
* **Outputs**: Autotile composite sheet, tile bitmask definitions, collision maps, and seam validation reports.

### 6. Game Asset Designer
* **Role**: Designs items, equipment, weapons, UI icons, and interactive pickups.
* **Inputs**: `ItemSpec` (category, size, material, rarity tier), `ArtProfile`.
* **Outputs**: Layered icon or animated prop sprite with specular highlights and outline contrast.

### 7. Technical Artist
* **Role**: Manages layer naming conventions, canvas bounds, pivot point anchoring, and `.aseprite` file structure.
* **Inputs**: Multi-frame buffers from Animator or Environment Artist.
* **Outputs**: Validated `AsepriteProject` with correct metadata, named layers, tags, and zero orphan/empty layers.

### 8. Art QA Specialist
* **Role**: Automated and subjective quality control. Enforces cluster rules, palette compliance, and outline continuity.
* **Inputs**: Finished asset candidate before export.
* **Outputs**: `ValidationReport` (Status: PASS / FAIL, severity list, specific pixel coordinates of defects, required corrections).

### 9. Godot Integration Specialist
* **Role**: Compiles texture atlases, configures padding, and outputs Godot 4.x `SpriteFrames` (.tres) and `TileSet` resources.
* **Inputs**: Approved `AsepriteProject` + `ValidationReport`.
* **Outputs**: Engine-ready `.tres` resources, texture atlas PNGs, and JSON metadata.

---

## 3. Production Workflows & State Machine

```
[DRAFT REQUEST]
      │
      ▼
1. SPECIFY ───> Art Director & Designer create/confirm ArtProfile & Asset Blueprint.
      │
      ▼
2. DRAW ──────> Pixel Artist generates native-resolution layered raster buffers.
      │
      ▼
3. ANIMATE ───> Animator generates frame sequences and timing tags.
      │
      ▼
4. ASSEMBLE ──> Technical Artist packages into clean AsepriteProject.
      │
      ▼
5. QA AUDIT ──> Art QA executes automated checks:
      │         - Palette adherence (no orphan colors)
      │         - No translucent border pixels
      │         - Pivot & dimension consistency
      │         - Seam continuity (for tiles)
      │
      ├───[Defects Found]───> Send issue report back to Pixel Artist / Animator (Max 3 cycles)
      │
      └───[Passed QA]
                │
                ▼
6. EXPORT ────> Godot Specialist compiles AtlasTexture, SpriteFrames, and JSON metadata.
                │
                ▼
7. SIGN-OFF ──> Asset delivered to project `game_assets/` directory.
```

---

## 4. Concurrency & Race-Condition Safeguards

1. **Staged Generation**: Generators write strictly to a temporary scratch directory (`/tmp/staged_<uuid>`) during processing.
2. **File Locking**: No file in the destination project directory is touched until the final atomic move after full QA validation.
3. **No Overwrites Without User Flag**: Existing files prompt human confirmation or require an explicit `overwrite=True` parameter.
