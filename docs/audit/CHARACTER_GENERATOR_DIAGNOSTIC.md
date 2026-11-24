# Character Generator Quality Diagnostic & Architectural Redesign Plan

**Document Version:** 1.0  
**Status:** Audit Complete — Architecture Redesign Approved  
**Target:** `libresprite_game_mcp/generators/character_generator.py`  
**Date:** 2026-11-24  

---

## 1. Executive Summary

A comprehensive forensic audit was conducted on the existing character assets (`warrior_hero`, `pixil_knight`, `goblin_rogue`, `arcane_mage`) and the procedural generator codebase (`character_generator.py`).

The visual evaluation confirmed that while the assets technically satisfy automated validation checks (resolution, non-empty layers, valid Aseprite chunk headers, and Godot 4 SpriteFrames resources), their visual quality is unacceptable for production games. The characters resemble primitive rectangular "color-swapped wooden mannequins" lacking readable silhouettes, volume, selective outlining, and archetype identity.

This audit details the root causes in code and outlines the architectural redesign.

---

## 2. Forensic Visual & Structural Analysis

### 2.1 Side-by-Side ASCII Pixel Footprint
Direct inspection of the 16x16 frame previews reveals near-identical rectangular topology across ostensibly distinct archetypes:

```
=== warrior_hero (Knight) ===       === arcane_mage (Mage) ===
                                    
     ++++++ (6px hair bar)               ###### (6px hood)
     ++++++                              #......#
     #....# (6x3 face box)               #......#
     ##..## (eyes @ fixed pos)           ##....###
     #....#                              ##....##.#
     ++++++                              #++++++#.#
    ++....+... (6x4 torso)              #+++++++...# (6x4 torso)
    ++....++.                           #++++++++.#
    ++++++++.                           #++++++++.#
     ##  ## (2px leg sticks)             ######### (2px leg sticks)
     ##  ##                              ########
     ##  ##                              ########
    ######## (shadow)                   ########## (shadow)
    ########                            ##########
```

### 2.2 Critical Visual Defects Identified

1. **Monolithic Geometric Primitives (Rectangular Mannequins):**
   - The head is strictly drawn as a solid 6x5 rectangle `mid_x - 3` to `mid_x + 3`.
   - The torso is drawn as an identical 6x4 rectangle.
   - The legs are two parallel 2x3 vertical columns separated by a 2px gap.
   - Every character shares this exact bounding box regardless of role, weight, or clothing.

2. **Total Absence of Archetype Silhouette Anchors:**
   - **Knight/Warrior:** Lacks helmet plumes, visors, or pauldron shoulder overhangs. It has the exact same shoulder width (6px) as an unarmored civilian.
   - **Arcane Mage:** Has no flared robe hem, no pointed wizard cowl or drooping hood, and holds a sword-shaped 1px line instead of a mystical staff.
   - **Goblin Rogue:** Has human proportions with green skin. Lacks pointed lateral ears, hunched asymmetric posture, or jagged daggers.
   - **Brute/Dwarf:** Cannot be represented because chest width and leg height are strictly hardcoded.

3. **Destructive Post-Process Outlining (Muddy Blobbing):**
   - In `generate_character_frame`, outlines are drawn naively as black/shadow borders around the primitive rectangles.
   - When outline pixels are slapped around the 1px sword and 1px arms, they merge into the torso and facial area, creating an undifferentiated 1-pixel muddy border.

4. **Primitive Facial Geometry:**
   - Eyes are fixed at `(mid_x - 2, head_y + 2)` and `(mid_x + 1, head_y + 2)`.
   - There is no brow line, no forehead shadow, no cheek highlight, and no chin contour.

5. **Lack of Drop Shadows and Material Depth:**
   - Hair sits as a flat horizontal band atop the head without casting a drop shadow onto the forehead.
   - The head connects directly to the chest without a chin shadow or neck definition.

---

## 3. Code-Level Root Cause Analysis in `character_generator.py`

| Code Location | Defect Mechanism | Impact |
| :--- | :--- | :--- |
| `lines 175-181` | Proportions fixed at `head_y = (3+bob)*scale`, `torso_h = 4*scale`, `legs_h = 3*scale`. | Prevents robed characters, dwarfs, or hunched monsters. |
| `lines 183-196` | Torso and legs drawn as hardcoded `mid_x - 3, 6*scale` and `mid_x - 3, 2*scale`. | Eliminates pauldron shoulders, robe flares, and leg tapering. |
| `lines 209-218` | Head drawn as `mid_x - 3, head_y, 6*scale, 5*scale`; hair as `6*scale, 2*scale`. | Skull has no cranial curve; hair does not overhang forehead or sides. |
| `lines 235-240` | Weapon drawn as a single vertical line `wx, wy-3 to wx, wy+2` and 3px hilt. | Cannot render curved daggers, staves with crystals, hammers, or shields. |
| `lines 86-102` | `blueprint_to_style` maps flat colors but ignores `blueprint.proportion` or archetype metadata. | Archetype metadata is discarded; generator falls back to the single human template. |

---

## 4. Architectural Redesign Specification

To resolve these defects without breaking MCP schemas or backward compatibility, the generator will be redesigned into a modular, multi-archetype procedural system:

### 4.1 Archetype Anatomy Modules
Introduce dedicated procedural rendering routines selected by archetype metadata (`blueprint.archetype`, or derived from `blueprint.character_id` / `name`):
1. **`Knight / Warrior` Archetype:**
   - **Headgear:** Armored bascinet / great helm with metallic brow highlight, visor slit (`#140c1c`), and optional plume.
   - **Torso & Shoulders:** Pauldron shoulder pads extending 1px laterally (`mid_x - 4` to `mid_x + 3`), giving a heroic V-taper / broad silhouette.
   - **Torso Shading:** Breastplate central highlight cluster and lateral plate shadows.
   - **Weapon:** Broadsword with defined crossguard and pommel, or kite shield.
2. **`Mage / Spellcaster` Archetype:**
   - **Headgear:** Pointed wizard cowl or deep drooping hood with 1px shadow cast over upper face.
   - **Torso / Robe:** Flared wizard robe that tapers outward from 6px at the chest to 8-10px at the hemline, eliminating separate leg columns.
   - **Weapon:** Mystic staff with wooden shaft and glowing elemental orb/crystal cluster (with highlight and glow aura).
3. **`Goblin / Creature` Archetype:**
   - **Anatomy:** Hunched posture, head shifted forward/lower.
   - **Ears:** Pointed goblin ears extending 2-3px diagonally from the lateral skull perimeter (`mid_x - 5` and `mid_x + 4`).
   - **Facial Features:** Lower-set glowing/beady eyes, sharp jawline.
   - **Weapon:** Jagged curved rogue dagger held in reverse or low grip.
4. **`Brute / Heavy / Dwarf` Archetype:**
   - **Anatomy:** Broad 8-10px chest, low center of gravity, stubby 2px legs.
   - **Facial Hair / Features:** Massive beard or heavy brow extending beyond face perimeter.
   - **Weapon:** Dual-edged battleaxe or war hammer.

### 4.2 Selective Outlining & Color Ramping Engine
- **Exterior Contour:** Applied strictly around the composite exterior silhouette perimeter using the designated outline color.
- **Interior Shading Hierarchy:**
  - Hair / helmet casts a 1px shadow across face row 0.
  - Chin / jawline casts a 1px shadow across chest row 0.
  - Belt / waistline provides high-contrast 1px separation between shirt and pants/robe.
  - Specular highlight cluster placed on the top-left shoulder/helmet.

### 4.3 Full Backward Compatibility
- If legacy arguments (`name`, `shirt_color`, etc.) or generic `CharacterBlueprint` with default parameters are passed, the generator maps to `human_warrior` or the closest archetype while benefiting from the enhanced anatomical volume and selective shading.
- All layer names (`Shadow`, `Body`, `Clothes`, `Gear`) and animation tags (`idle`, `walk`, `attack`, `hurt`) are preserved verbatim.
