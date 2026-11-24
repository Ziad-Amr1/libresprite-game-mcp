"""
Tool Contract Registry and Dispatcher for LibreSprite Production Art System.
Provides explicit allowlisted tool contracts, parameter/output validation,
and strict runtime separation between PRODUCTION, SANDBOX, MOCK, and LIVE_RUNTIME modes.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from PIL import Image

from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.core.palettes import hex_to_rgba
from libresprite_game_mcp.core.pixel_art_ops import PixelCanvas
from libresprite_game_mcp.core.security import workspace_policy
from libresprite_game_mcp.exporters.game_export import (
    export_godot_spriteframes,
    export_pixilart_project,
    export_sprite_sheet_native,
)
from libresprite_game_mcp.generators.character_generator import (
    build_animated_character_project,
)
from libresprite_game_mcp.generators.item_generator import (
    generate_potion_icon,
    generate_sword_icon,
)
from libresprite_game_mcp.generators.tileset_generator import (
    build_autotile_3x3_sheet,
)
from libresprite_game_mcp.models.schemas import CharacterBlueprint
from libresprite_game_mcp.qa.validator import AssetValidator


class ExecutionMode(str, Enum):
    PRODUCTION = "PRODUCTION"
    SANDBOX = "SANDBOX"
    MOCK = "MOCK"
    LIVE_RUNTIME = "LIVE_RUNTIME"


class ToolExecutionError(RuntimeError):
    """Raised when an allowlisted tool fails execution in production."""
    pass


class ToolContract:
    """Specification of an approved tool contract."""

    def __init__(
        self,
        name: str,
        handler: Callable[[Dict[str, Any], Path], Dict[str, Any]],
        description: str = "",
        required_params: Optional[List[str]] = None,
        output_keys: Optional[List[str]] = None,
        execution_type: str = "python_service",
    ):
        self.name = name
        self.handler = handler
        self.description = description
        self.required_params = required_params or []
        self.output_keys = output_keys or []
        self.execution_type = execution_type

    def validate_inputs(self, params: Dict[str, Any]) -> None:
        missing = [req for req in self.required_params if req not in params or params[req] is None]
        if missing:
            raise ValueError(f"Tool '{self.name}' missing required parameters: {missing}")

    def validate_outputs(self, outputs: Dict[str, Any]) -> None:
        if not isinstance(outputs, dict):
            raise ToolExecutionError(f"Tool '{self.name}' returned invalid non-dict output.")
        for key in self.output_keys:
            if key not in outputs:
                raise ToolExecutionError(f"Tool '{self.name}' output missing required key: '{key}'")


# -----------------------------------------------------------------------------
# Real Production Tool Implementations
# -----------------------------------------------------------------------------

def _prod_generate_character(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    character_id = str(params.get("character_id", "character"))
    name = str(params.get("name", character_id))
    size_param = params.get("size", (16, 16))
    size = tuple(size_param) if isinstance(size_param, (list, tuple)) else (16, 16)
    proportion = str(params.get("proportion", "chibi_1_2"))
    palette_name = str(params.get("palette_name", "db16"))

    bp = CharacterBlueprint(
        character_id=character_id,
        name=name,
        size=size,
        proportion=proportion,
    )

    project = build_animated_character_project(blueprint=bp, palette_name=palette_name)
    target_path = workspace / f"{character_id}.aseprite"
    project.save(target_path)

    # Export a preview PNG
    preview_path = workspace / f"{character_id}_preview.png"
    frames = project.get_all_frame_images()
    if frames:
        frames[0].save(preview_path)

    return {
        "project_path": str(target_path),
        "preview_path": str(preview_path),
        "character_id": character_id,
        "width": size[0],
        "height": size[1],
        "frames": len(project.sprite.frames),
    }


def _prod_generate_tileset(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    tileset_id = str(params.get("tileset_id", "tileset"))
    tile_size = int(params.get("tile_size", 16))
    theme_name = str(params.get("theme_name", "grass_dirt"))

    img = build_autotile_3x3_sheet(tile_size=tile_size, theme_name=theme_name)
    target_path = workspace / f"{tileset_id}.png"
    img.save(target_path)

    return {
        "project_path": str(target_path),
        "tileset_id": tileset_id,
        "width": img.width,
        "height": img.height,
        "tile_size": tile_size,
    }


def _prod_generate_item(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    item_id = str(params.get("item_id", "item"))
    category = str(params.get("category", "sword"))
    size = int(params.get("size", 16))

    if category == "potion":
        img = generate_potion_icon(size=size)
    else:
        img = generate_sword_icon(size=size)

    target_path = workspace / f"{item_id}.png"
    img.save(target_path)

    return {
        "project_path": str(target_path),
        "item_id": item_id,
        "width": img.width,
        "height": img.height,
    }


def _prod_apply_outline(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    project_path_str = params.get("project_path") or params.get("input_file")
    if not project_path_str:
        raise ValueError("Tool 'apply_outline' requires 'project_path' or 'input_file'.")

    p = Path(project_path_str).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Asset file not found for outline application: '{p}'")

    mode = str(params.get("mode", "colored"))
    outline_color = hex_to_rgba(params.get("outline_color", "#140c1c"))
    diagonal = bool(params.get("diagonal", False))

    if p.suffix.lower() in (".ase", ".aseprite"):
        project = AsepriteProject.load(p)
        layer_name = list(project.layers.keys())[0] if project.layers else "Layer 1"
        for i in range(len(project.sprite.frames)):
            img = project.get_frame_image(i)
            canvas = PixelCanvas.from_image(img)
            canvas.add_outline(outline_color=outline_color, diagonal=diagonal)
            project.set_frame_image(i, layer_name, canvas.image)
        project.save(p)
    else:
        img = Image.open(p).convert("RGBA")
        canvas = PixelCanvas.from_image(img)
        canvas.add_outline(outline_color=outline_color, diagonal=diagonal)
        canvas.image.save(p)

    return {
        "project_path": str(p),
        "outline_applied": True,
        "mode": mode,
    }


def _prod_validate_asset(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    project_path_str = params.get("project_path") or params.get("input_file")
    if not project_path_str:
        raise ValueError("Tool 'validate_asset' requires 'project_path' or 'input_file'.")

    p = Path(project_path_str).resolve()
    if not p.exists():
        return {
            "passed": False,
            "critical_errors": [f"Target artifact does not exist: '{p}'"],
            "warnings": [],
            "ready_for_export": False,
        }

    expected_size = params.get("expected_size") or params.get("size")
    if expected_size and isinstance(expected_size, (list, tuple)) and len(expected_size) >= 2:
        exp_tuple = (int(expected_size[0]), int(expected_size[1]))
    else:
        exp_tuple = None

    palette = params.get("palette_name")
    validator = AssetValidator(
        palette=palette,
        expected_size=exp_tuple,
    )

    if p.suffix.lower() in (".ase", ".aseprite"):
        project = AsepriteProject.load(p)
        report = validator.validate_project(project, asset_name=p.stem)
    else:
        img = Image.open(p)
        report = validator.validate_image(img, asset_name=p.stem)

    res = report.model_dump()
    res["project_path"] = str(p)
    res["input_file"] = str(p)
    return res


def _prod_export_godot_spritesheet(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    project_path_str = params.get("project_path") or params.get("input_file")
    if not project_path_str:
        raise ValueError("Tool 'export_godot_spritesheet' requires 'project_path'.")

    p = Path(project_path_str).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Project file not found for Godot export: '{p}'")

    if p.suffix.lower() == ".pixil":
        candidate_ase = p.with_suffix(".aseprite")
        if not candidate_ase.exists():
            candidate_ase = p.with_suffix(".ase")
        if candidate_ase.exists():
            project = AsepriteProject.load(candidate_ase)
        else:
            import json
            with open(p, "r", encoding="utf-8") as f:
                pixil_data = json.load(f)
            w = pixil_data.get("width", 16)
            h = pixil_data.get("height", 16)
            project = AsepriteProject(w, h)
            for fr in pixil_data.get("frames", []):
                frame_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                for layer in fr.get("layers", []):
                    for px in layer.get("pixels", []):
                        frame_img.putpixel((px["x"], px["y"]), hex_to_rgba(px["color"]))
                project.add_animation_frame(duration_ms=fr.get("duration_ms", 100), layer_images={"Layer 1": frame_img})
    else:
        project = AsepriteProject.load(p)

    target_tres = workspace / f"{p.stem}_spriteframes.tres"
    target_png = workspace / f"{p.stem}_sheet.png"

    # Export spritesheet
    export_sprite_sheet_native(project, target_png)
    res_tex_path = f"res://{target_png.name}"
    export_godot_spriteframes(
        project=project,
        sheet_texture_res_path=res_tex_path,
        output_tres_path=target_tres,
    )

    return {
        "sheet_png": str(target_png),
        "tres_file": str(target_tres),
        "exported": True,
        "target_engine": "godot_4",
    }


def _prod_export_pixilart_project(params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
    project_path_str = params.get("project_path") or params.get("input_file")
    if not project_path_str:
        raise ValueError("Tool 'export_pixilart_project' requires 'project_path'.")

    p = Path(project_path_str).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Project file not found for Pixilart export: '{p}'")

    project = AsepriteProject.load(p)
    target_pixil = workspace / f"{p.stem}.pixil"
    title = str(params.get("title", p.stem))

    saved_path = export_pixilart_project(project, target_pixil, title=title)

    return {
        "saved_path": str(saved_path),
        "project_path": str(p),
        "format": "pixil",
        "exported": True,
    }


# -----------------------------------------------------------------------------
# Dispatcher Implementations
# -----------------------------------------------------------------------------

class BaseToolDispatcher:
    """Base interface for tool execution dispatchers."""

    def dispatch(self, tool_name: str, params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        raise NotImplementedError


class ProductionToolDispatcher(BaseToolDispatcher):
    """Executes real production tool implementations against actual filesystem artifacts."""

    def __init__(self):
        self.contracts: Dict[str, ToolContract] = {
            "generate_character": ToolContract(
                name="generate_character",
                handler=_prod_generate_character,
                description="Generates base character anatomy project file",
                output_keys=["project_path", "character_id"],
            ),
            "generate_tileset": ToolContract(
                name="generate_tileset",
                handler=_prod_generate_tileset,
                description="Generates 3x3 autotile sheet",
                output_keys=["project_path"],
            ),
            "generate_item": ToolContract(
                name="generate_item",
                handler=_prod_generate_item,
                description="Generates pixel art weapon or item icon",
                output_keys=["project_path"],
            ),
            "apply_outline": ToolContract(
                name="apply_outline",
                handler=_prod_apply_outline,
                description="Applies outline and cleans stray pixels",
                output_keys=["project_path", "outline_applied"],
            ),
            "validate_asset": ToolContract(
                name="validate_asset",
                handler=_prod_validate_asset,
                description="Runs automated Art QA validation on artifact",
                output_keys=["passed", "critical_errors"],
            ),
            "export_godot_spritesheet": ToolContract(
                name="export_godot_spritesheet",
                handler=_prod_export_godot_spritesheet,
                description="Exports packed spritesheet and Godot 4 SpriteFrames",
                output_keys=["sheet_png", "tres_file", "exported"],
            ),
            "export_pixilart_project": ToolContract(
                name="export_pixilart_project",
                handler=_prod_export_pixilart_project,
                description="Exports native Pixilart .pixil JSON project",
                output_keys=["saved_path", "exported"],
            ),
        }

    def dispatch(self, tool_name: str, params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        contract = self.contracts.get(tool_name)
        if not contract:
            raise ToolExecutionError(
                f"Production tool '{tool_name}' is not registered. Registered tools: {list(self.contracts.keys())}"
            )

        contract.validate_inputs(params)
        try:
            result = contract.handler(params, workspace)
            contract.validate_outputs(result)
            return result
        except Exception as ex:
            raise ToolExecutionError(f"Error executing production tool '{tool_name}': {ex}") from ex


class MockToolDispatcher(BaseToolDispatcher):
    """Simulated mock dispatcher strictly for unit testing without filesystem side effects."""

    def dispatch(self, tool_name: str, params: Dict[str, Any], workspace: Path) -> Dict[str, Any]:
        if tool_name == "generate_character":
            return {"project_path": "mock_char.aseprite", "character_id": params.get("character_id", "hero"), "frames": 2, "qa_passed": True}
        elif tool_name == "apply_outline":
            return {"project_path": "mock_char.aseprite", "outline_applied": True, "mode": params.get("mode", "colored"), "qa_passed": True}
        elif tool_name == "validate_asset":
            return {"passed": True, "critical_errors": [], "warnings": [], "ready_for_export": True}
        elif tool_name == "export_godot_spritesheet":
            return {"sheet_png": "mock_sheet.png", "tres_file": "mock.tres", "exported": True}
        elif tool_name == "export_pixilart_project":
            return {"saved_path": "mock.pixil", "format": "pixil", "exported": True}
        return {"status": "ok", "qa_passed": True}
