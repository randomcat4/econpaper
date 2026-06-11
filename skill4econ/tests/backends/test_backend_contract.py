from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from skill4econ.adapters.heavy_backend_contract import (
    probe_r_backend,
    run_backend_command,
    validate_spatial_impacts_table,
)
from skill4econ.diagnostics.spatial_models import parse_impact_decomposition


FIXTURES = Path(__file__).resolve().parent / "parser_fixtures"


def _fake_executable(tmp_path: Path, name: str, body: str) -> Path:
    script = tmp_path / f"{name}.py"
    script.write_text(body, encoding="utf-8")
    if os.name == "nt":
        wrapper = tmp_path / f"{name}.cmd"
        wrapper.write_text(f'@echo off\r\n"{sys.executable}" "{script}" %*\r\n', encoding="utf-8")
    else:
        wrapper = tmp_path / name
        wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8")
        wrapper.chmod(0o755)
    return wrapper


def test_probe_r_backend_with_fake_executable_ok_and_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_r = _fake_executable(
        tmp_path,
        "Rscript",
        """
import os
import sys
mode = os.environ.get("FAKE_R_MODE", "ok")
if mode == "missing":
    print(os.environ.get("FAKE_R_MISSING", "spdep"))
    sys.exit(42)
print("ok")
""".strip(),
    )
    ok = probe_r_backend(["spdep"], executable=fake_r, timeout=5)
    assert ok["status"] == "ok"
    assert ok["fallback_used"] is False

    monkeypatch.setenv("FAKE_R_MODE", "missing")
    monkeypatch.setenv("FAKE_R_MISSING", "spdep")
    missing = probe_r_backend(["spdep"], executable=fake_r, timeout=5)
    assert missing["status"] == "missing_dependency"
    assert missing["error_code"] == "BACKEND_MISSING_DEPENDENCY"
    assert missing["missing_packages"] == ["spdep"]


def test_probe_r_backend_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SKILL4ECON_RSCRIPT", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    result = probe_r_backend(["spdep"])
    assert result["status"] == "backend_unavailable"
    assert result["error_code"] == "R_BACKEND_UNAVAILABLE"


def test_backend_command_contract_detects_nonzero_missing_output_and_timeout(tmp_path: Path) -> None:
    nonzero = run_backend_command(
        [sys.executable, "-c", "import sys; sys.exit(7)"],
        backend="fake_stata",
        timeout=5,
    )
    assert nonzero["status"] == "backend_error"
    assert nonzero["returncode"] == 7

    missing = run_backend_command(
        [sys.executable, "-c", "print('claimed success')"],
        expected_outputs=[tmp_path / "missing_result.csv"],
        backend="fake_stata",
        timeout=5,
    )
    assert missing["status"] == "result_missing"
    assert missing["error_code"] == "BACKEND_RESULT_MISSING"

    timeout = run_backend_command(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        backend="fake_stata",
        timeout=0.2,
    )
    assert timeout["status"] == "backend_timeout"
    assert timeout["error_code"] == "BACKEND_TIMEOUT"


def test_backend_command_success_requires_declared_outputs(tmp_path: Path) -> None:
    output = tmp_path / "result.csv"
    result = run_backend_command(
        [sys.executable, "-c", "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('x\\n', encoding='utf-8')", str(output)],
        expected_outputs=[output],
        backend="fake_r",
        timeout=5,
    )
    assert result["status"] == "ok"
    assert output.exists()


def test_spatial_impact_parser_fixture_contract(tmp_path: Path) -> None:
    source = FIXTURES / "sdm_ok_impacts.csv"
    validation = validate_spatial_impacts_table(source)
    assert validation["status"] == "ok"
    parsed = parse_impact_decomposition(source, tmp_path / "adapter")
    assert parsed["status"] == "ok"
    assert parsed["backend_run_status"] == "parser_only"
    assert parsed["canonical_backend_result"]["status"] == "parser_only"
    assert (tmp_path / "adapter" / "backend_canonical_result.json").exists()


@pytest.mark.parametrize(
    ("fixture", "marker"),
    [
        ("sdm_missing_impacts.csv", "SDM_IMPACTS_MISSING"),
        ("sdm_empty_impacts.csv", "BACKEND_PARSE_FAILED"),
    ],
)
def test_spatial_impact_parser_rejects_incomplete_fixtures(tmp_path: Path, fixture: str, marker: str) -> None:
    with pytest.raises(ValueError, match=marker):
        parse_impact_decomposition(FIXTURES / fixture, tmp_path / fixture)
