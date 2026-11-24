# AI Pixel Art Production Workflow

**Standard 10-Step Asset Production Lifecycle**  
**Version:** 1.0  

---

## 1. The 10-Step Production Pipeline

To deliver game-ready pixel art rather than disconnected images, every asset progresses through this structured pipeline:

```
[1. User Request] ──> [2. Asset Spec] ──> [3. Design Plan] ──> [4. Draft Canvas] ──> [5. Native Preview]
                                                                                           │
[10. User Signoff] <── [9. Engine Test] <── [8. Engine Export] <── [7. QA Audit] <── [6. Critique & Revise]
```

### Step 1: Understand the Request
* Parse the user prompt for asset category, style intent, target resolution, and movement requirements.
* Determine whether the asset belongs to an existing game project or requires a new `ArtProfile`.

### Step 2: Establish Asset Specification & Art Profile
* Retrieve or construct the typed `ArtProfile` (e.g. `db16` palette, 16x16 tile grid, top-down perspective).
* Define the `CharacterBlueprint`, `TilesetSpec`, or `ItemSpec` with explicit color schemes, views, and animation tags.

### Step 3: Design Planning
* **Character Designer** selects silhouette shape language (circle/square/triangle) and head-to-body proportion ratio.
* Plan layer hierarchy (`Shadow`, `Body`, `Costume`, `Gear`, `VFX`).

### Step 4: Generate Draft Canvas (Native Resolution)
* **Pixel Artist** constructs the raster data at true 1:1 pixel scale (e.g., 16x16 or 32x32).
* Enforce pixel clustering: no isolated stray pixels; smooth outline stepping; hue-shifted ramps.

### Step 5: Native & Scaled Preview
* Render the draft at native resolution and upscale 4x (nearest-neighbor) for human/AI evaluation.
* Ensure contrast and readability hold up against both dark and light game backgrounds.

### Step 6: Critique & Revision Loop
* **Art Director** and **Pixel Artist** inspect:
  * Are silhouettes recognizable?
  * Do colors match the Art Profile palette?
  * Do animation key poses convey weight and anticipation?
* Apply targeted modifications to specific layers without regenerating the entire asset.

### Step 7: Automated QA Validation
* Run `AssetValidator` checks:
  * Zero unauthorized palette colors.
  * Zero translucent border pixels (`0 < a < 255`).
  * Consistent feet baseline and pivot coordinate (`0.5, 0.9`).
  * Seamless edges for tiling assets.
* If validation fails with critical errors, trigger an automatic revision pass (up to 3 attempts).

### Step 8: Multi-Format Game Engine Export
* **Godot Integration Specialist** builds:
  * Texture Atlas PNG with $\ge 1\text{px}$ shape and border padding.
  * Godot 4.x `SpriteFrames` (.tres) with valid `[sub_resource type="AtlasTexture"]` blocks.
  * TexturePacker / Aseprite JSON Hash/Array metadata.
  * Native `.aseprite` project with named layers.

### Step 9: Engine Validation
* Verify that the exported `.tres` and `.png` adhere strictly to Godot 4 resource syntax.
* Verify frame rect bounds match atlas dimensions exactly.

### Step 10: Human Sign-off & Project Integration
* Atomically move validated assets into the project's destination folder.
* Present the user with a crisp preview, layer summary, and Godot usage instructions.
