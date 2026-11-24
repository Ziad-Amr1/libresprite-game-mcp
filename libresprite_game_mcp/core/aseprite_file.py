"""
Native .ase and .aseprite file reader/writer using aseprite-py and Pillow.
Allows creating, reading, and modifying multi-layer, multi-frame, tagged animations
with zero dependency on GUI or background processes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from PIL import Image

import aseprite
from libresprite_game_mcp.core.palettes import GamePalette, RGBA


class AsepriteProject:
    """High-level abstraction for constructing and manipulating .ase/.aseprite files."""

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.sprite = aseprite.Sprite(width, height)
        # Track layers; initial layer is created by Sprite constructor as "Layer 1"
        self._initial_layer_renamed = False
        self.layers: Dict[str, aseprite.Layer] = {self.sprite.layers[0].name: self.sprite.layers[0]}
        self.tags: Dict[str, Tuple[int, int]] = {}
        self.metadata: Dict[str, Any] = {}

    @classmethod
    def load(cls, file_path: Union[str, Path]) -> "AsepriteProject":
        """Loads an existing .ase or .aseprite file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        sprite = aseprite.Sprite.open(str(path))
        proj = cls(sprite.size[0], sprite.size[1])
        proj.sprite = sprite
        proj.layers = {layer.name: layer for layer in sprite.layers}
        proj._initial_layer_renamed = True
        return proj

    def set_layer_name(self, old_name: str, new_name: str) -> None:
        if old_name in self.layers:
            layer = self.layers.pop(old_name)
            layer.name = new_name
            self.layers[new_name] = layer
            self._initial_layer_renamed = True

    def add_layer(self, name: str, opacity: int = 255) -> aseprite.Layer:
        """Adds a new raster image layer or adopts the default layer if untouched."""
        if name in self.layers:
            return self.layers[name]

        # Prevent empty orphan 'Layer 1'
        if not self._initial_layer_renamed and "Layer 1" in self.layers:
            layer = self.layers.pop("Layer 1")
            layer.name = name
            layer.opacity = opacity
            self.layers[name] = layer
            self._initial_layer_renamed = True
            return layer

        layer = self.sprite.add_layer(name, opacity=opacity)
        self.layers[name] = layer
        return layer

    def add_animation_frame(
        self,
        duration_ms: int = 100,
        layer_images: Optional[Dict[str, Image.Image]] = None
    ) -> int:
        """
        Adds a new frame to the animation.
        If layer_images is provided, sets each layer's pixels from a Pillow Image.
        Returns the new frame index.
        """
        frame_idx = len(self.sprite.frames)
        # If frame 0 is empty, populate frame 0; otherwise add_frame
        if frame_idx == 1 and not hasattr(self, "_frame_0_initialized"):
            frame = self.sprite.frames[0]
            frame.duration_ms = duration_ms
            self._frame_0_initialized = True
            frame_idx = 0
        else:
            frame = self.sprite.add_frame(duration_ms=duration_ms)

        if layer_images:
            for layer_name, img in layer_images.items():
                self.set_frame_image(frame_idx, layer_name, img)

        return frame_idx

    def set_frame_image(self, frame_idx: int, layer_name: str, img: Image.Image) -> None:
        """Sets the pixel content of a specific frame and layer from a Pillow Image."""
        if frame_idx >= len(self.sprite.frames):
            raise IndexError(f"Frame index {frame_idx} out of range (total {len(self.sprite.frames)})")

        layer = self.add_layer(layer_name)
        frame = self.sprite.frames[frame_idx]

        # Ensure image is in RGBA and matches canvas dimensions
        rgba_img = img.convert("RGBA")
        if rgba_img.size != (self.width, self.height):
            rgba_img = rgba_img.resize((self.width, self.height), Image.Resampling.NEAREST)

        pixels = self.sprite.blank_pixels()
        width, height = self.width, self.height

        # Load pixels into aseprite buffer
        img_data = rgba_img.load()
        for y in range(height):
            for x in range(width):
                r, g, b, a = img_data[x, y]
                if a > 0:
                    pixels[x, y] = (r, g, b, a)

        frame[layer] = pixels

    def add_tag(self, name: str, from_frame: int, to_frame: int) -> None:
        """Adds an animation tag (e.g. 'idle', 'walk', 'attack')."""
        self.sprite.add_tag(name, from_frame, to_frame)
        self.tags[name] = (from_frame, to_frame)

    def get_frame_image(self, frame_idx: int = 0, layer_name: Optional[str] = None) -> Image.Image:
        """Renders and returns a Pillow Image for the given frame (optionally isolated to layer_name)."""
        if layer_name and layer_name in self.layers:
            layer = self.layers[layer_name]
            frame = self.sprite.frames[frame_idx]
            try:
                cel = frame[layer]
                if cel and hasattr(cel, "pixels") and cel.pixels:
                    return Image.frombytes("RGBA", (cel.pixels.width, cel.pixels.height), bytes(cel.pixels.data))
            except KeyError:
                pass
            return Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        return self.sprite.image(frame_idx)

    def get_all_frame_images(self) -> List[Image.Image]:
        """Renders and returns composited Pillow Images for all frames."""
        return [self.sprite.image(i) for i in range(len(self.sprite.frames))]

    def get_info(self) -> Dict:
        """Returns metadata about the sprite project."""
        tag_list = []
        for t in self.sprite.tags:
            tag_list.append({
                "name": t.name,
                "from": t.from_frame,
                "to": t.to_frame,
            })
        return {
            "width": self.width,
            "height": self.height,
            "frame_count": len(self.sprite.frames),
            "layers": [l.name for l in self.sprite.layers],
            "tags": tag_list,
        }

    def save(self, file_path: Union[str, Path]) -> Path:
        """Saves the project to .ase or .aseprite file."""
        out = Path(file_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self.sprite.save(str(out))
        return out
