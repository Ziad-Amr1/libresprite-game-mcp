"""
Skill Registry.
Provides storage, lookup, matching, and filesystem synchronization for versioned skills.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from libresprite_game_mcp.skills.models import SkillDefinition, SkillStatus
from libresprite_game_mcp.skills.repository import SkillRepository

DEFAULT_SKILLS_DIR = Path("data/skills")


class SkillRegistry:
    """Central registry for discovering, retrieving, and serializing Skills."""

    def __init__(self, repository: SkillRepository, skills_dir: Optional[Path] = None):
        self.repository = repository
        self.skills_dir = skills_dir or DEFAULT_SKILLS_DIR
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def register_skill(self, skill: SkillDefinition, sync_fs: bool = True, force: bool = False) -> SkillDefinition:
        """Registers a skill definition in the repository and optionally saves to disk."""
        saved = self.repository.save_skill_definition(skill, force=force)
        if sync_fs:
            self.export_to_filesystem(saved)
        return saved

    def get_skill(
        self,
        skill_id: str,
        version: Optional[str] = None,
        allow_unapproved: bool = False,
    ) -> Optional[SkillDefinition]:
        """
        Retrieves a skill.
        If version is None, retrieves latest APPROVED version (or latest unapproved if allow_unapproved=True).
        In production, only APPROVED skills are returned unless allow_unapproved is True (e.g. during testing/sandbox).
        """
        if version:
            skill = self.repository.get_skill_version(skill_id, version)
            if not skill:
                return None
            if not allow_unapproved and skill.status != SkillStatus.APPROVED:
                return None
            return skill

        if not allow_unapproved:
            return self.repository.get_latest_approved_skill(skill_id)

        # Allow unapproved: return highest semver version available
        versions = self.repository.list_versions_for_skill(skill_id)
        return versions[0] if versions else None

    def find_matching_skills(
        self,
        context: Dict[str, Any],
        art_profile_name: Optional[str] = None,
        allow_unapproved: bool = False,
    ) -> List[SkillDefinition]:
        """
        Finds skills whose trigger_conditions match the task context.
        """
        all_skills = self.repository.list_skills(status=None if allow_unapproved else SkillStatus.APPROVED)
        matches: List[SkillDefinition] = []

        for skill in all_skills:
            # Check art profile compatibility if defined
            if art_profile_name and skill.art_profile_compatibility:
                if art_profile_name not in skill.art_profile_compatibility:
                    continue

            # Match trigger conditions
            conds = skill.trigger_conditions
            match = True
            for k, expected_v in conds.items():
                if k not in context:
                    match = False
                    break
                actual_v = context[k]
                if isinstance(expected_v, list):
                    if actual_v not in expected_v:
                        match = False
                        break
                elif actual_v != expected_v:
                    match = False
                    break

            if match:
                matches.append(skill)

        return matches

    def export_to_filesystem(self, skill: SkillDefinition) -> Path:
        """Saves a skill definition as a versioned JSON artifact atomically."""
        target_dir = self.skills_dir / skill.skill_id / skill.version
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = target_dir / "skill.json"
        tmp_file = target_dir / "skill.json.tmp"

        with open(tmp_file, "w", encoding="utf-8") as f:
            f.write(skill.model_dump_json(indent=2))

        import os
        os.replace(tmp_file, manifest_file)
        return manifest_file

    def import_from_filesystem(self, manifest_file: Path, force: bool = False) -> SkillDefinition:
        """Loads and registers a skill definition from a JSON manifest file."""
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        skill = SkillDefinition.model_validate(data)
        return self.register_skill(skill, sync_fs=False, force=force)
