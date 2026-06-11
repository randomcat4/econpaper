"""Tests for economics and finance venue profiles."""
from __future__ import annotations

from pathlib import Path

from src.skills.loader import SkillLoader
from src.skills.registry import SkillRegistry


ROOT = Path(__file__).resolve().parents[1]
VENUES_DIR = ROOT / "src" / "skills" / "builtin" / "venues"
REQUIRED_SECTIONS = [
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
]


def _load_venues():
    return SkillLoader().load_directory(VENUES_DIR)


def test_econ_finance_venue_configs_load() -> None:
    venues = {skill.name: skill for skill in _load_venues()}

    assert "american-economic-review" in venues
    assert "quarterly-journal-of-economics" in venues
    assert "journal-of-financial-economics" in venues


def test_econ_finance_required_sections_are_ordered() -> None:
    venues = {skill.name: skill for skill in _load_venues()}

    for name in (
        "american-economic-review",
        "quarterly-journal-of-economics",
        "journal-of-financial-economics",
    ):
        assert venues[name].venue_config["required_sections"] == REQUIRED_SECTIONS


def test_econ_finance_venue_specific_constraints() -> None:
    venues = {skill.name: skill for skill in _load_venues()}

    aer = venues["american-economic-review"].venue_config
    qje = venues["quarterly-journal-of-economics"].venue_config
    jfe = venues["journal-of-financial-economics"].venue_config

    assert aer["name"] == "american-economic-review"
    assert aer["abstract_limit"] == 100
    assert aer["page_limit"] == 40
    assert aer["field"] == "economics"

    assert qje["name"] == "quarterly-journal-of-economics"
    assert qje["abstract_limit"] == 250
    assert qje["require_total_word_count"] is True
    assert qje["field"] == "economics"

    assert jfe["name"] == "journal-of-financial-economics"
    assert jfe["abstract_limit"] == 100
    assert jfe["anonymous"] is True
    assert jfe["field"] == "finance"


def test_econ_finance_venues_are_discoverable_by_full_style_guide() -> None:
    registry = SkillRegistry()
    for skill in _load_venues():
        registry.register(skill)

    assert registry.get_venue_profile("american-economic-review").venue_config["name"] == (
        "american-economic-review"
    )
    assert registry.get_venue_profile("journal-of-financial-economics").venue_config["name"] == (
        "journal-of-financial-economics"
    )
