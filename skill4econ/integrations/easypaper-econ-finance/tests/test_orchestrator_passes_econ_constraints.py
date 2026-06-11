"""Tests for passing econ DocumentInput fields into planner requests."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.agents.metadata_agent.models import PaperMetaData
from src.agents.metadata_agent.orchestrator import ReviewOrchestrator


REQUIRED_SECTIONS = [
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
]


def _venue_config() -> dict:
    return {
        "name": "american-economic-review",
        "page_limit": 40,
        "required_sections": REQUIRED_SECTIONS,
    }


@pytest.mark.asyncio
async def test_create_paper_plan_passes_econ_content_brief_and_constraints() -> None:
    planner = SimpleNamespace(create_plan=AsyncMock(return_value="paper-plan"))
    host = SimpleNamespace(
        _planner=planner,
        _effective_venue_config=lambda **_: _venue_config(),
    )
    orchestrator = ReviewOrchestrator(host)
    metadata = PaperMetaData(
        title="Minimum Wage Pass-Through and Local Employment",
        idea_hypothesis="Minimum wage changes affect prices and employment.",
        method="Legacy DiD method.",
        data="County-year panel data.",
        experiments="Legacy experiment summary.",
        venue="american-economic-review",
        empirical_strategy="Difference-in-differences with county and year fixed effects.",
        results="Positive pass-through and imprecise employment effects.",
        robustness="Alternative control groups and placebo policy dates.",
    )

    result = await orchestrator._create_paper_plan(
        metadata=metadata,
        target_pages=None,
        style_guide=None,
    )

    assert result == "paper-plan"
    request = planner.create_plan.await_args.args[0]
    assert request.content_brief["empirical_strategy"] == metadata.empirical_strategy
    assert request.content_brief["results"] == metadata.results
    assert request.content_brief["robustness"] == metadata.robustness
    assert request.constraints.required_sections == REQUIRED_SECTIONS
    assert request.target_pages == 40
    assert request.style_guide == "american-economic-review"


@pytest.mark.asyncio
async def test_create_paper_plan_preserves_legacy_request_without_venue_config() -> None:
    planner = SimpleNamespace(create_plan=AsyncMock(return_value="paper-plan"))
    host = SimpleNamespace(
        _planner=planner,
        _effective_venue_config=lambda **_: None,
    )
    orchestrator = ReviewOrchestrator(host)
    metadata = PaperMetaData(
        title="Legacy ML Paper",
        idea_hypothesis="A model improves accuracy.",
        method="A transformer method.",
        data="Benchmark datasets.",
        experiments="Ablations and comparisons.",
    )

    result = await orchestrator._create_paper_plan(
        metadata=metadata,
        target_pages=8,
        style_guide="NeurIPS",
    )

    assert result == "paper-plan"
    request = planner.create_plan.await_args.args[0]
    assert request.method == "A transformer method."
    assert request.experiments == "Ablations and comparisons."
    assert request.content_brief["method"] == "A transformer method."
    assert request.content_brief["experiments"] == "Ablations and comparisons."
    assert request.constraints.required_sections == []
    assert request.target_pages == 8
    assert request.style_guide == "NeurIPS"
