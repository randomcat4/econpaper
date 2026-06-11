"""Tests for economics fields carried by planner requests."""
from __future__ import annotations

from src.agents.planner_agent.models import PlanRequest
from src.models.document_spec import GenerationConstraints


REQUIRED_SECTIONS = [
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
]


def _legacy_payload() -> dict:
    return {
        "title": "Legacy Paper",
        "idea_hypothesis": "Hypothesis.",
        "method": "Method.",
        "data": "Data.",
        "experiments": "Experiments.",
    }


def test_old_plan_request_payload_still_validates() -> None:
    request = PlanRequest.model_validate(_legacy_payload())

    assert request.title == "Legacy Paper"
    assert request.content_brief == {}
    assert request.constraints is None


def test_plan_request_accepts_content_brief_and_constraints_dict() -> None:
    payload = {
        **_legacy_payload(),
        "content_brief": {
            "empirical_strategy": "Difference-in-differences.",
            "results": "Positive pass-through.",
            "robustness": "Placebo policy dates.",
        },
        "constraints": {
            "style_guide": "american-economic-review",
            "required_sections": REQUIRED_SECTIONS,
            "citation_format": "bibtex",
        },
    }

    request = PlanRequest.model_validate(payload)

    assert request.content_brief["empirical_strategy"] == "Difference-in-differences."
    assert request.content_brief["results"] == "Positive pass-through."
    assert request.content_brief["robustness"] == "Placebo policy dates."
    assert request.constraints.required_sections == REQUIRED_SECTIONS
    assert request.constraints.style_guide == "american-economic-review"


def test_plan_request_accepts_generation_constraints_model() -> None:
    constraints = GenerationConstraints(
        style_guide="journal-of-financial-economics",
        required_sections=REQUIRED_SECTIONS,
    )

    request = PlanRequest(
        **_legacy_payload(),
        content_brief={"empirical_strategy": "Bank exposure design."},
        constraints=constraints,
    )

    assert request.constraints.required_sections == REQUIRED_SECTIONS
    assert request.constraints.style_guide == "journal-of-financial-economics"


def test_content_brief_default_is_not_shared_between_requests() -> None:
    first = PlanRequest(**_legacy_payload())
    second = PlanRequest(**_legacy_payload())

    first.content_brief["results"] = "Only first request."

    assert second.content_brief == {}
