from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.run_validation import MOCK_WATERMARK, validate_run_dir, write_run_validation


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_dir(
    root: Path,
    *,
    status: str = "success",
    method: str = "ols_cluster",
    validation_status: str | None = "passed",
    artifact_manifest: bool = True,
    mock_runner: bool = False,
    agent_status: str = "claimable_success",
    claim_level: str = "main_estimate",
    paper_readiness: str = "paper_ready",
    main_claim_available: bool = True,
) -> Path:
    run_dir = root / "run"
    run_dir.mkdir()
    _write_json(
        run_dir / "status.json",
        {
            "status": status,
            "agent_status": agent_status,
            "method_or_workflow": method,
            "engine": "python",
            "run_id": "fixture",
            "claim_level": claim_level,
            "paper_readiness": paper_readiness,
            "main_claim_available": main_claim_available,
            "risk_codes": [],
            "run_dir": str(run_dir),
            "rerun_command": "echo rerun",
        },
    )
    _write_json(
        run_dir / "manifest.json",
        {
            "status": status,
            "method": method,
            "claim_level": claim_level,
            "paper_readiness": paper_readiness,
            "main_claim_available": main_claim_available,
        },
    )
    _write_json(run_dir / "audit.json", {"status": status, "method": method, "mock_runner": mock_runner})
    _write_json(run_dir / "run_config_resolved.json", {"spec": {}, "mock_runner": mock_runner})
    if validation_status is not None:
        _write_json(run_dir / "validation_report.json", {"status": validation_status, "errors": []})
    if artifact_manifest:
        _write_json(
            run_dir / "artifact_manifest.json",
            {
                "workflow": method,
                "run_id": "fixture",
                "status": status,
                "evidence_contract": {
                    "consumer": "econpaper",
                    "schema_version": "evidence_pack.v2",
                    "artifact_type_field": "evidence_type",
                },
                "artifacts": [{"path": "model_table.json", "type": "model_result", "evidence_type": "model_table", "required": True, "exists": True}],
                "missing_required_artifacts": [],
            },
        )
    return run_dir


def _codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_known_success_run_allows_automatic_claims(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.status == "passed"
    assert report.automatic_claims_allowed is True
    assert report.automatic_results_allowed is True


def test_windows_utf8_bom_json_is_accepted(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path)
    for path in run_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8")
        path.write_text(text, encoding="utf-8-sig")
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.status == "passed"
    assert "invalid_json" not in _codes(report)


def test_unknown_run_status_fails_closed(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, status="weird_completed_state")
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.automatic_claims_allowed is False
    assert "unknown_run_status" in _codes(report)


def test_unknown_method_cannot_be_paper_ready(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, method="my_new_magic_estimator")
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.automatic_claims_allowed is False
    assert "unknown_method" in _codes(report)


def test_missing_validation_report_blocks_results(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, validation_status=None)
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.automatic_results_allowed is False
    assert "validation_report_not_passed" in _codes(report)


def test_missing_artifact_manifest_blocks_claimable_results(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, artifact_manifest=False)
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    assert report.automatic_claims_allowed is False
    assert "artifact_manifest_not_claimable" in _codes(report)


def test_parser_or_adapter_only_statuses_are_not_claimable(tmp_path: Path) -> None:
    run_dir = _run_dir(
        tmp_path,
        status="skipped",
        agent_status="blocked_parser_only",
        claim_level="adapter_only",
        paper_readiness="not_available",
        main_claim_available=False,
    )
    report = validate_run_dir(run_dir, known_methods={"ols_cluster"})
    codes = _codes(report)
    assert "non_claimable_run_status" in codes
    assert "non_claimable_agent_status" in codes
    assert "non_claimable_claim_level" in codes


def test_mock_output_requires_visible_watermark(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, mock_runner=True)
    out_dir = tmp_path / "out"
    report = write_run_validation(run_dir, out_dir)
    assert report.mock_watermark_required is True
    assert report.public_watermark == MOCK_WATERMARK
    assert MOCK_WATERMARK in (out_dir / "AUTHOR_REPORT.md").read_text(encoding="utf-8")
    assert "mock_output_not_paper_draft" in _codes(report)


def test_validate_run_cli_writes_internal_report_and_exits_nonzero_on_block(tmp_path: Path) -> None:
    run_dir = _run_dir(tmp_path, status="weird_completed_state")
    out_dir = tmp_path / "lint_pack"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "validate-run",
            "--run-dir",
            str(run_dir),
            "--out",
            str(out_dir),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 1
    assert (out_dir / "reports" / "internal" / "run_validation.json").exists()
    assert (out_dir / "AUTHOR_REPORT.md").exists()
