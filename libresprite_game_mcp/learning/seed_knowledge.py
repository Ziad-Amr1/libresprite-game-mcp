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
    ]


def seed_art_bible_knowledge(
    repo: LearningRepository,
    overwrite: bool = False,
) -> List[KnowledgeRecord]:
    """
    Idempotently seeds the 10 universal Art Bible external reference rules into the provided repository.
    If a rule with the same rule_name already exists and overwrite is False, it preserves the existing rule.
    Returns the list of seeded/existing KnowledgeRecords.
    """
    rules = get_pixel_art_knowledge_rules()
    seeded_records: List[KnowledgeRecord] = []

    # Query existing universal rules
    existing_rules = {r.rule_name: r for r in repo.query_knowledge(project_id=None, limit=200)}

    for rule in rules:
        if rule.rule_name in existing_rules and not overwrite:
            seeded_records.append(existing_rules[rule.rule_name])
        else:
            saved = repo.save_knowledge(rule)
            seeded_records.append(saved)

    return seeded_records
