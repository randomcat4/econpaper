from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from skill4econ.core import make_run_context
from skill4econ.diagnostics import live_backend_certification as live_cert
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
    repo_root = Path(__file__).resolve().parents[3]
    child_env = os.environ.copy()
    src_root = repo_root / "skill4econ" / "src"
    child_env["PYTHONPATH"] = (
        str(src_root)
        if not child_env.get("PYTHONPATH")
        else f"{src_root}{os.pathsep}{child_env['PYTHONPATH']}"
    )
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
        cwd=repo_root,
        env=child_env,
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


def test_stata_command_probe_uses_matching_log_name_and_timeout(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_run_stata_do(spec, output_dir, *, name, do_text, timeout):
        captured.update({"name": name, "do_text": do_text, "timeout": timeout})
        return {"status": "ok", "backend_run_status": "ok", "available": True}

    monkeypatch.setattr(live_cert, "_run_stata_do", fake_run_stata_do)

    result = live_cert._stata_command_available({"xsmle_probe_timeout": 123}, tmp_path, "xsmle")

    assert captured["name"] == "which_xsmle"
    assert 'capture which xsmle' in str(captured["do_text"])
    assert "log using" not in str(captured["do_text"])
    assert captured["timeout"] == 123
    assert result["command_name"] == "xsmle"


def test_run_stata_do_passes_absolute_do_file_when_output_dir_is_relative(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(live_cert, "resolve_stata", lambda spec: (Path("D:/stata17/StataMP-64.exe"), "test"))
    monkeypatch.setattr(live_cert, "resolve_stata_batch_args", lambda executable, spec: ["/e", "do"])

    class FakeProc:
        returncode = 0

    def fake_run(cmd, *, cwd, stdout, stderr, text, timeout, check):
        captured.update({"cmd": cmd, "cwd": cwd, "timeout": timeout})
        return FakeProc()

    monkeypatch.setattr(live_cert.subprocess, "run", fake_run)

    result = live_cert._run_stata_do({}, Path("relative_out"), name="probe", do_text="exit\n", timeout=7)

    assert result["status"] == "ok"
    assert Path(captured["cmd"][-1]).is_absolute()
    assert Path(captured["cwd"]).is_absolute()
    assert captured["timeout"] == 7


def test_parse_xsmle_impact_csv_requires_uncertainty(tmp_path: Path) -> None:
    impact_path = tmp_path / "xsmle_impacts.csv"
    impact_path.write_text(
        "\n".join(
            [
                "effect,direct,indirect,total,direct_std_error,indirect_std_error,total_std_error,direct_p_value,indirect_p_value,total_p_value",
                "x1,0.1,0.2,0.3,0.01,0.02,0.03,0.04,0.05,0.06",
                "x2,0.1,0.2,0.3,,,,,,",
            ]
        ),
        encoding="utf-8",
    )

    rows = live_cert.parse_xsmle_impact_csv(impact_path, model="SDM", w_name="W")

    assert len(rows) == 1
    assert rows[0]["backend"] == "stata_xsmle"
    assert rows[0]["effect"] == "x1"
    assert rows[0]["direct_p_value"] == 0.04


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
