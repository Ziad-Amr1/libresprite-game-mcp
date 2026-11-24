# Character Generator — Distinct Animation System Evaluation

**Document Version:** 1.0  
**Animation States:** `idle` and `move`  
**Canvas Resolution:** Native 32×32  
**Target Engine:** Godot 4.x / Aseprite  
**Branch:** `feature/production-art-system`  
**Date:** 2026-11-24  

---

## 1. Executive Summary

This report documents the design, implementation, and motion verification of the new **distinct animation system** across the four 32×32 character archetypes.

Rather than relying on generic vertical bobbing or superficial pixel flickering, each character features independent motion profiles engineered to convey personality, weight, equipment mechanics, and locomotion dynamics.

All four characters implement two primary states:
1. **`idle` Animation:** Alive, breathing, poised, and character-driven idle presence.
2. **`move` Animation:** Fully articulated locomotion cycle showing true foot planting, weight transfer, torso lean, and equipment inertia.

---

## 2. Archetype Motion Profiles & Timing Analysis

| Archetype | Animation State | Frames | Frame Duration | Loop Duration | Motion Profile Dynamics |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Knight** | `idle` | 6 frames | 150 ms | 900 ms | Disciplined martial breathing; flowing crimson plume waves softly; shield and sword held firm. |
| | `move` | 8 frames | 120 ms | 960 ms | Upright martial march; 8-phase alternate leg stride with knee bend, sabaton planting, and plume wave. |
| **Mage** | `idle` | 6 frames | 180 ms | 1080 ms | Serene celestial meditation; floating crystal orb pulses in luminosity; somatic particle spark in free hand. |
| | `move` | 6 frames | 130 ms | 780 ms | Graceful gliding stride; robe hem sways fluidly from side to side; staff tilts forward as walking conduit. |
| **Goblin Rogue** | `idle` | 6 frames | 130 ms | 780 ms | Low-slung twitchy breathing; head tilt; predatory ear twitch on frame 3; subtle dagger gleam. |
| | `move` | 6 frames | 100 ms | 600 ms | Agile, low-slung sneaky scurry; fast stealth strides; bent knees; dagger held forward in reverse grip. |
| **Heavy Brute** | `idle` | 6 frames | 200 ms | 1200 ms | Deep abdominal respiration; chest expands +1px; shoulders rise; beard settles into wide stance. |
| | `move` | 6 frames | 140 ms | 840 ms | Heavy earth-shaking stomping stride; side-to-side weight transfer; boot impact dips body; axe trails with inertia. |

---

## 3. Frame-by-Frame Motion State Breakdown

### 3.1 Knight (Armored March & Combat Vigilance)
- **`idle` Cycle (6 frames, 900ms):**
  - *Frames 0-1:* Upright guard, gentle inhale, shoulders elevate +1px.
  - *Frames 2-3:* Plume peak wave curves backwards, specular gleam on breastplate.
  - *Frames 4-5:* Exhale, plume settles, disciplined recovery to baseline.
- **`move` Cycle (8 frames, 960ms):**
  - *Frame 0:* Left foot forward contact, right foot back, shield held forward.
  - *Frame 1:* Left foot down, body absorbs impact, plume dips.
  - *Frame 2:* Passing pose: right leg passing left knee, sword elevates slightly.
  - *Frame 3:* High pose: right leg reaching ahead.
  - *Frame 4:* Right foot forward contact, left foot back.
  - *Frame 5:* Right foot down, body absorbs impact, plume dips.
  - *Frame 6:* Passing pose: left leg passing right knee.
  - *Frame 7:* High pose: left leg reaching ahead, completing the march.

### 3.2 Mage (Celestial Resonance & Gliding Stride)
- **`idle` Cycle (6 frames, 1080ms):**
  - *Frames 0-1:* Calm floating stance, crystal orb at base cyan glow (`#6dc2ca`).
  - *Frames 2-3:* Arcane pulse: orb core flares to brilliant white (`#deeed6`), somatic spark appears at left fingertips.
  - *Frames 4-5:* Energy pulse softens, robes settle, return to baseline.
- **`move` Cycle (6 frames, 780ms):**
  - *Frames 0-1:* Forward glide, staff tilts forward as conduit, robe hem sways left (`-2px`).
  - *Frames 2-3:* Glide passing pose, staff plants lightly, robe hem sways through center to right (`+2px`).
  - *Frames 4-5:* Floating stride recovery, trailing folds sweep gracefully.

### 3.3 Goblin Rogue (Predatory Twitch & Sneaky Scurry)
- **`idle` Cycle (6 frames, 780ms):**
  - *Frames 0-1:* Deep crouch, ready grip on curved dagger.
  - *Frames 2-3:* Inhale, head tilts, right pointed ear twitches upward (+1px), beady amber eyes glint.
  - *Frames 4-5:* Exhale, ear relaxes, settling back into crouch.
- **`move` Cycle (6 frames, 600ms):**
  - *Frames 0-1:* Fast forward sprint step, left foot thrusts, dagger tucked low in reverse grip.
  - *Frames 2-3:* Low center passing pose, knees bent wide, arms counter-pumping.
  - *Frames 4-5:* Right foot thrusts forward, maintaining low sneaky profile.

### 3.4 Heavy Brute (Slow Heavy Respiration & Stomping Stride)
- **`idle` Cycle (6 frames, 1200ms):**
  - *Frames 0-1:* Massive grounded power stance, battleaxe haft grounded.
  - *Frames 2-3:* Deep chest expansion (barrel chest widens +1px, shoulders rise +1px), braided beard lifts.
  - *Frames 4-5:* Heavy exhale, shoulders drop, beard settles.
- **`move` Cycle (6 frames, 840ms):**
  - *Frames 0-1:* Left stomp: body weight sways left (`mid_x - 1`), left boot slams ground, torso dips under weight.
  - *Frames 2-3:* Passing stride: center elevation, axe haft lifts under arm inertia.
  - *Frames 4-5:* Right stomp: body weight sways right (`mid_x + 1`), right boot slams ground, torso dips.

---

## 4. Godot 4.x Engine Verification

Inspection of the generated `SpriteFrames` resources in `game_assets/experimental_32x32/` confirms:
1. **Named Animations:** Exactly `&"idle"` and `&"move"` registered as sub-resources.
2. **Atlas Texture Regions:** Every frame accurately points to its corresponding cell on the horizontal spritesheet with `Rect2(x, y, 32, 32)`.
3. **Frame Durations & Speed:** Frame duration factors correctly reflect timing ratios (e.g. `1.5x` hold on idle breathing, `1.2x` on stomping contacts).
4. **Looping:** `loop = true` configured for seamless runtime playback.
