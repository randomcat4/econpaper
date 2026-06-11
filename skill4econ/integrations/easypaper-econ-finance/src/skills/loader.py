"""
Skill Loader
- **Description**:
    - Loads WritingSkill definitions from YAML files on disk
    - Recursively scans a skills directory for .yaml files
"""
import logging
from pathlib import Path
from typing import IO, Any, List, Optional

import yaml

from .models import WritingSkill

logger = logging.getLogger("uvicorn.error")


class SkillLoader:
    """
    Loads WritingSkill objects from YAML files.

    - **Methods**:
        - `load_directory()`: Recursively scan a directory and load all .yaml files
        - `load_single()`: Load a single YAML file into a WritingSkill
    """

    def load_directory(self, skills_dir: Path, *, warn_missing: bool = True) -> List[WritingSkill]:
        """
        Recursively load all .yaml files under *skills_dir*.

        - **Args**:
            - `skills_dir` (Path): Root directory to scan

        - **Returns**:
            - `List[WritingSkill]`: All successfully loaded skills
        """
        skills: List[WritingSkill] = []
        skills_path = Path(skills_dir)

        if not skills_path.exists():
            if warn_missing:
                logger.warning("skills.loader: directory not found: %s", skills_path)
            return skills

        for yaml_file in sorted(skills_path.rglob("*.yaml")):
            skill = self.load_single(yaml_file)
            if skill is not None:
                skills.append(skill)

        logger.info(
            "skills.loader: loaded %d skills from %s",
            len(skills),
            skills_path,
        )
        return skills

    def load_single(self, path: Path) -> Optional[WritingSkill]:
        """
        Load a single YAML file into a WritingSkill.

        - **Args**:
            - `path` (Path): Path to the .yaml file

        - **Returns**:
            - `WritingSkill` or None if loading fails
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                skill = self.load_stream(f, source=str(path))
            if skill is None:
                return None
            logger.debug("skills.loader: loaded skill '%s' from %s", skill.name, path)
            return skill

        except Exception as e:
            logger.warning("skills.loader: failed to load %s: %s", path, e)
            return None

    def load_stream(self, stream: IO[str], *, source: str) -> Optional[WritingSkill]:
        """
        Load a WritingSkill from an already-open text stream.

        Package-resource based built-ins do not always have a normal filesystem
        path, so the loader accepts streams in addition to Path objects.
        """
        try:
            data: Any = yaml.safe_load(stream)
            if not isinstance(data, dict):
                logger.warning("skills.loader: invalid YAML (not a dict): %s", source)
                return None
            return WritingSkill(**data)
        except Exception as e:
            logger.warning("skills.loader: failed to load %s: %s", source, e)
            return None
