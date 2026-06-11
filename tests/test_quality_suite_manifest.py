from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from econpaper.quality_suite import build_quality_suite_manifest, write_quality_suite_manifest


def test_false_confidence_fixture_manifest_retains_all_fifteen() -> None:
    result = build_quality_suite_manifest()
    fixtures = result.manifest["false_confidence_fixtures"]
    assert result.has_hard_blocks is False
    assert len(fixtures) == 15
    assert {item["id"] for item in fixtures} == {f"T{idx:02d}" for idx in range(1, 16)}
    assert next(item for item in fixtures if item["id"] == "T15")["expected_tier"] == "flag_and_confirm"


def test_q_series_manifest_has_q1_through_q8() -> None:
    result = build_quality_suite_manifest()
    q_series = result.manifest["q_series_checks"]
    assert len(q_series) == 8
    assert {item["id"] for item in q_series} == {f"Q{idx}" for idx in range(1, 9)}
    assert len(q_series) >= 5


def test_tier_semantics_are_explicit() -> None:
    result = build_quality_suite_manifest()
    semantics = result.manifest["tier_semantics"]
    assert "hard_block" in semantics
    assert "flag_and_confirm" in semantics
    assert "style_advice" in semantics
    assert "fabricated_numeric_value" in result.manifest["hard_block_classes"]
    assert "mock_output_as_real" in result.manifest["hard_block_classes"]


def test_quality_suite_cli_writes_manifest_and_author_report(tmp_path: Path) -> None:
    out = tmp_path / "quality"
    proc = subprocess.run(
        [sys.executable, "-m", "econpaper.cli", "quality-suite", "--out", str(out)],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "reports" / "internal" / "quality_suite.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()


def test_write_quality_suite_author_report_contains_human_pass_line(tmp_path: Path) -> None:
    result = write_quality_suite_manifest(out_dir=tmp_path / "out")
    report = (tmp_path / "out" / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert result.status == "passed"
    assert "at least five scholars" in report
    assert "False-confidence fixtures retained: `15`" in report
