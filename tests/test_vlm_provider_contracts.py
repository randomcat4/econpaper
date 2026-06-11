from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


EASYPAPER_ROOT = Path(__file__).resolve().parents[1] / "EasyPaper"
if str(EASYPAPER_ROOT) not in sys.path:
    sys.path.insert(0, str(EASYPAPER_ROOT))


def test_vlm_service_uses_empty_key_for_openai_compatible_local_endpoint(monkeypatch) -> None:
    from src.agents.shared.vlm_service import VLMService
    from src.agents.vlm_review_agent.providers.base import VLMFactory

    captured: dict[str, object] = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(VLMFactory, "create", fake_create)

    service = VLMService(provider="openai", base_url="http://localhost:8000/v1", model="local-vlm")
    service._get_provider()

    assert captured["provider"] == "openai"
    assert captured["api_key"] == "EMPTY"
    assert captured["base_url"] == "http://localhost:8000/v1"
    assert captured["model"] == "local-vlm"


def test_vlm_service_fails_fast_without_key_for_hosted_openai() -> None:
    from src.agents.shared.vlm_service import VLMService

    service = VLMService(provider="openai")

    with pytest.raises(ValueError, match="API key required"):
        service._get_provider()


@pytest.mark.asyncio
async def test_claude_vlm_sends_required_message_parameters(monkeypatch) -> None:
    from src.agents.vlm_review_agent.providers.claude_vlm import ClaudeVLM

    captured: dict[str, object] = {}

    class _Messages:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[SimpleNamespace(text='{"semantic_role":"main_results"}')],
                usage=SimpleNamespace(input_tokens=5, output_tokens=7),
            )

    class _AsyncAnthropic:
        def __init__(self, api_key: str):
            self.api_key = api_key
            self.messages = _Messages()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=_AsyncAnthropic))

    provider = ClaudeVLM(api_key="secret", model="claude-test")
    response = await provider.analyze_page(b"\x89PNG\r\n\x1a\nfake", "Analyze this.")

    assert response.success is True
    assert captured["model"] == "claude-test"
    assert captured["max_tokens"] == 1024
    assert captured["temperature"] == 0.1
    assert captured["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    assert response.tokens_used == 12


def test_claude_vlm_requires_api_key(monkeypatch) -> None:
    from src.agents.vlm_review_agent.providers.claude_vlm import ClaudeVLM

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=object))

    with pytest.raises(ValueError, match="requires an Anthropic API key"):
        ClaudeVLM(api_key="")
