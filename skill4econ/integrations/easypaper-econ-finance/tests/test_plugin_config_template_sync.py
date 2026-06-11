from pathlib import Path

import yaml

from src.config.schema import AppConfig


ROOT = Path(__file__).resolve().parents[1]


def test_plugin_setup_skill_config_template_matches_example_config():
    canonical = (ROOT / "configs" / "example.yaml").read_text(encoding="utf-8")
    plugin_template = (
        ROOT
        / "plugins"
        / "easypaper"
        / "skills"
        / "easypaper-setup-environment"
        / "config.example.yaml"
    ).read_text(encoding="utf-8")

    assert plugin_template == canonical


def test_example_config_matches_current_schema_shape():
    raw = yaml.safe_load((ROOT / "configs" / "example.yaml").read_text(encoding="utf-8"))
    config = AppConfig(**raw)

    assert config.skills is not None
    assert config.skills.enabled is True
    assert config.tools is not None
    assert config.tools.enabled is True
    assert config.vlm_service is not None
    assert config.vlm_service.enabled is True


def test_setup_skill_mentions_synchronized_config_template():
    skill_text = (
        ROOT
        / "plugins"
        / "easypaper"
        / "skills"
        / "easypaper-setup-environment"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "config.example.yaml" in skill_text
    assert "easypaper_config.yaml" in skill_text
    assert "configs/example.yaml" in skill_text
