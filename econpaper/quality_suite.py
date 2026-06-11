from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


QUALITY_SUITE_VERSION = "v3.0"

FALSE_CONFIDENCE_FIXTURES = [
    ("T01", "unknown_method_cannot_become_paper_ready", "hard_block", "tests/test_run_validator_fail_closed.py"),
    ("T02", "unknown_run_status_cannot_become_success_with_warnings", "hard_block", "tests/test_run_validator_fail_closed.py"),
    ("T03", "table_path_is_not_sufficient_evidence", "hard_block", "tests/test_evidence_ledger_builder.py"),
    ("T04", "invented_coefficient_hard_blocked", "hard_block", "tests/test_lint_mode_mvp.py"),
    ("T05", "robustness_cannot_become_main_result", "flag_and_confirm", "tests/test_claim_ledger_builder.py"),
    ("T06", "mechanism_cannot_be_written_as_proof", "flag_and_confirm", "tests/test_lint_mode_mvp.py"),
    ("T07", "staggered_did_with_twfe_only_flagged", "flag_and_confirm", "tests/test_design_profiler.py"),
    ("T08", "iv_without_first_stage_flagged", "flag_and_confirm", "tests/test_design_profiler.py"),
    ("T09", "rdd_without_manipulation_test_flagged", "flag_and_confirm", "tests/test_design_profiler.py"),
    ("T10", "finance_signal_with_lookahead_flagged", "flag_and_confirm", "tests/test_design_profiler.py"),
    ("T11", "missing_bibliography_does_not_create_fake_citations", "hard_block", "tests/test_section_writer.py"),
    ("T12", "unknown_citation_key_hard_blocks_cite_command", "hard_block", "tests/test_lint_mode_mvp.py"),
    ("T13", "absolute_path_leakage_blocked_from_public_output", "hard_block", "tests/test_compile_and_write_pack.py"),
    ("T14", "mock_output_cannot_masquerade_as_real_draft", "hard_block", "tests/test_run_validator_fail_closed.py"),
    ("T15", "external_validity_overclaim_flagged", "flag_and_confirm", "tests/test_lint_mode_mvp.py"),
]

Q_SERIES_CHECKS = [
    ("Q1", "economic_magnitude_required_in_main_results", "hard_block", "tests/test_release_gate.py"),
    ("Q2", "deterministic_numeric_rendering_required", "hard_block", "tests/test_numeric_renderer.py"),
    ("Q3", "hedging_density_bounded", "style_advice", "tests/test_global_coherence.py"),
    ("Q4", "global_numeric_consistency", "hard_block", "tests/test_global_coherence.py"),
    ("Q5", "abstract_and_body_consistency", "hard_block", "tests/test_global_coherence.py"),
    ("Q6", "override_trace_completeness", "hard_block", "tests/test_claim_ledger_builder.py"),
    ("Q7", "publication_table_quality", "hard_block", "tests/test_publication_table_generator.py"),
    ("Q8", "human_evaluation_release_gate", "hard_block", "tests/test_release_gate.py"),
]

HARD_BLOCK_CLASSES = {
    "fabricated_numeric_value",
    "fabricated_citation_key",
    "mock_output_as_real",
    "release_gate_quality_failure",
}


@dataclass
class QualitySuiteResult:
    manifest: dict[str, Any]
    status: str = "passed"
    issues: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.get("tier") == "hard_block" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": QUALITY_SUITE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "manifest": self.manifest,
            "issues": self.issues,
        }


def build_quality_suite_manifest() -> QualitySuiteResult:
    false_confidence = [_fixture_dict(item) for item in FALSE_CONFIDENCE_FIXTURES]
    q_series = [_fixture_dict(item) for item in Q_SERIES_CHECKS]
    issues: list[dict[str, Any]] = []
    if len(false_confidence) != 15:
        issues.append({"code": "false_confidence_count_invalid", "tier": "hard_block", "message": "Expected exactly 15 false-confidence fixtures."})
    if len(q_series) < 5:
        issues.append({"code": "q_series_count_invalid", "tier": "hard_block", "message": "Expected at least five Q-series quality checks."})
    test15 = next((item for item in false_confidence if item["id"] == "T15"), None)
    if not test15 or test15["expected_tier"] != "flag_and_confirm":
        issues.append({"code": "test15_tier_invalid", "tier": "hard_block", "message": "Test 15 must be flag_and_confirm in v3 semantics."})
    manifest = {
        "version": QUALITY_SUITE_VERSION,
        "tier_semantics": {
            "hard_block": "non-overridable fabricated numbers, fabricated citations, mock-as-real, and release-gate quality failures",
            "flag_and_confirm": "serious design or reviewer risks with author override path",
            "style_advice": "wording or presentation preference, not release-blocking by itself",
        },
        "hard_block_classes": sorted(HARD_BLOCK_CLASSES),
        "false_confidence_fixtures": false_confidence,
        "q_series_checks": q_series,
        "pass_line": {
            "false_confidence_fixture_count": 15,
            "minimum_q_series_checks": 5,
            "human_eval": "at least five scholars; median retention >= 50%; >=4 report time saved; no silent fabrication; >=3 clearer AUTHOR_REPORT; all feedback attached",
        },
    }
    return QualitySuiteResult(manifest=manifest, status="failed" if issues else "passed", issues=issues)


def write_quality_suite_manifest(*, out_dir: str | Path) -> QualitySuiteResult:
    result = build_quality_suite_manifest()
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    (internal / "quality_suite.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _fixture_dict(item: tuple[str, str, str, str]) -> dict[str, Any]:
    fixture_id, name, expected_tier, covered_by = item
    return {
        "id": fixture_id,
        "name": name,
        "expected_tier": expected_tier,
        "covered_by": covered_by,
    }


def _author_report_text(result: QualitySuiteResult) -> str:
    manifest = result.manifest
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Quality Suite Status",
        "",
        f"- Status: `{result.status}`",
        f"- False-confidence fixtures retained: `{len(manifest.get('false_confidence_fixtures', []))}`",
        f"- Q-series checks: `{len(manifest.get('q_series_checks', []))}`",
        "",
        "## Human Evaluation Pass Line",
        "",
        f"- {manifest.get('pass_line', {}).get('human_eval')}",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    hard = [issue for issue in result.issues if issue.get("tier") == "hard_block"]
    lines.extend([f"- `{issue['code']}`: {issue['message']}" for issue in hard] if hard else ["- None."])
    return "\n".join(lines) + "\n"
