"""
Experience Normalizer.
Standardizes task contexts, sanitizes sensitive tokens, and extracts tags.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


class ExperienceNormalizer:
    """Normalizes experiences and scrubs sensitive credentials."""

    SENSITIVE_KEYS = {"session_token", "token", "password", "secret", "auth", "api_key", "authorization"}

    def sanitize_payload(self, payload: Any) -> Any:
        """Recursively masks sensitive tokens and credentials."""
        if isinstance(payload, dict):
            sanitized = {}
            for k, v in payload.items():
                if any(sens in k.lower() for sens in self.SENSITIVE_KEYS):
                    sanitized[k] = "[MASKED]"
                else:
                    sanitized[k] = self.sanitize_payload(v)
            return sanitized
        elif isinstance(payload, list):
            return [self.sanitize_payload(item) for item in payload]
        elif isinstance(payload, str):
            # Check for potential bearer tokens or 32+ hex strings
            if len(payload) == 64 and re.match(r"^[0-9a-fA-F]+$", payload):
                return "[MASKED_TOKEN]"
            return payload
        return payload

    def extract_resolution(self, context: Dict[str, Any]) -> Tuple[int, int]:
        """Extracts canonical resolution (width, height) from various context formats."""
        if "resolution" in context:
            res = context["resolution"]
            if isinstance(res, (tuple, list)) and len(res) >= 2:
                return int(res[0]), int(res[1])
            if isinstance(res, str) and "x" in res:
                parts = res.lower().split("x")
                return int(parts[0]), int(parts[1])

        if "size" in context:
            size = context["size"]
            if isinstance(size, (tuple, list)) and len(size) >= 2:
                return int(size[0]), int(size[1])

        if "dimensions" in context:
            dim = context["dimensions"]
            if isinstance(dim, (tuple, list)) and len(dim) >= 2:
                return int(dim[0]), int(dim[1])

        return (16, 16)

    def extract_tags(
        self,
        task_category: str,
        asset_category: str,
        resolution: Tuple[int, int],
        art_profile: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[str]:
        """Generates deterministic, standardized search tags."""
        tags: Set[str] = set()

        tags.add(task_category.lower())
        tags.add(asset_category.lower())
        tags.add(f"{resolution[0]}x{resolution[1]}")

        # Art profile hints
        if "palette_name" in art_profile:
            tags.add(f"palette:{art_profile['palette_name']}")
        if "perspective" in art_profile:
            tags.add(f"perspective:{art_profile['perspective']}")
        if "engine" in art_profile:
            tags.add(f"engine:{art_profile['engine']}")

        # Character blueprint hints
        if "proportion" in context:
            tags.add(f"proportion:{context['proportion']}")
        if "theme_name" in context:
            tags.add(f"theme:{context['theme_name']}")
        if "category" in context:
            tags.add(f"item:{context['category']}")

        return sorted(list(tags))
