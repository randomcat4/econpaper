from __future__ import annotations

import json
from pathlib import Path

from skill4econ.validation.contract_verifier import validate_run_dir, write_validation_report


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _minimal_run(run_dir: Path, *, risk_code: str = "SPATIAL_SE_NOT_USED", status_codes: list[str] | None = None) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_log.md").write_text("# Run Log\n", encoding="utf-8")
    (run_dir / "run_log.txt").write_text("# Run Log\n", encoding="utf-8")
    (run_dir / "run_config_resolved.yaml").write_text("method: fixture\n", encoding="utf-8")
    _write_json(run_dir / "run_config_resolved.json", {"method": "fixture", "spec": {}, "rerun_command": "echo rerun"})
    (run_dir / "model_table.csv").write_text("note\nfixture\n", encoding="utf-8")
    _write_json(
        run_dir / "audit.json",
        {"status": "ok", "method": "fixture", "engine": "python", "state": "run", "messages": ["ok"]},
    )
    risks = [
        {
            "code": risk_code,
            "severity": "medium",
            "scope": "spatial",
            "message": "fixture risk",
            "required_fix": "fixture",
            "claim_degradation": "supplementary_only",
            "affected_artifacts": [],
            "known_code": risk_code != "FAKE_NEW_CODE",
        }
    ]
    _write_json(
        run_dir / "reviewer_risk.json",
        {"workflow": "fixture", "risk_level": "medium", "risks": risks, "safe_claims": [], "unsafe_claims": []},
    )
    codes = status_codes if status_codes is not None else [risk_code]
    _write_json(
        run_dir / "status.json",
        {
            "status": "success_with_warnings",
            "legacy_status": "ok",
            "method_or_workflow": "fixture",
            "method": "fixture",
            "engine": "python",
            "state": "run",
            "run_id": "fixture",
            "run_dir": str(run_dir),
            "claim_level": "diagnostic",
            "paper_readiness": "supplementary_only",
            "main_claim_available": False,
            "primary_failure_reason": None,
            "skipped_reason": None,
            "missing_dependencies": [],
            "risk_codes": codes,
            "rerun_command": "echo rerun",
        },
    )
    artifacts = []
    for path in sorted(run_dir.iterdir()):
        if path.is_file():
            artifacts.append(
                {
                    "path": path.name,
                    "type": "metadata" if path.suffix == ".json" else "log",
                    "role": "supporting",
                    "required": path.name
                    in {
                        "manifest.json",
                        "audit.json",
                        "reviewer_risk.json",
                        "artifact_manifest.json",
                        "run_config_resolved.json",
                        "run_config_resolved.yaml",
                        "run_log.md",
                        "run_log.txt",
                        "status.json",
                        "model_table.csv",
                    },
                    "required_for_paper": False,
                    "producer": "fixture",
                    "exists": True,
                    "bytes": path.stat().st_size,
                }
            )
    artifacts.append(
        {
            "path": "artifact_manifest.json",
            "type": "metadata",
            "role": "manifest",
            "required": True,
            "required_for_paper": True,
            "producer": "fixture",
            "exists": True,
            "bytes": 1,
        }
    )
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": "fixture",
            "run_id": "fixture",
            "status": "ok",
            "input_contract": None,
            "artifacts": artifacts,
            "backend_status": {},
            "missing_required_artifacts": [],
        },
    )
    _write_json(
        run_dir / "manifest.json",
        {
            "status": "ok",
            "method": "fixture",
            "engine": "python",
            "run_dir": str(run_dir),
            "timestamp_utc": "fixture",
            "rerun_command": "echo rerun",
            "claim_level": "diagnostic",
            "paper_readiness": "supplementary_only",
            "main_claim_available": False,
        },
    )


def test_valid_minimal_run_passes(tmp_path: Path) -> None:
    run_dir = tmp_path / "valid_minimal"
    _minimal_run(run_dir)
    report = validate_run_dir(run_dir, strict=True)
    assert report.status == "passed"


def test_missing_artifact_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "invalid_missing_artifact"
    _minimal_run(run_dir)
    (run_dir / "run_log.md").unlink()
    report = validate_run_dir(run_dir, strict=True)
    assert report.status == "failed"
    assert any(item.code == "missing_required_file" for item in report.errors)


def test_unregistered_risk_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "invalid_unregistered_risk"
    _minimal_run(run_dir, risk_code="FAKE_NEW_CODE")
    report = validate_run_dir(run_dir)
    assert report.status == "failed"
    assert any(item.code == "unregistered_risk_code" for item in report.errors)


def test_inconsistent_status_risk_codes_fail(tmp_path: Path) -> None:
    run_dir = tmp_path / "invalid_inconsistent_status"
    _minimal_run(run_dir, status_codes=[])
    report = validate_run_dir(run_dir)
    assert report.status == "failed"
    assert any(item.code == "risk_code_mismatch" for item in report.errors)


def test_success_with_fatal_risk_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "success_with_fatal_risk"
    _minimal_run(run_dir)
    reviewer_risk = json.loads((run_dir / "reviewer_risk.json").read_text(encoding="utf-8"))
    reviewer_risk["risks"][0]["severity"] = "fatal"
    reviewer_risk["risks"][0]["claim_degradation"] = "failed"
    _write_json(run_dir / "reviewer_risk.json", reviewer_risk)
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    status["status"] = "success"
    _write_json(run_dir / "status.json", status)
    report = validate_run_dir(run_dir)
    assert report.status == "failed"
    assert any(item.code == "success_with_fatal_risk" for item in report.errors)


def test_write_validation_report(tmp_path: Path) -> None:
    run_dir = tmp_path / "valid_minimal"
    _minimal_run(run_dir)
    report = write_validation_report(run_dir, strict=True)
    assert report.status == "passed"
    assert (run_dir / "validation_report.json").exists()


def test_workflow_child_run_and_model_table_sources_pass(tmp_path: Path) -> None:
    child = tmp_path / "child"
    parent = tmp_path / "parent"
    _minimal_run(child)
    _minimal_run(parent)
    audit = json.loads((parent / "audit.json").read_text(encoding="utf-8"))
    audit["workflow"] = "fixture_workflow"
    audit["steps"] = [{"seq": 1, "engine": "python", "method": "fixture", "status": "ok", "run_dir": str(child)}]
    _write_json(parent / "audit.json", audit)
    (parent / "step_results.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "seq": 1,
                        "engine": "python",
                        "method": "fixture",
                        "status": "ok",
                        "critical": True,
                        "run_dir": str(child),
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (parent / "model_table.csv").write_text(
        "term,coef,status,source_run_dir,source_model_table\n"
        f"fixture,1.0,ok,{child},{child / 'model_table.csv'}\n",
        encoding="utf-8",
    )
    report = validate_run_dir(parent, strict=True)
    assert report.status == "passed"


def test_missing_model_table_source_fails(tmp_path: Path) -> None:
    run_dir = tmp_path / "missing_source"
    _minimal_run(run_dir)
    audit = json.loads((run_dir / "audit.json").read_text(encoding="utf-8"))
    audit["workflow"] = "fixture_workflow"
    audit["steps"] = [{"seq": 1, "engine": "python", "method": "fixture", "status": "ok"}]
    _write_json(run_dir / "audit.json", audit)
    (run_dir / "model_table.csv").write_text(
        "term,coef,status,source_model_table\nfixture,1.0,ok,missing_child/model_table.csv\n",
        encoding="utf-8",
    )
    report = validate_run_dir(run_dir)
    assert report.status == "failed"
    assert any(item.code == "model_table_source_missing" for item in report.errors)


def test_invalid_child_run_contract_fails_parent_validation(tmp_path: Path) -> None:
    child = tmp_path / "bad_child"
    parent = tmp_path / "parent"
    _minimal_run(child)
    _minimal_run(parent)
    (child / "status.json").unlink()
    (parent / "step_results.json").write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "seq": 1,
                        "engine": "python",
                        "method": "fixture",
                        "status": "failed",
                        "critical": True,
                        "run_dir": str(child),
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (parent / "model_table.csv").write_text(
        "term,status,source_run_dir,source_model_table\n"
        f"fixture,failed,{child},{child / 'model_table.csv'}\n",
        encoding="utf-8",
    )
    report = validate_run_dir(parent)
    assert report.status == "failed"
    assert any(item.code == "child_run_contract_failed" for item in report.errors)
