# Pixel Art Character Design Guide & Learning Layer Art Bible

**Document Version:** 1.0  
**Target:** LibreSprite Game MCP Learning Layer & Procedural Generators  
**Author:** AI Art Director & Senior Software Architect  
**Date:** 2026-11-24  
**Branch:** `feature/production-art-system`  

---

## 1. Overview & Purpose

This guide formalizes the pixel art character design principles synthesized from online authorities and industry practitioners—notably **Sandro Maglione** (*Getting Started with Pixel Art*), **vysnvnt** (*Beginner's Guide: How I Started Drawing Pixel Characters*), **Brandon James Greer**, **MortMort**, and **Pedro Medeiros (Saint11)**—into an actionable, machine-readable Art Bible.

Every rule described in this document corresponds directly to a persistent, confidence-scored `KnowledgeRecord` in the LibreSprite Game MCP **Learning Layer** (`data/learning/learning.db`).

---

## 2. Core Methodological Pillars

### Pillar 1: Atomic Thinking & The Puzzle Mindset (Sandro Maglione)
Pixel art is not low-resolution painting. It is an economy of abstraction:
- Moving a pixel by just one coordinate point alters character expression, pose, or silhouette balance.
- Every pixel must be placed with high intentionality.
- Abstraction replaces micro-details: suggest eyes, belt buckles, and armor clasps with 1–2 pixel clusters rather than attempting high-resolution rendering.

### Pillar 2: The 15-Minute Visual Reference Rule (vysnvnt)
- Never begin generating or drawing characters from a blank canvas in isolation.
- Gather 4–8 diverse visual references covering posture, clothing folds, armor plating, and color schemes.
- Deconstruct references into geometric masses (squares, triangles, cylinders) before defining silhouettes.

### Pillar 3: Canvas Budgeting & Anti-Aliasing (vysnvnt)
- Choose target canvas deliberately:
  - **16×16:** Symbolic retro chibi; head = 40%–50% of total height; single-pixel eye dots.
  - **32×32 (The Sweet Spot):** Expressive anatomy; head = 30%–38% of height; 2×3 eyes with specular highlights; layered cloth folds.
- Turn OFF all anti-aliasing / brush feathering: every pixel must have binary opacity ($A \in \{0, 255\}$).

### Pillar 4: Silhouette-First & The Black Mask Test (vysnvnt, Greer, MortMort)
- Form always precedes detail.
- Render the character as a solid monochromatic black silhouette.
- If the archetype, stance, and primary weapon are unreadable purely from contour, redesign the silhouette before adding internal pixels.
- Maintain strong class shape motifs:
  - *Knight:* Flared V-taper pauldrons and grounded stance.
  - *Mage:* Flared triangular skirt hemline ($\ge 1.8\times$ chest width) and mystical staff.
  - *Goblin:* Crooked spine hunch, lateral ear protrusions, compact daggers.
  - *Brute:* Colossal rectangular torso block, wide heavy footing, massive axe.

### Pillar 5: Clean Linework (Jaggies & Doubles Elimination) (Sandro Maglione, MortMort)
- Smooth curves require mathematical step progressions (`3-2-1-1-2-3`).
- **Jaggies Ban:** Eliminate erratic step length jumps (e.g., `3-1-4-1`) that break line rhythm.
- **Doubles Purge:** Purge accidental $2\times2$ corner clusters on single-pixel diagonal lines.

### Pillar 6: Strict Palette Discipline & Hue Shifting (Sandro Maglione, Derek Yu)
- Cap total sprite palette at 8–16 colors (e.g., DawnBringer `db16`).
- **Zero raw mathematical color lightening** (`(255-r)*0.25`).
- **Hue Shifting:** Highlights shift warm (yellow, gold, cream); shadows shift cool (violet, navy, teal).

### Pillar 7: Directional Cluster Shading (Anti-Pillowing) (Sandro Maglione, vysnvnt)
- Ban concentric "pillow shading" inward from borders.
- Anchor all lighting to a single top-left 45° directional light source.
- Group shades into solid $2\times2$ or $2\times3$ clusters.
- Mandatory cast shadows under jaw, bangs, belt, and ground contact plane.

### Pillar 8: Selective Outlining ("Sel-Out") (MortMort, Brandon James Greer)
- Outer boundary uses deep dark hue (`#140c1c`).
- Interior seams use the local material's shadow ramp, never pure black.
- Avoid black rings around eyes and weapon hafts ("sticker blobbing").

### Pillar 9: Articulated Locomotion & Personality Respiration (Saint11)
- Locomotion walk cycles must implement true 4-phase gait mechanics: Contact $\rightarrow$ Squash (Down) $\rightarrow$ Passing $\rightarrow$ Lift (Up).
- Idle states must express personality: heavy chest expansion for brutes, orb pulsing for mages, ear twitches for rogues.

### Pillar 10: Proofreading (100% Zoom & Canvas Flip) (Brandon James Greer)
- Always verify the finished sprite at 100% native resolution without magnification.
- Horizontally flip the canvas to break visual fatigue and expose anatomical asymmetry defects.

---

## 3. Four-Tier Knowledge Architecture & Reference Registry

The Learning Layer strictly separates four tiers of knowledge to prevent literature citations from masquerading as empirical data:

1. `EXTERNAL_REFERENCE`: Synthesized principles from verified tutorials, publications, and master artists. Retains complete bibliographic provenance. Unscored by pseudo-probabilities (`confidence_score: None`). Immune to mutation from empirical feedback.
2. `EMPIRICAL_KNOWLEDGE`: Machine-learned patterns synthesized from repeated generation runs, QA validator reports, and execution telemetry. Continuously confidence-scored (`0.0 - 1.0`).
3. `HUMAN_FEEDBACK`: Direct user reviews, approvals, ratings, and explicit design preferences tied to specific experience runs. Strictly isolated to the target project.
4. `VALIDATED_SKILL`: Reusable, deterministic DAG workflows that have passed isolated sandbox evaluation and received explicit Art Director approval.

### Registered External Reference Rules

The 10 rules formalized in this guide are registered as universal external references (`project_id = None`) in the LibreSprite Game MCP Learning Layer:

| Category | Rule Name | Evidence Status | Provenance Author & Source | Conditional Scope | Key Recommendations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SILHOUETTE` | Universal Silhouette Readability & Black Mask Rule | `COMMUNITY_CONSENSUS` | vysnvnt (*Beginner's Guide: How I Started Drawing Pixel Characters*) | `task_category: character` | Black mask test, class shape motifs, contrapposto |
| `COMPOSITION` | Native Canvas Resolution Budgeting | `COMMUNITY_CONSENSUS` | Sandro Maglione (*Getting started with Pixel Art*) | `task_category: character` | 4px top clearance, 2px ground shadow, chibi head ratios |
| `OUTLINE` | Mathematical Stair-Stepping & Jaggies Purge | `COMMUNITY_CONSENSUS` | Sandro Maglione (*Getting started with Pixel Art*) | `task_category: character` | Monotonic step progressions, ban erratic jumps |
| `OUTLINE` | Elimination of Double Pixels and Clumping | `COMMUNITY_CONSENSUS` | Sandro Maglione (*Getting started with Pixel Art*) | `task_category: character` | Purge $2\times2$ corner clusters on 1px diagonals |
| `PALETTE` | Strict Palette Discipline & Temperature Hue Shifting | `REFERENCE_GUIDANCE` | Derek Yu (*Pixel Art Tutorial: Color Theory*) | `task_category: character`, `palette_name: db16` | DB16 palette, warm highlights, cool shadows, zero raw RGB math |
| `LIGHTING` | Directional Cluster Shading & Anti-Pillow-Shading Ban | `COMMUNITY_CONSENSUS` | Sandro Maglione (*Getting started with Pixel Art*) | `task_category: character` | Top-left 45° light, cluster $\ge 2\times2$, drop shadows |
| `OUTLINE` | Selective Outlining (Sel-Out) and Interior Seam Ramping | `COMMUNITY_CONSENSUS` | MortMort (*Pixel Art Linework and Outlining Guide*) | `task_category: character` | Dark perimeter, material shadow ramp for interior seams |
| `DITHERING` | Controlled Dithering Prohibition on Low Resolutions | `COMMUNITY_CONSENSUS` | Sandro Maglione (*Getting started with Pixel Art*) | `task_category: character`, `resolution: <=32x32` | No noisy dithering under 48×48; solid clusters preferred |
| `ANIMATION_TIMING` | Articulated Locomotion Dynamics & Weight Transfer | `COMMUNITY_CONSENSUS` | Pedro Medeiros / Saint11 (*Pixel Art Walk Cycle Tutorials*) | `task_category: character`, `animation_state: move` | 4-phase gait cycle, $\ge 6$ frames, secondary inertia lag |
| `GENERAL` | Proofreading Protocol (100% Native Scale & Canvas Flip) | `COMMUNITY_CONSENSUS` | Brandon James Greer (*Proofreading Your Pixel Art*) | `task_category: character` | 100% scale verification, horizontal flip, binary alpha |

---

## 4. Programmatic Retrieval & End-to-End Generator Integration

Specialist agents and procedural generators query the Learning Layer via the Production Orchestrator, which constructs a typed `CharacterGenerationGuidance` package and forwards it down the complete execution pipeline:

```
[MCP Request / Tool API]
         │
         ▼
[ProductionOrchestrator] ──(Retrieves applicable rules & packages CharacterGenerationGuidance)──┐
         │                                                                                      │
         ▼                                                                                      │
[Deterministic DAG WorkflowEngine] ──(Binds user parameters & guidance into step inputs)───────┤
         │                                                                                      │
         ▼                                                                                      ▼
[ProductionToolDispatcher] ─────────────────────────────────────────────────────────────► [Character Generator (16x16 / 32x32)]
         │                                                                                      │
         ▼                                                                                      ▼
[AssetValidator QA Gate] ◄─────────────────────────────────────────────────────────────── [Aseprite Project & Metadata]
         │
         ▼
[Engine Exporters (Godot 4.x / Spritesheet / GIF)]
```

### Typed Guidance Usage Example

```python
from libresprite_game_mcp.core.orchestrator import ProductionOrchestrator

orchestrator = ProductionOrchestrator()

# Generate character directly with end-to-end guidance integration
output = orchestrator.generate_character(
    character_id="grand_paladin",
    name="Grand Paladin",
    size=(32, 32),
    archetype="knight",
    palette_name="db16",
    art_profile="DefaultGame",
)

# Generator output captures the exact guidance applied:
# output["guidance_applied"] --> List of applied rule names
# output["width"]            --> 32
# output["height"]           --> 32
# output["archetype"]        --> "knight"
# output["project_path"]     --> "game_assets/grand_paladin.aseprite"
# output["experience_id"]    --> "exp_guidance_run_..."
```
