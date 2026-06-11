"""Explicit OpenAI-compatible config builders for standalone EasyPaper runs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .schema import (
    AgentConfig,
    AppConfig,
    CoreRefAnalysisConfig,
    DoclingConfig,
    ExemplarConfig,
    ModelConfig,
    ResearchContextConfig,
    SkillsConfig,
    ToolsConfig,
    VLMReviewConfig,
    VLMServiceConfig,
)

DEFAULT_LOCAL_AGENT_NAMES = ("metadata", "planner", "writer", "reviewer", "typesetter")
REDACTED_SECRET = "***REDACTED***"


def _require_nonempty(value: str | None, *, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required for standalone EasyPaper runs")
    return text


def _shared_model_config(*, model: str, base_url: str, api_key: str) -> ModelConfig:
    return ModelConfig(
        model_name=_require_nonempty(model, name="model"),
        base_url=_require_nonempty(base_url, name="base_url"),
        api_key=_require_nonempty(api_key, name="api_key"),
    )


def build_app_config(
    *,
    model: str,
    base_url: str,
    api_key: str,
    venue: str | None = None,
    enable_vlm: bool = False,
) -> AppConfig:
    """
    Build an explicit config for local OpenAI-compatible EasyPaper runs.

    The builder intentionally does not fall back to the schema default
    ``https://api.openai.com/v1``. Callers must pass a base URL or resolve one
    from their own environment first.
    """
    shared_model = _shared_model_config(model=model, base_url=base_url, api_key=api_key)
    tools = ToolsConfig(
        enabled=False,
        available_tools=[],
        max_react_iterations=0,
        planner_plan_review_enabled=False,
        table_critic_enabled=False,
        table_rendered_review_enabled=False,
        paper_search=None,
        research_context=ResearchContextConfig(enabled=False),
        core_ref_analysis=CoreRefAnalysisConfig(enabled=False),
        docling=DoclingConfig(enabled=False),
        exemplar=ExemplarConfig(enabled=False),
    )

    agents: list[AgentConfig] = []
    for name in DEFAULT_LOCAL_AGENT_NAMES:
        agents.append(
            AgentConfig(
                name=name,
                model=shared_model.model_copy(deep=True),
                tools_config=tools.model_copy(deep=True) if name in {"metadata", "writer"} else None,
            )
        )

    vlm_service = None
    if enable_vlm:
        vlm_service = VLMServiceConfig(
            enabled=True,
            provider="openai",
            model=shared_model.model_name,
            api_key=shared_model.api_key,
            base_url=shared_model.base_url,
        )
        agents.append(
            AgentConfig(
                name="vlm_review",
                model=shared_model.model_copy(deep=True),
                vlm_review_config=VLMReviewConfig(
                    enabled=True,
                    provider="openai",
                    vlm_model=shared_model.model_name,
                    vlm_api_key=shared_model.api_key,
                    vlm_base_url=shared_model.base_url,
                ),
            )
        )

    return AppConfig(
        agents=agents,
        tools=tools,
        skills=SkillsConfig(venue_profile=venue),
        vlm_service=vlm_service,
    )


def _redact_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if "api_key" in lowered or lowered.endswith("key"):
        return REDACTED_SECRET if value else value
    return value


def _redact_obj(value: Any, *, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: _redact_obj(_redact_value(k, v), key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_obj(item, key=key) for item in value]
    return _redact_value(key, value)


def redact_app_config(config: AppConfig) -> dict[str, Any]:
    """Return a JSON-serializable config dict with secrets redacted."""
    return _redact_obj(config.model_dump(mode="json"))


def write_redacted_app_config(config: AppConfig, output_path: str | Path) -> Path:
    """Persist a redacted YAML config for audit/debugging."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(redact_app_config(config), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
