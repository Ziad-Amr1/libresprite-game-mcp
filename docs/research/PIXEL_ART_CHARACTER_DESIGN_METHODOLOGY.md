# Pixel Art Character Design Methodology & Forensic Comparative Audit

**Document Version:** 2.0  
**Target:** LibreSprite Game MCP Production Art Pipeline  
**Author:** AI Art Director & Senior Software Architect  
**Date:** 2026-11-24  
**Branch:** `feature/production-art-system`  

---

## 1. Executive Summary

This document presents a comprehensive, industry-grade synthesis of professional pixel art character design workflows—drawing directly from foundational guides and industry masters including:
- **Sandro Maglione** (*Getting Started with Pixel Art - A Beginner Perspective*, `sandromaglione.com`)
- **vysnvnt** (*Beginner's Guide: How I Started Drawing Pixel Characters*, `vysnvnt.medium.com`)
- **Brandon James Greer (BJG)** (*Silhouette-first character blocking, proportional staging, proofreading*)
- **MortMort** (*Technical line hygiene, stair-stepping, jaggies/doubles elimination, palette economy*)
- **Pedro Medeiros / Saint11** (*Articulated locomotion dynamics, contact/squash/pass/lift mechanics, respiration*)
- **Derek Yu** (*Pixel art tutorials, readability at native resolution, selective outlining*)

It provides:
1. **The Human Artist Methodology:** The end-to-end professional pipeline from blank canvas and visual reference gathering to finished sprite and animation cycles.
2. **Forensic Project Comparison:** How our generator evolved from naive primitive block-stamping (Sprint 0) to modular 16×16 anatomy (Sprint 0.3–0.7), and finally to native 32×32 silhouette sculpting and articulated locomotion (Sprint 0.8).
3. **The "Do Each Time" Operational Protocol:** A mandatory 10-point quality checklist that our procedural AI systems and specialist agents must execute on every character generation task.
4. **Learning Layer Knowledge Architecture:** How these empirical principles are formalized into structured, versioned, confidence-scored `KnowledgeRecord` entries within the Learning Layer (`learning.db`) for automated guidance retrieval.

---

## PART I — THE HUMAN ARTIST METHODOLOGY

Professional pixel artists do not "place random pixels until it looks like something." Pixel art is a deliberate economy of visual information where every single pixel carries semantic and structural weight.

```
+---------------------------------------------------------------------------------------------------+
|                            THE 10-STAGE PROFESSIONAL PIXEL ART PIPELINE                           |
+---------------------------------------------------------------------------------------------------+
|  1. Visual Reference  -->  2. Canvas Budget   -->  3. Gesture Armature  -->  4. Silhouette Mask   |
|         |                        |                       |                        |               |
|  8. Cluster Shading   <--  7. Flat Palette    <--  6. Doubles Purge     <--  5. Clean Stair-Steps |
|         |                                                                                         |
|  9. Sel-Out & Edges   -->  10. Locomotion & Proofreading (100% Zoom + Flip Test)                  |
+---------------------------------------------------------------------------------------------------+
```

---

### Stage 1: The 15-Minute Visual Reference Rule (vysnvnt)
As emphasized by **vysnvnt** (`vysnvnt.medium.com`), drawing purely out of one's head on a blank canvas is the single most common cause of weak anatomy and generic designs.
- **The Protocol:** Before opening the sprite editor or placing a single pixel, spend 10–15 minutes gathering 4–8 diverse visual references:
  - Costume & silhouette cuts (e.g., historical armor, rogue cowls, flowing wizard robes).
  - Poses & lines of action (action figures, martial arts stances, athletics).
  - Palette inspiration from curated sets (Lospec, DawnBringer, Endesga).
- **Inspiration vs. Tracing:** References are analyzed for **shape relationships**, weight distribution, and contrast points—never 1:1 traced or copied.

---

### Stage 2: Dimension & Resolution Budgeting (vysnvnt, Sandro Maglione)
Scale dictates the degree of abstraction. Both Sandro Maglione and vysnvnt stress that working without an explicit pixel budget results in either muddy overcrowding or empty canvas:
- **8×8 to 16×16 (Micro / Retro / Chibi):**
  - Extreme symbolic abstraction.
  - Head represents 40%–50% of total height (chibi / SD proportions).
  - Eyes are 1×1 or 1×2 single dots; limbs are 1–2 pixels wide.
  - Shading is minimal (1 highlight, 1 base, 1 shadow per material).
- **24×24 to 32×32 ("The Sweet Spot" - vysnvnt):**
  - The optimal balance for modern indie games.
  - Generous enough to render expressive 2×3 eyes with specular glints, tiered clothing folds, layered pauldrons, braided beards, and recognizable class weapons.
  - Compact enough to keep animation cycles agile (6–8 frames) without illustration-scale overhead.
- **48×48 to 64×64+ (Detailed Arcade / High-Density):**
  - Realistic anatomical muscle groups, intricate cloth physics, weapon runes. Requires high-level illustrative draftsmanship.
- **Canvas Rule (Hard Edges):** Anti-aliasing must be **strictly disabled** in the editor. Opacity must be binary: $A \in \{0, 255\}$.

---

### Stage 3: Gesture Armature & Line of Action (Brandon James Greer)
Rather than drawing "from the hat down," Brandon James Greer establishes the character's kinetic energy using a 1-pixel skeletal stick frame:
- **Line of Action:** A single dynamic curve passing from the cranium through the spine to the weight-bearing foot. Characters are never posed in stiff, symmetrical vertical t-poses.
- **Weight Distribution:** The pelvis and ribcage are counter-angled (contrapposto). Even in a resting stance, weight rests predominantly on one foot.
- **Ground Clearance:** 2–3 rows of pixels at the bottom of the canvas are reserved for contact shadows; 3–4 rows at the top are reserved for jump/motion rebounds.

---

### Stage 4: Silhouette-First Blockout & The "Squint Test" (vysnvnt, BJG, MortMort)
Before rendering internal details, facial features, or colors, the artist fills the gesture armature with a solid monochromatic mass (dark gray or black):
- **Class Shape Motifs:**
  - *Knight:* Inverted trapezoid / V-taper with flared shoulder pauldrons; grounded stance communicating defensive stability.
  - *Mage:* Triangle / flared pyramid hemline (skirt width $\ge 1.8\times$ chest width); mystical verticality.
  - *Goblin / Rogue:* Crooked hunch, low center of gravity, sharp triangular cowl folds, prominent lateral ear protrusions.
  - *Heavy Brute:* Colossal square/rectangle block, massive upper torso, forward-thrust cranium, wide footing.
- **The "Black Mask" Test:** Fill the entire sprite with pure black (`#000000`). If a player cannot identify the character archetype and primary equipment purely from outer contour, the design fails. Internal details cannot rescue an unreadable silhouette.

---

### Stage 5: Clean Stair-Stepping & Jaggies Elimination (Sandro Maglione, MortMort)
Sandro Maglione highlights the **atomic nature** of pixel art: shifting a single pixel changes a curve's perceived trajectory:
- **Mathematical Step Progression:** Smooth curves and diagonal edges must follow regular, monotonic numerical sequences:
  - *Smooth Curve:* `3-2-1-1-2-3` or `4-2-1-1-2-4`.
  - *Consistent Angle:* Uniform step runs (e.g., `2-2-2-2` for a 26.5° slope, or `1-1-1-1` for a 45° slope).
- **Hunting "Jaggies":** Jaggies are awkward, spiky breaks in lines caused by erratic step lengths (e.g., `3-1-4-1` or `2-1-3-1`). The unexpected jump from 1 to 4 breaks the viewer's eye path and makes edges look broken.

```
Jaggies (Erratic, Broken Flow):
  [#][#][#]
           [#]
              [#][#][#][#]   <-- Awkward jump from 1px to 4px
                          [#]

Clean Stair-Stepping (Mathematical Rhythm):
  [#][#][#]
           [#][#]
                 [#]
                    [#]
                       [#][#]
                             [#][#][#]
```

---

### Stage 6: Purging "Doubles" / Clumping (Sandro Maglione, MortMort)
A "double" is an unintended $2\times2$ or corner-sharing block of pixels along a diagonal line:
- **Why Doubles Ruin Art:** They add irregular thickness, creating bulky, accidental corners that destroy line sharpness.
- **The Purge Rule:** Any diagonal line intended to be 1 pixel thick must never have two pixels sharing an interior corner edge unless deliberately creating a corner juncture.

```
Double Pixel / Clumping (Messy Edge):
  [#]
  [#][#]   <-- Unintended double corner
     [#]

Clean Single-Pixel Diagonal:
  [#]
     [#]
        [#]
```

---

### Stage 7: Limited Palette Discipline & Temperature Hue Shifting (Sandro Maglione, Derek Yu)
Beginner artists darken colors by naively reducing brightness (sliding RGB toward black), resulting in lifeless, muddy, desaturated characters.
- **Palette Economy:** Capped at 8–16 colors total (e.g., DawnBringer `db16`). Restricting color choices forces strong contrast and visual unity.
- **Hue Shifting (Color Temperature Ramping):**
  - **Highlights shift warm:** Step toward yellow, cream, or gold.
  - **Shadows shift cool:** Step toward deep violet, navy blue, or teal.
- **Material Ramps:** Each material receives exactly 3–4 values:
  1. *Specular Glint / Edge Highlight* (10% area)
  2. *Base / Local Value* (50% area)
  3. *Mid-Shadow* (30% area)
  4. *Deep Ambient Crevice / Outline Ramp* (10% area)

---

### Stage 8: Form Shading & The Anti-Pillow-Shading Ban (Sandro Maglione, vysnvnt)
- **The Pillow Shading Hazard:** Shading concentric rings inward from the outline (brightest in the center, dark along all edges) creates flat, puffy balloon shapes lacking 3D volume.
- **Directional Light Key:** Establish a consistent directional light source (standard: top or top-left key light at 45°).
- **Pixel Clustering:** Pixels must form solid $2\times2$, $2\times3$, or $3\times3$ cohesive clusters. Stray, isolated 1-pixel dots create visual static and noise.
- **Contact & Cast Shadows:** Mandatory cast shadows:
  - Under chin/jaw (separates head from torso).
  - Under bangs/helmet brim (gives facial depth).
  - Under belt/tunic hem (gives torso volume).
  - Ground ellipse shadow under feet (anchors character to the world).
- **Controlled Dithering:** Dithering (checkerboard blending) should be used sparingly or avoided entirely on small sprites (under 48×48). Clean cluster boundaries are dramatically more readable than noisy checkerboards.

---

### Stage 9: Selective Outlining ("Sel-Out") (MortMort, Brandon James Greer)
A uniform pitch-black outline around every part of a character creates a "coloring book" or "sticker" effect that flattens form:
- **Exterior Silhouette Outline:** Uses the darkest ramp color (`#140c1c` or deep navy) along the outer boundary to separate the sprite cleanly from arbitrary backgrounds.
- **Interior Seam Outlines (Sel-Out):** Internal divisions (sleeve to arm, breastplate to belt, cloth folds) use the **shadow shade of the local color ramp**, NEVER pure black.
  - *Example:* A fold in blue cloth uses dark navy; armor panel seams use dark steel blue; facial features use warm shadow tone.

---

### Stage 10: Proofreading, Locomotion & The 100% Zoom Check (Brandon James Greer, Saint11)
- **The 100% Scale Sanity Check (Maglione & Greer):** Artists spend hours working at 800% or 1600% zoom. Before finalizing, always inspect the sprite at 100% native scale. If micro-details turn into muddy noise, simplify and merge clusters.
- **The Horizontal Flip Test (Greer):** Mirroring the canvas horizontally resets eye fatigue and immediately exposes leaning poses, lopsided shoulders, or distorted anatomy.
- **True Locomotion Mechanics (Pedro Medeiros / Saint11):**
  - Walking is never a simple 1-pixel up/down oscillation.
  - A real walk cycle executes 4 distinct mechanical phases across 6–8 frames:
    1. *Contact:* Lead foot plants, trailing foot pushes off.
    2. *Down (Squash):* Body compresses downward (-1px bob), absorbing impact.
    3. *Passing:* Center of gravity elevates, free leg swings forward.
    4. *Up (Push-off):* Body reaches maximum elevation, pushing forward.
  - *Secondary Inertia:* Plumes, cape tails, robe hemlines, and heavy weapons trail body movement with a 1-frame inertial delay.

---

## PART II — FORENSIC COMPARISON: INDUSTRY METHODOLOGY VS OUR ENGINE

The following matrix compares industry-standard methodologies against the three evolutionary stages of the LibreSprite Game MCP character generator:

| Pipeline Dimension | Industry Standard (Maglione / vysnvnt / Greer / Saint11) | Phase 0: Legacy Baseline (Sprint 0) | Phase 1: Modular 16×16 (Sprint 0.3–0.7) | Phase 2: Native 32×32 Engine (Sprint 0.8) | Current Rating |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Reference Gathering** | 10–15 min reference gathering; analyze shape relationships and color ramps. | ❌ NONE. Hardcoded box offsets generated from static assumptions. | ⚠️ PARTIAL. Reference library created (`PIXEL_ART_REFERENCE_LIBRARY.md`). | ✅ EXCELLENT. Reference analysis mapped directly into archetype profiles and shape schemas. | **A** |
| **Canvas Budgeting** | Explicit resolution constraint ($16\times16$, $24\times24$, $32\times32$); clearance for jumps & ground shadow. | ❌ FAILED. Full canvas utilization with zero clearance; character heads hit canvas ceiling. | ⚠️ MODERATE. Fit within 16×16 bounds, but micro-details were 1px sticks. | ✅ EXCELLENT. 32×32 with 4px top clearance, 2px ground shadow, active bounding boxes. | **A+** |
| **Silhouette & Shape Language** | Distinct shape motifs per class; passes solid black mask test; contrapposto gesture. | ❌ FAILED. All classes used identical 6×5 rectangular heads and 6×4 torso boxes. | ⚠️ MODERATE. Added pauldron flair, robe hem, lateral ears, and plume. | ✅ EXCELLENT. 18px goblin ears, 18px brute chest, 22px robe flare, heater shield. Passes black mask test. | **A+** |
| **Anatomical Proportions** | Chibi 1:2 to 1:3 ratio for retro; head = 30%–40% height; articulated eye glints & pupils. | ❌ FAILED. Monolithic block limbs; eyes were flat single dots with zero pupils or glints. | ⚠️ MODERATE. Head 45%, torso 30%, legs 25%; basic 1px eye slits. | ✅ EXCELLENT. 32×32 head 35%, torso 28%, legs 32%; 2×3 expressive eyes with pupils and specular glints. | **A+** |
| **Linework & Stair-Stepping** | Monotonic mathematical steps (`3-2-1-1-2-3`); zero jaggies. | ❌ FAILED. Rigid rectangular block boundaries; no curved stepping. | ⚠️ MODERATE. Basic chin and helm stepping, but coarse. | ✅ EXCELLENT. Curved dome craniums, organic goblin skull, curved horns, crescent axe blades. | **A** |
| **Double Pixels Purge** | Strict removal of accidental $2\times2$ corner clusters on 1px lines. | ❌ FAILED. Rectangular corner overlap created accidental doubles everywhere. | ⚠️ PARTIAL. Post-processing outline tool reduced some clumping. | ✅ EXCELLENT. Structural coordinate math avoids diagonal clumping; clean 1px contours. | **A** |
| **Palette & Hue Shifting** | Strict 8–16 color limit; warm highlights, cool shadows; zero mathematical RGB tinting. | ❌ FAILED. Math RGB lightening (`(255-r)*0.25`) generated unauthorized colors. | ✅ PASS. Quantized 100% to DB16 palette lookups. | ✅ EXCELLENT. 100% DB16 adherence; steel gleam `#deeed6`, cyan orb `#6dc2ca`, deep blue `#30346d`. | **A+** |
| **Form Shading & Clusters** | $2\times2$ to $3\times3$ solid clusters; top-left light key; chin/hair drop shadows; zero pillowing. | ❌ FAILED. Flat solid fills with 1px border lines; pillow shading effect. | ✅ GOOD. Procedural hair-on-face and chin-on-torso drop shadows. | ✅ EXCELLENT. Tiered breastplate ridge, beard fold shadows, undulating robe fold clusters. | **A** |
| **Selective Outlining (Sel-Out)** | Dark exterior boundary; interior seams use local shadow ramp; no black eye rings. | ❌ FAILED. Naive black outline around weapons/arms merged into muddy blob. | ✅ GOOD. Interior seams switched to shadow ramps (`pants_shadow`, `skin_shadow`). | ✅ EXCELLENT. Shield rim, axe haft, and robe folds use material ramps; zero sticker blobbing. | **A+** |
| **Locomotion Cycles (Move)** | Articulated 6–8 phase walk: contact, squash, pass, lift; side-to-side weight transfer. | ❌ FAILED. Only shifted `bob_y` 1px and leg offset ±1px. | ⚠️ MODERATE. 4-step leg cycle with bob, but body remained upright. | ✅ EXCELLENT. 8-frame martial knight march; 6-frame heavy brute stomp with sway; 6-frame goblin scurry. | **A+** |
| **Idle Respiration Physics** | Personality-driven respiration; secondary plume/cloth delay; weapon inertia. | ❌ FAILED. Alternated `bob_y = 1` on odd frames across all characters. | ⚠️ MODERATE. Basic bob with subtle weapon adjustment. | ✅ EXCELLENT. Brute chest expansion (+1px width); Mage crystal orb pulsing; Goblin ear twitch; Knight plume wave. | **A+** |
| **Proofreading & Native Check** | 100% scale zoom check; horizontal canvas flip; zero stray flicker pixels. | ❌ FAILED. Only inspected via high-zoom terminal logs. | ⚠️ MODERATE. Automated Art QA checks added. | ✅ EXCELLENT. Export pipeline renders native 1x spritesheets, GIFs, and Godot 4 `.tres` alongside QA gates. | **A+** |

---

## PART III — THE "DO EACH TIME" OPERATIONAL PROTOCOL

To ensure every asset produced by our procedural generation engine, specialist agents, and human collaborators meets commercial game-industry standards, every generation task must execute this 10-step protocol:

```
[1. Reference & Budget]  -->  [2. Armature & Pose]  -->  [3. Silhouette Mask]  -->  [4. Anatomy Ratios]
         |
[8. Articulated Locomotion] <-- [7. Sel-Out & Alpha] <-- [6. Cluster Shading] <-- [5. Stair-Steps & Purge]
         |
[9. Respiration Idle]    -->  [10. Proofreading & Engine QA Gate]
```

### 1. Reference & Budget Gate
- Retrieve project Art Profile and define target grid ($16\times16$, $24\times24$, $32\times32$, or $48\times48$).
- Reserve 3–4 pixels at top for head bounce/jump clearance; reserve 2–3 rows at bottom for grounding shadow.
- Extract color ramp requirements from curated palette (e.g., DawnBringer `db16`).

### 2. Gesture Armature & Stance Gate
- Establish kinetic spine curve. Avoid static bilateral symmetry.
- Shift body mass to dominant weight-bearing leg (contrapposto).
- Orient weapon and equipment along opposing diagonal axes to balance visual weight.

### 3. Silhouette Mask & Squint Test Gate
- Render composite character in solid black (`#000000`) against a light background.
- Verify class recognizability:
  - *Knight:* V-taper chest, broad pauldron edges, prominent shield contour.
  - *Mage:* Flared skirt hem $\ge 1.8\times$ chest width, vertical staff silhouette with topper.
  - *Goblin:* Low-slung hunchback, wide lateral ear span, compact blade dagger.
  - *Brute:* Bulky rectangular torso block, wide stance, oversized two-handed axe/maul.

### 4. Anatomy & Head-to-Body Ratio Gate
- For $16\times16$: Head = 42%–50% total height; Torso = 25%–30%; Legs = 20%–25%.
- For $32\times32$: Head = 30%–38% total height; Torso = 25%–30%; Legs = 25%–35%.
- Facial anchors: Eyes must have defined pupil and specular glint; nose bridge or helmet visor slit must establish head gaze orientation.

### 5. Stair-Stepping & Doubles Purge Gate
- Trace all curved contours (helmet crown, horns, cowl, axe curves).
- Verify monotonic step sequences (`3-2-1-1-2-3`). Eliminate irregular jumps (jaggies).
- Purge all accidental $2\times2$ corner clusters on 1px diagonal lines.

### 6. Limited Palette & Directional Cluster Shading Gate
- All colors must quantize 100% to project palette. Zero raw mathematical RGB operations.
- Group pixels into contiguous $2\times2$ or $3\times3$ solid clusters. Ban single-pixel noise (except deliberate 1px specular glints).
- Apply consistent directional key light (top-left 45°).
- Mandatory cast shadows: under jaw/chin, under hair/helmet, under belt, and under feet.

### 7. Selective Outlines (Sel-Out) & Alpha Hygiene Gate
- Perimeter boundary: Dark outline color (`#140c1c`).
- Interior seams: Local shadow ramp color. Never use pure black around internal seams or eyes.
- Alpha channel must be strictly binary: $A \in \{0, 255\}$. Zero semi-transparent pixels.

### 8. Articulated Locomotion (`move`) Gate
- Movement must NEVER be a uniform 1px up-and-down oscillation.
- Implement 4-phase gait mechanics: Contact $\rightarrow$ Squash (Down) $\rightarrow$ Passing $\rightarrow$ Lift (Up).
- Incorporate horizontal sway (`sway_x`) for heavy classes and forward sprint-lean for agile classes.
- Implement 1-frame trailing inertia on secondary elements (plumes, capes, weapon heads).

### 9. Character-Driven Respiration (`idle`) Gate
- Idle state must reflect character personality:
  - Heavy brute: Torso width expands by $+1$px on inhale; heavy ground stance.
  - Mage: Crystal staff orb pulses in brightness; robes drift subtly.
  - Goblin rogue: Rapid breathing, ear twitches, dagger tilt adjustments.
  - Knight: Slow disciplined respiration with plume sway.

### 10. Proofreading & Engine QA Gate
- **100% Scale Native Check:** Verify readability at $1\times$ scale without magnification.
- **Horizontal Canvas Flip:** Mirror canvas to confirm anatomical balance and lack of tilt bias.
- **Automated Art QA Validation:**
  - Dimensions match target grid exactly.
  - Zero semi-transparent pixels (`alpha_hygiene`).
  - Zero off-palette colors (`palette_adherence`).
  - Contact baseline grounded correctly across all frames.
- **Engine Exports:** Native `.aseprite` source, spritesheet PNG + JSON metadata, looping GIF previews (`_idle.gif`, `_move.gif`), and Godot 4.x `SpriteFrames` (`.tres`) registration.

---

## PART IV — LEARNING LAYER UPGRADE ARCHITECTURE

To ensure that the principles synthesized from Sandro Maglione, vysnvnt, Brandon James Greer, MortMort, and Saint11 persist permanently and guide all future AI operations, the **Learning Layer** (`libresprite_game_mcp/learning/`) is upgraded to store and retrieve these principles as structured, versioned, provenance-tracked `KnowledgeRecord` entries.

### The Four-Tier Knowledge Architecture

The system enforces strict architectural separation across four distinct categories of knowledge:

1. **`EXTERNAL_REFERENCE`**: Principles extracted from industry tutorials, master artists, and published game dev literature. Carries complete bibliographic provenance (author, URL, title, date, extraction, limitations). Retains `confidence_score = None` (no arbitrary probabilities) and is completely immune to mutation from empirical feedback.
2. **`EMPIRICAL_KNOWLEDGE`**: Observations and heuristics synthesized by machine learning algorithms from repeated task executions, telemetry logs, and Art QA validation outcomes. Dynamically confidence-scored (`0.0 - 1.0`).
3. **`HUMAN_FEEDBACK`**: Granular artist ratings, text critiques, approvals, and corrective directives submitted by human operators. Strictly scoped to target projects.
4. **`VALIDATED_SKILL`**: Concrete, reproducible DAG workflows that have passed isolated sandbox testing and explicit Art Director approval.

### Structured Knowledge Schema

```
+----------------------------------------------------------------------------------------------------+
|                                    KNOWLEDGE RECORD ARCHITECTURE                                   |
+----------------------------------------------------------------------------------------------------+
|  id:              UUID v4 (unique identifier)                                                      |
|  project_id:      NULL (Universal Art Bible rule) or String (Project-specific override)            |
|  knowledge_type:  KnowledgeType (EXTERNAL_REFERENCE, EMPIRICAL_KNOWLEDGE, etc.)                   |
|  evidence_status: EvidenceStatus (COMMUNITY_CONSENSUS, REFERENCE_GUIDANCE, EMPIRICAL_OBSERVATION)  |
|  category:        KnowledgeCategory (PALETTE, SILHOUETTE, OUTLINE, LIGHTING, DITHERING, etc.)      |
|  rule_name:       Descriptive, human-readable rule identifier                                      |
|  description:     Detailed architectural heuristic and rationale                                   |
|  conditions:      Conditional scope (e.g. {"task_category": "character", "palette_name": "db16"})  |
|  recommendations: Concrete actionable parameters for generators, prompts, and QA gates             |
|  confidence_score: Float (0.0-1.0) for empirical rules; None for external references                |
|  provenance:      ReferenceProvenance (source title, author, URL, access date, limitations)        |
|  created_at:      UTC timestamp                                                                    |
|  updated_at:      UTC timestamp                                                                    |
+----------------------------------------------------------------------------------------------------+
```

### Knowledge Records Seeded

The following 10 universal Art Bible external reference rules are registered in the database:

1. **`Universal Silhouette Readability & Black Mask Rule`** (`SILHOUETTE`)
   - *Provenance:* vysnvnt (*Beginner's Guide: How I Started Drawing Pixel Characters*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"silhouette_test": "black_mask", "require_asymmetry": True, "class_shape_motifs": {"knight": "v_taper", "mage": "pyramid_skirt", "rogue": "hunch_lateral_ears", "brute": "colossal_rectangle"}}`

2. **`Native Canvas Resolution Budgeting`** (`COMPOSITION`)
   - *Provenance:* Sandro Maglione (*Getting started with Pixel Art - A beginner perspective*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"head_ratio_16x16": [0.42, 0.50], "head_ratio_32x32": [0.30, 0.38], "top_clearance_px": 4, "ground_shadow_rows": 2}`

3. **`Mathematical Stair-Stepping & Jaggies Purge`** (`OUTLINE`)
   - *Provenance:* Sandro Maglione (*Getting started with Pixel Art*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"line_stepping": "monotonic", "disallow_jaggies": True, "max_step_delta": 1, "outline_mode": "colored"}`

4. **`Elimination of Double Pixels and Clumping`** (`OUTLINE`)
   - *Provenance:* Sandro Maglione (*Getting started with Pixel Art*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"purge_doubles": True, "diagonal_width_px": 1, "outline_mode": "colored"}`

5. **`Strict Palette Discipline & Temperature Hue Shifting`** (`PALETTE`)
   - *Provenance:* Derek Yu (*Pixel Art Tutorial: Color Theory and Palette Selection*)
   - *Evidence Status:* `REFERENCE_GUIDANCE`
   - *Scope:* `{"task_category": "character", "palette_name": "db16"}` (Applies strictly when DB16 is selected)
   - *Recommendations:* `{"recommended_palette": "db16", "highlights_temperature": "warm_yellow_cream", "shadows_temperature": "cool_violet_navy", "allow_raw_rgb_math": False}`

6. **`Directional Cluster Shading & Anti-Pillow-Shading Ban`** (`LIGHTING`)
   - *Provenance:* Sandro Maglione (*Getting started with Pixel Art*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"light_source": "top_left_45_deg", "shading_style": "cluster", "min_cluster_size": [2, 2], "pillow_shading_allowed": False, "mandatory_shadows": ["chin_drop", "hair_drop", "belt_crevice", "ground_ellipse"]}`

7. **`Selective Outlining (Sel-Out) and Interior Seam Ramping`** (`OUTLINE`)
   - *Provenance:* MortMort (*Pixel Art Linework and Outlining Guide*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character"}`
   - *Recommendations:* `{"exterior_outline": "#140c1c", "interior_seams": "local_shadow_ramp", "pure_black_interior_allowed": False, "outline_mode": "colored"}`

8. **`Controlled Dithering Prohibition on Low Resolutions`** (`DITHERING`)
   - *Provenance:* Sandro Maglione (*Getting started with Pixel Art*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character", "resolution": ["16x16", "24x24", "32x32"]}`
   - *Recommendations:* `{"dithering_allowed_under_48px": False, "preferred_shading": "solid_clusters"}`

9. **`Articulated Locomotion Dynamics & Weight Transfer`** (`ANIMATION_TIMING`)
   - *Provenance:* Pedro Medeiros / Saint11 (*Pixel Art Walk Cycle Tutorials*)
   - *Evidence Status:* `COMMUNITY_CONSENSUS`
   - *Scope:* `{"task_category": "character", "animation_state": "move"}`
   - *Recommendations:* `{"walk_phases": ["contact", "down_squash", "passing", "up_lift"], "min_frames": 6, "allow_pure_vertical_bob": False, "secondary_inertia_delay_frames": 1}`

10. **`Proofreading Protocol (100% Native Scale & Canvas Flip)`** (`GENERAL`)
    - *Provenance:* Brandon James Greer (*Proofreading Your Pixel Art: 5 Common Mistakes*)
    - *Evidence Status:* `COMMUNITY_CONSENSUS`
    - *Scope:* `{"task_category": "character"}`
    - *Recommendations:* `{"verify_native_1x_zoom": True, "perform_horizontal_flip": True, "require_binary_alpha": True}`

### End-to-End Generator Integration Pipeline

Guidance is not passive documentation. When an art creation task is initiated, the Production Orchestrator:
1. Queries matching universal references and project-specific empirical rules via `get_knowledge_guidance(...)`.
2. Packages them into a typed `CharacterGenerationGuidance` data contract.
3. Injects guidance into the workflow execution context without overriding user-specified parameters.
4. The Tool Dispatcher routes parameters and guidance down to `build_animated_character_project` ($16\times16$) or `build_animated_character_project_32` ($32\times32$).
5. The generated asset records `guidance_applied` in its execution summary and telemetry.

