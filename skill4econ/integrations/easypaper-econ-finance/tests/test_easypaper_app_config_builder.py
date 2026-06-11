"""Tests for standalone OpenAI-compatible EasyPaper config construction."""
from __future__ import annotations

import yaml

from src.config.easypaper_config import (
    REDACTED_SECRET,
    build_app_config,
    redact_app_config,
    write_redacted_app_config,
)


def _agent_base_urls(config):
    return [
        agent.model.base_url
        for agent in config.agents
        if agent.model is not None
    ]


def test_build_app_config_sets_all_agent_base_urls():
    config = build_app_config(
        model="kimi-k2",
        base_url="https://api.moonshot.ai/v1",
        api_key="secret-key",
        venue="american-economic-review",
    )

    assert set(_agent_base_urls(config)) == {"https://api.moonshot.ai/v1"}
    assert {agent.name for agent in config.agents} == {
        "metadata",
        "planner",
        "writer",
        "reviewer",
        "typesetter",
    }
    assert config.skills.venue_profile == "american-economic-review"


def test_redacted_config_never_contains_api_key(tmp_path):
    config = build_app_config(
        model="kimi-k2",
        base_url="https://api.moonshot.ai/v1",
        api_key="secret-key",
        venue="journal-of-financial-economics",
    )

    redacted = redact_app_config(config)
    text = yaml.safe_dump(redacted)

    assert "secret-key" not in text
    assert REDACTED_SECRET in text

    path = write_redacted_app_config(config, tmp_path / "config.redacted.yaml")
    saved = path.read_text(encoding="utf-8")
    assert "secret-key" not in saved
    assert REDACTED_SECRET in saved


def test_enable_vlm_false_does_not_construct_vlm_or_anthropic_provider():
    config = build_app_config(
        model="kimi-k2",
        base_url="https://api.moonshot.ai/v1",
        api_key="secret-key",
        enable_vlm=False,
    )
    redacted = redact_app_config(config)
    text = yaml.safe_dump(redacted).lower()

    assert config.vlm_service is None
    assert "vlm_review" not in {agent.name for agent in config.agents}
    assert "anthropic" not in text
    assert "claude" not in text


def test_enable_vlm_true_uses_same_openai_compatible_endpoint():
    config = build_app_config(
        model="kimi-k2",
        base_url="https://api.moonshot.ai/v1",
        api_key="secret-key",
        enable_vlm=True,
    )

    assert config.vlm_service is not None
    assert config.vlm_service.provider == "openai"
    assert config.vlm_service.base_url == "https://api.moonshot.ai/v1"
    vlm_agent = next(agent for agent in config.agents if agent.name == "vlm_review")
    assert vlm_agent.vlm_review_config.provider == "openai"
    assert vlm_agent.vlm_review_config.vlm_base_url == "https://api.moonshot.ai/v1"
