"""Shared skills bootstrap for SDK and server entry points."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from src.config.schema import SkillsConfig

from .loader import SkillLoader
from .models import WritingSkill
from .registry import SkillRegistry

logger = logging.getLogger("uvicorn.error")

_BUILTIN_PACKAGE = "src.skills.builtin"


@dataclass(frozen=True)
class SkillLoadReport:
    """Structured, stable reporting for skills loaded at startup."""

    enabled: bool
    built_in_count: int = 0
    user_count: int = 0
    overridden_names: List[str] = field(default_factory=list)
    final_skill_names: List[str] = field(default_factory=list)
    source_kind_by_skill: Dict[str, str] = field(default_factory=dict)
    user_dir: Optional[str] = None
    user_dir_exists: bool = False

    @property
    def registry_size(self) -> int:
        return len(self.final_skill_names)


def _iter_yaml_resources(root: Traversable) -> Iterable[Traversable]:
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.is_dir():
            yield from _iter_yaml_resources(child)
        elif child.name.endswith((".yaml", ".yml")):
            yield child


def load_builtin_skills(loader: Optional[SkillLoader] = None) -> List[WritingSkill]:
    """Load packaged built-in skills from importable package resources."""
    loader = loader or SkillLoader()
    try:
        root = resources.files(_BUILTIN_PACKAGE)
    except ModuleNotFoundError:
        logger.warning("skills.bootstrap: built-in skills package not found")
        return []

    skills: List[WritingSkill] = []
    for resource in _iter_yaml_resources(root):
        try:
            with resource.open("r", encoding="utf-8") as handle:
                skill = loader.load_stream(handle, source=str(resource))
            if skill is not None:
                skills.append(skill)
        except Exception as exc:  # pragma: no cover - defensive resource boundary
            logger.warning("skills.bootstrap: failed to load built-in %s: %s", resource, exc)
    return skills


def bootstrap_skill_registry(
    skills_config: SkillsConfig,
) -> Tuple[SkillRegistry, SkillLoadReport]:
    """
    Build a merged skill registry from packaged built-ins and user skills.

    Built-ins are registered first. User skills from ``skills_dir`` are
    registered second, so same-name user skills override packaged defaults.
    """
    registry = SkillRegistry()
    if not skills_config.enabled:
        return registry, SkillLoadReport(enabled=False)

    loader = SkillLoader()
    source_kind_by_skill: Dict[str, str] = {}
    overridden_names: List[str] = []

    builtins = load_builtin_skills(loader)
    for skill in builtins:
        registry.register(skill)
        source_kind_by_skill[skill.name] = "builtin"

    user_dir = Path(skills_config.skills_dir)
    user_dir_exists = user_dir.exists()
    user_skills = loader.load_directory(user_dir, warn_missing=False)
    for skill in user_skills:
        if skill.name in source_kind_by_skill:
            overridden_names.append(skill.name)
        registry.register(skill)
        source_kind_by_skill[skill.name] = "user_dir"

    final_names = sorted(skill.name for skill in registry)
    report = SkillLoadReport(
        enabled=True,
        built_in_count=len(builtins),
        user_count=len(user_skills),
        overridden_names=sorted(set(overridden_names)),
        final_skill_names=final_names,
        source_kind_by_skill={name: source_kind_by_skill[name] for name in final_names},
        user_dir=str(user_dir),
        user_dir_exists=user_dir_exists,
    )
    logger.info(
        "skills.bootstrap: loaded %d built-in, %d user, %d final skills",
        report.built_in_count,
        report.user_count,
        report.registry_size,
    )
    return registry, report


def bootstrap_skill_registry_for_config(
    skills_config: Optional[SkillsConfig],
) -> Tuple[Optional[SkillRegistry], SkillsConfig, SkillLoadReport]:
    """
    Normalize skills config and bootstrap with fail-open entrypoint semantics.

    SDK and FastAPI both call this wrapper so ``skills: null`` and bootstrap
    failures behave identically in every entry point.
    """
    normalized = skills_config or SkillsConfig()
    if not normalized.enabled:
        return None, normalized, SkillLoadReport(enabled=False)

    try:
        registry, report = bootstrap_skill_registry(normalized)
        return registry, normalized, report
    except Exception as exc:
        logger.warning("Skills loading failed; continuing without skills: %s", exc)
        return None, normalized, SkillLoadReport(enabled=False)


def format_skill_load_report(report: SkillLoadReport) -> str:
    """Render a stable user-visible summary for SDK/server startup logs."""
    if not report.enabled:
        return "Skills system disabled"
    names = ", ".join(report.final_skill_names) if report.final_skill_names else "(none)"
    parts = [
        f"Loaded built-in skills: {report.built_in_count}",
        f"user skills: {report.user_count}",
        f"final skills: {report.registry_size}",
        f"names: {names}",
    ]
    if report.overridden_names:
        parts.append(f"user overrides: {', '.join(report.overridden_names)}")
    if report.user_dir and not report.user_dir_exists:
        parts.append(f"user skills_dir missing: {report.user_dir}")
    return "; ".join(parts)
