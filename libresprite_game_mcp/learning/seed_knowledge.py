"""
Seed Knowledge Module for LibreSprite Learning Layer.
Ingests foundational Art Bible principles synthesized from online authorities and industry masters:
- Sandro Maglione (Atomic pixel placement, regular stair-stepping, jaggies/doubles purge, anti-pillowing)
- vysnvnt (15-minute visual reference rule, canvas budgeting, silhouette-first, anti-aliasing OFF)
- Brandon James Greer (Armature/gesture, black mask test, proofreading at 100% zoom and canvas flip)
- MortMort (Line hygiene, selective outlining, palette economy)
- Pedro Medeiros / Saint11 (4-phase locomotion dynamics, personality-driven idle respiration)

Architectural Guarantee:
All seeded rules are registered as EXTERNAL_REFERENCE with REFERENCE_GUIDANCE/COMMUNITY_CONSENSUS
evidence status and complete bibliographic provenance. They have NO arbitrary confidence scores (None),
and are protected against mutation from empirical feedback.
"""

from __future__ import annotations

from typing import List, Optional
from libresprite_game_mcp.learning.models import (
    EvidenceStatus,
    KnowledgeCategory,
    KnowledgeRecord,
    KnowledgeType,
    ReferenceProvenance,
)
from libresprite_game_mcp.learning.repository import LearningRepository


def get_pixel_art_knowledge_rules() -> List[KnowledgeRecord]:
    """
    Returns the 10 foundational universal Art Bible external reference rules.
    Every rule includes rigorous bibliographic provenance, explicit applicability boundaries,
    known limitations, and conditional scopes.
    """
    return [
        # 1. Silhouette & Black Mask (vysnvnt, Greer, MortMort)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.SILHOUETTE,
            rule_name="Universal Silhouette Readability & Black Mask Rule",
            description=(
                "Characters must be instantly identifiable purely by outer contour when rendered as a solid black mask. "
                "Enforce class-defining shape language: V-taper for Knight, flared skirt hem for Mage, hunchback with lateral "
                "ears for Rogue, and colossal rectangular mass for Brute. Enforce contrapposto and asymmetrical limb placement."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "silhouette_test": "black_mask",
                "require_asymmetry": True,
                "class_shape_motifs": {
                    "knight": "v_taper_broad_pauldrons",
                    "mage": "pyramid_skirt_flared_hem",
                    "rogue": "crooked_hunch_lateral_ears",
                    "brute": "colossal_rectangle_heavy_stance",
                },
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Beginner's Guide: How I Started Drawing Pixel Characters",
                author="vysnvnt",
                source_url="https://vysnvnt.medium.com/beginners-guide-how-i-started-drawing-pixel-characters-db534a0cde53",
                access_date="2026-11-24",
                extracted_principle="Block out the silhouette first; readability relies entirely on the silhouette shape before internal detail.",
                interpretation="Render sprite in monochromatic mask. If archetype and posture are unreadable, internal detail cannot rescue it.",
                applicable_asset_categories=["character"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["pixel_art", "chibi", "retro_rpg", "arcade"],
                known_limitations=["Does not apply to abstract non-figurative entities or particle effects."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 2. Native Canvas Resolution Budgeting (vysnvnt, Maglione)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.COMPOSITION,
            rule_name="Native Canvas Resolution Budgeting",
            description=(
                "Scale dictates abstraction. For 16x16: symbolic chibi, head = 40-50% height, 1-2px limbs. "
                "For 32x32: standard indie character sweet spot, head = 30-38% height, 2x3 expressive eyes with pupils and glints. "
                "Reserve 3-4px top clearance for jump/rebound and 2px at bottom for grounding shadow."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "head_ratio_16x16": [0.42, 0.50],
                "head_ratio_32x32": [0.30, 0.38],
                "top_clearance_px": 4,
                "ground_shadow_rows": 2,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Getting started with Pixel Art - A beginner perspective",
                author="Sandro Maglione",
                source_url="https://www.sandromaglione.com/articles/getting-started-with-pixel-art",
                access_date="2026-11-24",
                extracted_principle="Pixel art is abstraction and simplification working on an atomic level within strict grid budgets.",
                interpretation="Canvas dimensions strictly govern anatomical head-to-body ratios and vertical clearance budgets.",
                applicable_asset_categories=["character"],
                applicable_resolutions=["16x16", "32x32"],
                applicable_styles=["chibi", "retro_rpg"],
                known_limitations=["Proportions must be adjusted for non-humanoid creatures, quadrupeds, or isometric views."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 3. Mathematical Stair-Stepping & Jaggies Purge (Maglione, MortMort)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.OUTLINE,
            rule_name="Mathematical Stair-Stepping & Jaggies Purge",
            description=(
                "Contour curves and diagonal linework must follow monotonic, mathematically regular step sequences "
                "(e.g., 3-2-1-1-2-3). Eliminate erratic step jumps (jaggies, e.g. 3-1-4-1) that disrupt visual curve rhythm."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "line_stepping": "monotonic",
                "disallow_jaggies": True,
                "max_step_delta": 1,
                "outline_mode": "colored",
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Getting started with Pixel Art - A beginner perspective",
                author="Sandro Maglione",
                source_url="https://www.sandromaglione.com/articles/getting-started-with-pixel-art",
                access_date="2026-11-24",
                extracted_principle="Curves require regular increasing/decreasing adjacent pixel counts; jaggies are spiky irregular step breaks.",
                interpretation="Enforce monotonic step progressions on curved contours (helmets, skulls, shields, blades).",
                applicable_asset_categories=["character", "item", "tileset"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48", "64x64"],
                applicable_styles=["clean_pixel_art", "sharp_contour"],
                known_limitations=["Natural rough textures (e.g. jagged stone, torn rags) intentionally use broken steps."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 4. Elimination of Double Pixels and Clumping (Maglione, MortMort)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.OUTLINE,
            rule_name="Elimination of Double Pixels and Clumping",
            description=(
                "Purge accidental 2x2 corner-sharing pixel clusters on single-pixel diagonal lines. "
                "Lines intended to be 1px wide must maintain single-pixel thickness to prevent line bloat and preserve sharpness."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "purge_doubles": True,
                "diagonal_width_px": 1,
                "outline_mode": "colored",
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Getting started with Pixel Art - A beginner perspective",
                author="Sandro Maglione",
                source_url="https://www.sandromaglione.com/articles/getting-started-with-pixel-art",
                access_date="2026-11-24",
                extracted_principle="Doubles are redundant blocks of pixels that add unnecessary thickness and destroy line flow.",
                interpretation="Enforce single-pixel diagonal width on linework and contours to eliminate unintended bulk.",
                applicable_asset_categories=["character", "item"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["pixel_art"],
                known_limitations=["Thick 2px outer hero outlines or intentional junction corners may intentionally clump."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 5. Strict Palette Discipline & Temperature Hue Shifting (DB16 Scoped)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.REFERENCE_GUIDANCE,
            category=KnowledgeCategory.PALETTE,
            rule_name="Strict Palette Discipline & Temperature Hue Shifting",
            description=(
                "When DB16 palette is selected: strictly cap sprite colors to DawnBringer DB16 shades. "
                "Ban raw mathematical RGB lightening ((255-r)*0.25). Shift highlight hues warm (yellow, cream, gold) "
                "and shadow hues cool (navy, violet, teal) to avoid lifeless, muddy sprites."
            ),
            conditions={"task_category": "character", "palette_name": "db16"},
            recommendations={
                "recommended_palette": "db16",
                "highlights_temperature": "warm_yellow_cream",
                "shadows_temperature": "cool_violet_navy",
                "allow_raw_rgb_math": False,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Pixel Art Tutorial: Color Theory and Palette Selection",
                author="Derek Yu",
                source_url="https://www.derekyu.com/makegames/pixelart.html",
                access_date="2026-11-24",
                extracted_principle="Hue shifting creates dynamic, lively color ramps: shift highlights toward warm light and shadows toward cool ambient tones.",
                interpretation="All RGB values must map 100% to project palette constants; never compute raw linear RGB tint offsets.",
                applicable_asset_categories=["character", "item", "tileset"],
                applicable_resolutions=["16x16", "32x32"],
                applicable_styles=["db16", "fantasy_retro"],
                known_limitations=["Only applies when project ArtProfile selects DB16; do not enforce on PICO-8, Game Boy, or custom palettes."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 6. Directional Cluster Shading & Anti-Pillowing Ban (Maglione, vysnvnt)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.LIGHTING,
            rule_name="Directional Cluster Shading & Anti-Pillow-Shading Ban",
            description=(
                "Establish consistent directional key light (top-left 45 degrees). Ban concentric pillow-shading inward from borders. "
                "Group shades into solid >= 2x2 pixel clusters. Enforce mandatory cast shadows under jaw, bangs/helmet, belt, and ground ellipse."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "light_source": "top_left_45_deg",
                "shading_style": "cluster",
                "min_cluster_size": [2, 2],
                "pillow_shading_allowed": False,
                "mandatory_shadows": ["chin_drop", "hair_drop", "belt_crevice", "ground_ellipse"],
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Getting started with Pixel Art - A beginner perspective",
                author="Sandro Maglione",
                source_url="https://www.sandromaglione.com/articles/getting-started-with-pixel-art",
                access_date="2026-11-24",
                extracted_principle="Avoid pillow shading: light must originate from an explicit directional source rather than wrapping around edges.",
                interpretation="Render shading in cohesive clusters based on surface normals facing the top-left key light.",
                applicable_asset_categories=["character", "item"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["pixel_art"],
                known_limitations=["1px specular glints on eyes, blades, or gems are exempt from the 2x2 cluster size minimum."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 7. Selective Outlining (Sel-Out) and Interior Seam Ramping (MortMort, BJG)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.OUTLINE,
            rule_name="Selective Outlining (Sel-Out) and Interior Seam Ramping",
            description=(
                "Outer perimeter uses dark boundary color (#140c1c). "
                "Interior seams between clothing, armor, and anatomy use the local material's shadow ramp, NEVER pure black. "
                "Prevents coloring-book sticker blobbing around eyes and equipment."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "exterior_outline": "#140c1c",
                "interior_seams": "local_shadow_ramp",
                "pure_black_interior_allowed": False,
                "outline_mode": "colored",
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Pixel Art Linework and Outlining Guide",
                author="MortMort",
                source_url="https://www.youtube.com/c/MortMort",
                access_date="2026-11-24",
                extracted_principle="Sel-out (selective outlining) softens hard interior transitions by matching outline colors to adjacent internal ramps.",
                interpretation="Outer boundary provides contrast against arbitrary backgrounds; inner seams use shadow ramps to preserve depth.",
                applicable_asset_categories=["character", "item"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["pixel_art", "sel_out"],
                known_limitations=["Lineless styles or high-contrast 1-bit monochrome games do not use sel-out."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 8. Controlled Dithering Prohibition on Low Resolutions (Maglione)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.DITHERING,
            rule_name="Controlled Dithering Prohibition on Low Resolutions",
            description=(
                "Disallow loose checkerboard dithering on sprites smaller than 48x48. "
                "Prefer solid pixel clusters to prevent visual static, mud, and animation flicker on low resolutions."
            ),
            conditions={"task_category": "character", "resolution": ["16x16", "24x24", "32x32"]},
            recommendations={
                "dithering_allowed_under_48px": False,
                "preferred_shading": "solid_clusters",
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Getting started with Pixel Art - A beginner perspective",
                author="Sandro Maglione",
                source_url="https://www.sandromaglione.com/articles/getting-started-with-pixel-art",
                access_date="2026-11-24",
                extracted_principle="Dithering should be used sparingly; modern pixel art cautions against noisy checkerboard patterns on small grids.",
                interpretation="On grids <= 32x32, solid cluster boundaries maintain clarity; dithering creates visual mud and animation noise.",
                applicable_asset_categories=["character"],
                applicable_resolutions=["16x16", "24x24", "32x32"],
                applicable_styles=["pixel_art", "clean"],
                known_limitations=["Large environmental backgrounds, skies, or retro PC-98/Amiga styles may utilize dithering."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 9. Articulated Locomotion Dynamics & Weight Transfer (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.ANIMATION_TIMING,
            rule_name="Articulated Locomotion Dynamics & Weight Transfer",
            description=(
                "Locomotion walk cycles must implement true 4-phase gait mechanics: Contact, Squash (Down), Passing, Lift (Up). "
                "Incorporate side-to-side weight transfer (sway_x) for heavy classes and forward lean for agile runners. "
                "Ban pure 1px vertical body bobs."
            ),
            conditions={"task_category": "character", "animation_state": "move"},
            recommendations={
                "walk_phases": ["contact", "down_squash", "passing", "up_lift"],
                "min_frames": 6,
                "allow_pure_vertical_bob": False,
                "secondary_inertia_delay_frames": 1,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Pixel Art Walk Cycle Tutorials",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Walk cycles require four biomechanical phases: contact, down (squash), passing, and up (push-off) with weight transfer.",
                interpretation="Movement animations must articulate leg extension and weight transfer; 1px bobbing does not constitute walking.",
                applicable_asset_categories=["character"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["animated_sprite"],
                known_limitations=["Hovering spellcasters or wheeled vehicles do not use leg contact gait phases."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 10. Proofreading Protocol (100% Native Scale & Canvas Flip) (Greer)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.GENERAL,
            rule_name="Proofreading Protocol (100% Native Scale & Canvas Flip)",
            description=(
                "Mandatory final quality checks before committing or exporting: "
                "1. Inspect sprite at 100% native scale to confirm readability without magnification. "
                "2. Mirror/flip canvas horizontally to expose anatomical tilt bias and awkward shoulders. "
                "3. Verify binary alpha hygiene: alpha in {0, 255} with zero semi-transparent pixels."
            ),
            conditions={"task_category": "character"},
            recommendations={
                "verify_native_1x_zoom": True,
                "perform_horizontal_flip": True,
                "require_binary_alpha": True,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Proofreading Your Pixel Art: 5 Common Mistakes",
                author="Brandon James Greer",
                source_url="https://www.youtube.com/c/BrandonJamesGreer",
                access_date="2026-11-24",
                extracted_principle="Proofread pixel art by checking 100% native scale and flipping canvas horizontally to reset visual bias.",
                interpretation="Inspect unmagnified sprite to ensure cluster readability; flip sprite to check anatomical balance.",
                applicable_asset_categories=["character", "item", "tileset"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48", "64x64"],
                applicable_styles=["all"],
                known_limitations=["Intentionally asymmetrical character designs will appear asymmetric when flipped."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 11. Concentric High-Luminance Core & Additive Glow Ramp (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.VFX_SPELLS,
            rule_name="Concentric High-Luminance Core & Additive Glow Ramp",
            description=(
                "Pixel art energy, fire, lightning, and magic cannot rely on true additive blending. "
                "Convey intense magical luminance via a strict concentric 4-tier color ramp: "
                "Tier 1 (Core): Pure white (#ffffff) at center of mass/ignition. "
                "Tier 2 (Spectral Bloom): Highly saturated primary tint (bright yellow, electric cyan, radiant violet). "
                "Tier 3 (Chromatic Body): Medium body color (orange, cobalt, deep purple). "
                "Tier 4 (Ambient Falloff): Dark contextual rim outline; never use pure black outlines on emissive energy."
            ),
            conditions={"task_category": "spell", "effect_type": "emissive"},
            recommendations={
                "core_color": "#ffffff",
                "min_color_tiers": 4,
                "allow_pure_black_outline": False,
                "concentric_ramp": True,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Pixel Art FX and Magic Tutorials",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Magical energy requires a white-hot core surrounded by saturated rings; avoid black outlines around glowing effects.",
                interpretation="Use color temperature and stepped luminance bands instead of alpha gradients to simulate emissive glow.",
                applicable_asset_categories=["spell", "vfx", "projectile"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48", "64x64"],
                applicable_styles=["pixel_art", "animated_vfx"],
                known_limitations=["Dark void or shadow magic reverses luminance, using an obsidian core with bright outer corona."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 12. Non-Linear FX Timing & Snap-Decay Kinetic Curve (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.ANIMATION_TIMING,
            rule_name="Non-Linear FX Timing & Snap-Decay Kinetic Curve",
            description=(
                "Explosions, slashes, impacts, and spellbursts must avoid linear uniform frame durations. "
                "Apply the snap-decay curve: "
                "1. Anticipation/Ignition: Fast 1-frame charge (60-80ms). "
                "2. Snap Apex/Impact Flash: Immediate maximum expansion with white impact frame (50-70ms). "
                "3. Expansion/Shockwave: Expanding ring or hollow burst (80-100ms). "
                "4. Dissipation & Decay: Slower trailing decay with fragmenting embers (100-130ms)."
            ),
            conditions={"task_category": "vfx", "animation_type": "burst"},
            recommendations={
                "timing_curve": "fast_attack_slow_decay",
                "include_impact_flash_frame": True,
                "climax_frame_index": 1,
                "decay_duration_multiplier": 1.5,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Animation Timing in Special Effects",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Impacts and bursts should reach their peak quickly (frame 1 or 2), then spend several frames decaying and dispersing.",
                interpretation="Linear frame timing makes magic feel floaty and weak. Explosive snap followed by lingering dissipation gives attacks punch.",
                applicable_asset_categories=["vfx", "spell", "impact"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48"],
                applicable_styles=["animated_vfx"],
                known_limitations=["Continuous looping beams or gentle weather effects use uniform frame timing."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 13. Volume Breakup, Smoke Holes & Dissipating Negative Space (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.VFX_SPELLS,
            rule_name="Volume Breakup, Smoke Holes & Dissipating Negative Space",
            description=(
                "When spells and explosions dissipate, they must NOT simply shrink uniformly. "
                "As the shockwave expands, carve interior negative space ('smoke holes') into the core volume, "
                "breaking the solid shape into 3-5 distinct flying sub-clusters and fading particle embers."
            ),
            conditions={"task_category": "vfx", "effect_state": "dissipation"},
            recommendations={
                "carve_negative_space": True,
                "fragment_into_clusters": True,
                "avoid_uniform_scaling": True,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Explosion and Smoke Dissipation Guide",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Explosions hollow out in the center as they expand, breaking into drifting clumps of smoke rather than scaling down.",
                interpretation="Hollow out the center on frame 3 and break the perimeter into asymmetrical chunks to simulate fluid dynamics.",
                applicable_asset_categories=["vfx", "explosion", "magic_burst"],
                applicable_resolutions=["16x16", "24x24", "32x32", "48x48", "64x64"],
                applicable_styles=["animated_vfx"],
                known_limitations=["Solid crystallizing effects (e.g. ice prison) shatter into shards rather than hollowing smoke."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 14. Projectile Aerodynamics & Stepped Embers Trail (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.VFX_SPELLS,
            rule_name="Projectile Aerodynamics & Stepped Embers Trail",
            description=(
                "Moving magical projectiles (missiles, fireballs, energy bolts) must convey vector velocity: "
                "1. Leading Head: Rounded, high-luminance energy cap facing direction of motion. "
                "2. Body: Tapering teardrop aerodynamic stream with cluster shading. "
                "3. Trailing Tail: Stepped, detached 1-2px particle motes drifting backwards with decreasing size and opacity."
            ),
            conditions={"task_category": "spell", "effect_type": "projectile"},
            recommendations={
                "aerodynamic_silhouette": "teardrop_taper",
                "leading_edge_highlight": True,
                "trailing_particle_motes": True,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Designing Projectiles and Missiles in Pixel Art",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Projectiles need a distinct front (highest contrast) and trailing sparks behind to indicate direction and speed.",
                interpretation="Place the brightest highlights on the front nose; let tail flickers lag behind across alternating frames.",
                applicable_asset_categories=["spell", "projectile"],
                applicable_resolutions=["16x16", "24x24", "32x32"],
                applicable_styles=["animated_vfx"],
                known_limitations=["Spherical floating orbs (like slow homing wisp mines) do not require teardrop elongation."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),

        # 15. Ground Glyph Perspective & Vertical Energy Emission (Saint11)
        KnowledgeRecord(
            project_id=None,
            knowledge_type=KnowledgeType.EXTERNAL_REFERENCE,
            evidence_status=EvidenceStatus.COMMUNITY_CONSENSUS,
            category=KnowledgeCategory.VFX_SPELLS,
            rule_name="Ground Glyph Perspective & Vertical Energy Emission",
            description=(
                "Area of Effect (AoE) summon circles, healing wells, and sanctuary runes must anchor to the 2D world floor "
                "using a 2:1 aspect ratio ground ellipse. Runic symbols inside the ellipse must adhere to flattened perspective. "
                "Magical emissions (light pillars, rising sparkles, ascending smoke) erupt vertically perpendicular to the ground plane."
            ),
            conditions={"task_category": "spell", "effect_type": "aoe_ground"},
            recommendations={
                "ground_ellipse_aspect_ratio": "2:1",
                "vertical_beam_emission": True,
                "ascending_sparkle_particles": True,
            },
            confidence_score=None,
            provenance=ReferenceProvenance(
                source_title="Magic Circles and Ground Runes",
                author="Pedro Medeiros (Saint11)",
                source_url="https://blog.studiominiboss.com/pixelart",
                access_date="2026-11-24",
                extracted_principle="Ground magic must be drawn flattened in perspective (oval) while the magic beams project straight upwards.",
                interpretation="Draw base magic ring as a 2:1 horizontal oval on the ground; animate vertical light pillars and rising motes above it.",
                applicable_asset_categories=["spell", "aoe", "vfx"],
                applicable_resolutions=["32x32", "48x48", "64x64"],
                applicable_styles=["animated_vfx"],
                known_limitations=["Wall-mounted runes or ceiling traps orient to the respective surface normal."],
                validation_status="COMMUNITY_CONSENSUS",
            ),
        ),
    ]


def seed_art_bible_knowledge(
    repo: LearningRepository,
    overwrite: bool = False,
) -> List[KnowledgeRecord]:
    """
    Idempotently seeds the 15 universal Art Bible external reference rules (Characters, Environments, and Spells/VFX) into the provided repository.
    If a rule with the same rule_name already exists and overwrite is False, it preserves the existing rule.
    Returns the list of seeded/existing KnowledgeRecords.
    """
    rules = get_pixel_art_knowledge_rules()
    seeded_records: List[KnowledgeRecord] = []

    # Query existing universal rules
    existing_rules = {r.rule_name: r for r in repo.query_knowledge(project_id=None, limit=200)}

    for rule in rules:
        if rule.rule_name in existing_rules:
            if not overwrite:
                seeded_records.append(existing_rules[rule.rule_name])
                continue
            else:
                rule.id = existing_rules[rule.rule_name].id
        saved = repo.save_knowledge(rule)
        seeded_records.append(saved)

    return seeded_records
