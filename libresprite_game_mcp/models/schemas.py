"""
Structured Pydantic schemas for Project Art Profiles, Asset Blueprints, and QA Validation.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field


class OutlineConfig(BaseModel):
    enabled: bool = True
    mode: str = Field(default="colored", description="Options: black, colored, sel_out, none")
    diagonal: bool = False


class LightingConfig(BaseModel):
    direction: str = Field(default="top_left", description="Options: top_left, top, front")
    hue_shift: bool = True
    ambient_shadow_color: str = "#140c1c"
    specular_highlight_color: str = "#fff1e8"


class AnimationConfig(BaseModel):
    timing_unit: str = "ms"
    default_fps: float = 10.0
    preserve_foot_pivot: bool = True


class ArtProfile(BaseModel):
    """Governs the visual identity and engine constraints of a game project."""
    project_name: str = "DefaultGame"
    engine: str = Field(default="godot_4", description="Target engine: godot_4, unity_2d, generic")
    perspective: str = Field(default="top_down", description="Options: top_down, side_scroller, isometric")
    native_resolution: Tuple[int, int] = (320, 180)
    tile_size: Tuple[int, int] = (16, 16)
    character_base_size: Tuple[int, int] = (16, 16)
    palette_name: str = "db16"
    custom_palette: Optional[List[str]] = None
    outlines: OutlineConfig = Field(default_factory=OutlineConfig)
    lighting: LightingConfig = Field(default_factory=LightingConfig)
    animation: AnimationConfig = Field(default_factory=AnimationConfig)


class CharacterAnimationSpec(BaseModel):
    frames: int = 2
    duration_ms: int = 150
    loop: bool = True


class CharacterBlueprint(BaseModel):
    """Specification for character anatomy, costume layers, and animations."""
    character_id: str
    name: str
    size: Tuple[int, int] = (16, 16)
    proportion: str = Field(default="chibi_1_2", description="Options: chibi_1_2, sd_1_1, heroic_1_3")
    archetype: Optional[str] = Field(default=None, description="Options: knight, mage, goblin, heavy_brute, rogue, hero")
    colors: Dict[str, str] = Field(default_factory=dict)
    views: List[str] = Field(default_factory=lambda: ["down", "left", "right", "up"])
    animations: Dict[str, CharacterAnimationSpec] = Field(default_factory=dict)
    pivot: Tuple[float, float] = (0.5, 0.9)


class TilesetSpec(BaseModel):
    """Specification for environment terrain, autotiling, and collision."""
    tileset_id: str
    name: str
    tile_size: int = 16
    system: str = Field(default="autotile_3x3", description="Options: autotile_3x3, wang_16, blob_47")
    theme_name: str = "grass_dirt"
    custom_theme: Optional[Dict[str, str]] = None
    solid_indices: List[int] = Field(default_factory=list)


class ItemSpec(BaseModel):
    """Specification for weapons, potions, props, and collectibles."""
    item_id: str
    name: str
    category: str = Field(default="sword", description="Options: sword, potion, torch, coin, prop")
    dimensions: Tuple[int, int] = (16, 16)
    variant: Optional[str] = None
    animated: bool = False
    frame_count: int = 1


class ValidationCheck(BaseModel):
    passed: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Automated Art QA audit report for game assets."""
    asset_name: str
    passed: bool
    checks: Dict[str, ValidationCheck] = Field(default_factory=dict)
    critical_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    ready_for_export: bool = False
