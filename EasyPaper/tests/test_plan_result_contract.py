import json

import pytest
from pydantic import ValidationError

from src.agents.metadata_agent.models import PlanResult as MetadataPlanResult
from src.agents.planner_agent.models import PlanResult as PlannerPlanResult


def _full_plan_result() -> MetadataPlanResult:
    return MetadataPlanResult(
        paper_plan={"title": "Paper", "sections": [{"section_type": "introduction"}]},
        evidence_dag={"evidence_nodes": {}, "claim_nodes": {}, "binding_edges": {}},
        research_context={"topic": "metadata cleanup"},
        code_context={"files": ["src/agents/metadata_agent/models.py"]},
        code_summary_markdown="# Summary",
        ref_pool_snapshot={"core_refs": [], "discovered_refs": []},
        converted_tables={"tab:one": "\\begin{table}"},
        metadata_input={
            "title": "Paper",
            "idea_hypothesis": "h",
            "method": "m",
            "data": "d",
            "experiments": "e",
        },
        errors=["non-fatal"],
        warnings=["warning"],
        template_path="/tmp/template.zip",
        target_pages=8,
        exemplar_analysis={"title": "Example"},
        artifacts_prefix="prefix",
        paper_dir="/tmp/paper",
        plan_review={"verdict": "APPROVE"},
        plan_review_iterations=[{"iteration": 1}],
        figure_supplementation_trace={"added": []},
    )


def test_metadata_plan_result_json_roundtrip_preserves_execution_fields():
    plan = _full_plan_result()

    restored = MetadataPlanResult.model_validate(json.loads(json.dumps(plan.model_dump(mode="json"))))

    for field in (
        "paper_plan",
        "ref_pool_snapshot",
        "converted_tables",
        "metadata_input",
        "template_path",
        "target_pages",
        "exemplar_analysis",
        "artifacts_prefix",
        "paper_dir",
        "plan_review",
        "plan_review_iterations",
        "figure_supplementation_trace",
        "errors",
        "warnings",
        "evidence_dag",
        "research_context",
        "code_context",
        "code_summary_markdown",
    ):
        assert getattr(restored, field) == getattr(plan, field)


def test_metadata_plan_result_rejects_missing_paper_plan():
    with pytest.raises(ValidationError):
        MetadataPlanResult.model_validate({"metadata_input": {"title": "x"}})


@pytest.mark.parametrize(
    "payload",
    [
        {"paper_plan": "not-a-dict"},
        {"paper_plan": {"sections": []}, "ref_pool_snapshot": "not-a-dict"},
        {"paper_plan": {"sections": []}, "metadata_input": "not-a-dict"},
        {"paper_plan": {"sections": []}, "errors": "not-a-list"},
        {"paper_plan": {}, "errors": []},
    ],
)
def test_metadata_plan_result_rejects_malformed_payloads(payload):
    with pytest.raises(ValidationError):
        MetadataPlanResult.model_validate(payload)


def test_metadata_plan_result_allows_empty_plan_only_with_errors():
    plan = MetadataPlanResult(
        paper_plan={},
        metadata_input={"title": "x"},
        errors=["planning failed"],
    )

    assert plan.paper_plan == {}
    assert plan.errors == ["planning failed"]


def test_planner_agent_plan_result_is_distinct_contract():
    assert MetadataPlanResult is not PlannerPlanResult
