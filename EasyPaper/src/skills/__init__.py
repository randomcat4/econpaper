"""
Skills System for EasyPaper
- **Description**:
    - Provides pluggable writing constraints, reviewer rules, and venue profiles
    - Skills are loaded from YAML files and registered in a global registry
    - The PromptCompiler and ReviewerAgent consume skills at runtime
"""
from .models import WritingSkill
from .loader import SkillLoader
from .registry import SkillRegistry
from .bootstrap import (
    SkillLoadReport,
    bootstrap_skill_registry,
    bootstrap_skill_registry_for_config,
    format_skill_load_report,
)

__all__ = [
    "WritingSkill",
    "SkillLoader",
    "SkillRegistry",
    "SkillLoadReport",
    "bootstrap_skill_registry",
    "bootstrap_skill_registry_for_config",
    "format_skill_load_report",
]
