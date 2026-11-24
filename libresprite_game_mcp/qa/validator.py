"""
Automated Art QA Validation Engine for Pixel Art Assets.
Performs objective checks on palette compliance, alpha hygiene, dimensions, and animation alignment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image

from libresprite_game_mcp.core.palettes import (
    GamePalette,
    RGBA,
    rgba_to_hex,
    BUILTIN_PALETTES,
)
from libresprite_game_mcp.core.aseprite_file import AsepriteProject
from libresprite_game_mcp.models.schemas import ValidationReport, ValidationCheck


class AssetValidator:
    """Performs rigorous automated art quality assurance on pixel art assets."""

    def __init__(self, palette: Optional[GamePalette] = None, expected_size: Optional[Tuple[int, int]] = None):
        self.palette = palette
        self.expected_size = expected_size

    def validate_image(self, img: Image.Image, asset_name: str = "asset") -> ValidationReport:
        """Validates a single Pillow image against palette, size, and alpha rules."""
        rgba = img.convert("RGBA")
        width, height = rgba.size
        pixels = rgba.load()

        critical_errors: List[str] = []
        warnings: List[str] = []
        checks: Dict[str, ValidationCheck] = {}

        # 1. Dimension Check
        dim_passed = True
        dim_details = {"actual": [width, height]}
        if self.expected_size:
            dim_details["expected"] = list(self.expected_size)
            if (width, height) != self.expected_size:
                dim_passed = False
                critical_errors.append(
                    f"Dimension mismatch: expected {self.expected_size[0]}x{self.expected_size[1]}, got {width}x{height}"
                )
        checks["dimensions"] = ValidationCheck(passed=dim_passed, details=dim_details)

        # 2. Alpha Hygiene (no translucent border pixels: 0 < alpha < 255)
        translucent_count = 0
        translucent_coords = []
        for y in range(height):
            for x in range(width):
                _, _, _, a = pixels[x, y]
                if 0 < a < 255:
                    translucent_count += 1
                    if len(translucent_coords) < 5:
                        translucent_coords.append((x, y))

        alpha_passed = (translucent_count == 0)
        if not alpha_passed:
            critical_errors.append(
                f"Alpha hygiene violation: found {translucent_count} semi-transparent pixels (samples: {translucent_coords}). Game sprites require binary 0 or 255 alpha."
            )
        checks["alpha_hygiene"] = ValidationCheck(
            passed=alpha_passed,
            details={"semi_transparent_pixel_count": translucent_count, "sample_coords": translucent_coords}
        )

        # 3. Palette Adherence Check
        unique_colors = set()
        unauthorized_colors = set()
        palette_hex_set = set(self.palette.to_hex_list()) if self.palette else None

        for y in range(height):
            for x in range(width):
                r, g, b, a = pixels[x, y]
                if a > 0:
                    hex_code = rgba_to_hex((r, g, b, a))
                    unique_colors.add(hex_code)
                    if palette_hex_set and hex_code not in palette_hex_set:
                        unauthorized_colors.add(hex_code)

        palette_passed = (len(unauthorized_colors) == 0)
        if not palette_passed:
            critical_errors.append(
                f"Palette adherence failure: found {len(unauthorized_colors)} unauthorized colors not in '{self.palette.name}' palette: {list(unauthorized_colors)[:6]}"
            )
        checks["palette_adherence"] = ValidationCheck(
            passed=palette_passed,
            details={
                "unique_colors_used": len(unique_colors),
                "unauthorized_colors": list(unauthorized_colors),
                "palette_name": self.palette.name if self.palette else "unspecified",
            }
        )

        overall_passed = len(critical_errors) == 0
        return ValidationReport(
            asset_name=asset_name,
            passed=overall_passed,
            checks=checks,
            critical_errors=critical_errors,
            warnings=warnings,
            ready_for_export=overall_passed,
        )

    def validate_project(self, project: AsepriteProject, asset_name: str = "project") -> ValidationReport:
        """Validates all frames and layer consistency of an AsepriteProject."""
        frames = project.get_all_frame_images()
        if not frames:
            return ValidationReport(
                asset_name=asset_name,
                passed=False,
                critical_errors=["Project contains 0 animation frames."],
                ready_for_export=False,
            )

        # Base check on first frame
        base_report = self.validate_image(frames[0], asset_name=f"{asset_name}_f0")
        critical_errors = list(base_report.critical_errors)
        warnings = list(base_report.warnings)
        checks = dict(base_report.checks)

        # Animation Foot Alignment Check across frames
        foot_baselines = []
        for f_idx, f_img in enumerate(frames):
            rgba = f_img.convert("RGBA")
            pixels = rgba.load()
            max_y = 0
            found = False
            for y in range(rgba.height):
                for x in range(rgba.width):
                    if pixels[x, y][3] > 0:
                        max_y = max(max_y, y)
                        found = True
            if found:
                foot_baselines.append(max_y)

        alignment_passed = True
        baseline_drift = 0
        if foot_baselines:
            baseline_drift = max(foot_baselines) - min(foot_baselines)
            # Drift > 2 pixels indicates foot slipping or unanchored baseline
            if baseline_drift > 2:
                warnings.append(
                    f"Animation foot baseline drift of {baseline_drift}px detected across frames (min y={min(foot_baselines)}, max y={max(foot_baselines)})."
                )

        checks["animation_alignment"] = ValidationCheck(
            passed=alignment_passed,
            details={"foot_baselines": foot_baselines, "max_drift_px": baseline_drift}
        )

        # Check for orphan layers
        orphan_layers = [l for l in project.layers if l == "Layer 1" and len(project.layers) > 1]
        if orphan_layers:
            warnings.append("Project contains untouched default 'Layer 1'.")

        overall_passed = len(critical_errors) == 0
        return ValidationReport(
            asset_name=asset_name,
            passed=overall_passed,
            checks=checks,
            critical_errors=critical_errors,
            warnings=warnings,
            ready_for_export=overall_passed,
        )
