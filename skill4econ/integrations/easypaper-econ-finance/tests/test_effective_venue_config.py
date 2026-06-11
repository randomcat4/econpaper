"""Tests for resolving economics and finance venue configs."""
from __future__ import annotations

from pathlib import Path

from src.agents.metadata_agent.metadata_agent import MetaDataAgent
from src.config.schema import ModelConfig
from src.skills.loader import SkillLoader
from src.skills.registry import SkillRegistry


ROOT = Path(__file__).resolve().parents[1]
VENUES_DIR = ROOT / "src" / "skills" / "builtin" / "venues"


def _agent() -> MetaDataAgent:
    return MetaDataAgent(ModelConfig(model_name="m", api_key="k", base_url="http://x"))


def test_effective_venue_config_resolves_aer_aliases() -> None:
    agent = _agent()

    assert agent._effective_venue_config(style_guide="aer")["name"] == (
        "american-economic-review"
    )
    assert agent._effective_venue_config(style_guide="AER")["name"] == (
        "american-economic-review"
    )
    assert agent._effective_venue_config(style_guide="American Economic Review")["name"] == (
        "american-economic-review"
    )


def test_effective_venue_config_resolves_qje_and_jfe() -> None:
    agent = _agent()

    assert agent._effective_venue_config(style_guide="qje")["name"] == (
        "quarterly-journal-of-economics"
    )
    assert agent._effective_venue_config(style_guide="journal-of-financial-economics")[
        "name"
    ] == "journal-of-financial-economics"


def test_effective_venue_config_prefers_venue_over_style_guide() -> None:
    agent = _agent()

    config = agent._effective_venue_config(
        style_guide="american-economic-review",
        venue="jfe",
    )

    assert config["name"] == "journal-of-financial-economics"


def test_effective_venue_config_uses_loaded_registry_when_available() -> None:
    agent = _agent()
    registry = SkillRegistry()
    for skill in SkillLoader().load_directory(VENUES_DIR):
        registry.register(skill)
    agent._skill_registry = registry

    assert agent._effective_venue_config(style_guide="american-economic-review")[
        "name"
    ] == "american-economic-review"


def test_effective_venue_config_returns_none_for_unknown_style() -> None:
    agent = _agent()

    assert agent._effective_venue_config(style_guide="unknown-style") is None
