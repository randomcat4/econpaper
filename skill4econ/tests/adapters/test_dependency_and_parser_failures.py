from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from skill4econ.core import make_run_context
from skill4econ.python_wrappers import spatial_panel_model_adapter, spatial_spdep_lisa
from skill4econ.validation.contract_verifier import validate_run_dir


def test_spatial_panel_adapter_missing_backend_is_adapter_only(tmp_path: Path) -> None:
    ctx = make_run_context("spatial_panel_model_adapter", "python", {}, "run", str(tmp_path / "runs"))
    manifest = spatial_panel_model_adapter(ctx)
    assert manifest["status"] == "missing_dependency"
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["claim_level"] == "adapter_only"
    assert status["paper_readiness"] == "not_available"
    assert status["main_claim_available"] is False
    report = validate_run_dir(ctx.run_dir, strict=True)
    assert report.status == "passed"


def test_malformed_impact_parser_cli_fails_with_contract(tmp_path: Path) -> None:
    malformed = tmp_path / "bad_impacts.csv"
    pd.DataFrame([{"model": "SDM", "effect": "treat", "direct": 1.0}]).to_csv(malformed, index=False)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"impact_decomposition": str(malformed), "output_dir": str(tmp_path / "runs")}), encoding="utf-8")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill4econ.cli",
            "run",
            "--engine",
            "python",
            "--method",
            "spatial_panel_model_adapter",
            "--spec",
            str(spec),
            "--run",
        ],
        cwd=Path(__file__).resolve().parents[3],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    run_dir = Path(payload["run_dir"])
    status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    assert status["paper_readiness"] == "not_available"
    assert validate_run_dir(run_dir).status == "passed"


def test_spdep_lisa_missing_rscript_is_missing_dependency(monkeypatch, tmp_path: Path) -> None:
    data = tmp_path / "panel.csv"
    weights = tmp_path / "w.csv"
    pd.DataFrame({"id": [1, 2], "year": [2020, 2020], "y": [1.0, 2.0], "treat": [0, 1]}).to_csv(data, index=False)
    pd.DataFrame({"source": [1], "target": [2], "weight": [1.0]}).to_csv(weights, index=False)
    monkeypatch.setattr("shutil.which", lambda name: None if name == "Rscript" else None)
    ctx = make_run_context(
        "spatial_spdep_lisa",
        "python",
        {"data": str(data), "weights": str(weights), "id": "id", "time": "year", "y": "y", "treat": "treat"},
        "run",
        str(tmp_path / "runs"),
    )
    manifest = spatial_spdep_lisa(ctx)
    assert manifest["status"] == "missing_dependency"
    status = json.loads(ctx.artifact("status.json").read_text(encoding="utf-8"))
    assert status["missing_dependencies"]
    assert status["main_claim_available"] is False
