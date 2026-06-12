from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE_DIR = ROOT / "skill4econ" / "tests" / "fixtures" / "spatial"
if str(FIXTURE_DIR) not in sys.path:
    sys.path.insert(0, str(FIXTURE_DIR))

from generate_spatial_fixtures import SPATIAL_FIXTURE_NAMES, materialize_spatial_fixtures
from skill4econ.core import make_run_context
from skill4econ.diagnostics.spatial_exposure import run_spatial_exposure_did
from skill4econ.diagnostics.spatial_models import parse_impact_decomposition
from skill4econ.diagnostics.spatial_moran import run_moran_preflight
from skill4econ.diagnostics.spatial_preflight import audit_spatial_weights
from skill4econ.diagnostics.spatial_se import run_spatial_se_comparison
from skill4econ.diagnostics.w_sensitivity import run_w_sensitivity
from skill4econ.python_wrappers import spatial_panel_model_adapter, spatial_se_comparison, spatial_w_sensitivity


def _codes(result: dict) -> set[str]:
    return {item["code"] for item in result.get("warnings") or []}


def _resolve_case_spec(case_dir: Path) -> dict:
    spec = json.loads((case_dir / "spec.json").read_text(encoding="utf-8"))
    spec["data"] = str(case_dir / "panel.csv")
    for key in ["weights", "w_path", "weight_matrix"]:
        if spec.get(key):
            spec[key] = str(case_dir / spec[key])
    if spec.get("weight_paths"):
        spec["weight_paths"] = [str(case_dir / item) for item in spec["weight_paths"]]
    return spec


def test_spatial_fixture_family_expected_risks(tmp_path: Path) -> None:
    paths = materialize_spatial_fixtures(FIXTURE_DIR)
    assert {path.name for path in paths} == set(SPATIAL_FIXTURE_NAMES)
    for case_dir in paths:
        spec = _resolve_case_spec(case_dir)
        expected = set(json.loads((case_dir / "expected_risks.json").read_text(encoding="utf-8"))["expected_risks"])
        panel = pd.read_csv(spec["data"])
        method = spec["method"]
        if method == "spatial_w_audit":
            result = audit_spatial_weights(spec["weights"], panel, spec, tmp_path / case_dir.name)
        elif method == "spatial_moran_preflight":
            result = run_moran_preflight(panel, spec["weights"], spec, tmp_path / case_dir.name)
        elif method == "spatial_exposure_did":
            result = run_spatial_exposure_did(panel, spec["weights"], spec, tmp_path / case_dir.name)
        elif method == "spatial_w_sensitivity":
            result = run_w_sensitivity(panel, spec, tmp_path / case_dir.name)
        else:
            raise AssertionError(f"Unknown spatial fixture method: {method}")
        assert expected.issubset(_codes(result)), case_dir.name


def test_local_moran_table_is_written(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[2]
    spec = _resolve_case_spec(case_dir)
    panel = pd.read_csv(spec["data"])
    result = run_moran_preflight(panel, spec["weights"], spec, tmp_path / "moran")
    assert result["artifacts"]["local_moran"] == "tables/local_moran_by_year.csv"
    local = pd.read_csv(tmp_path / "moran" / "tables" / "local_moran_by_year.csv")
    assert {
        "local_moran_i",
        "expected_i",
        "variance_i",
        "z_i",
        "quadrant",
        "p_value",
        "p_value_available",
        "permutations",
        "backend",
    }.issubset(local.columns)
    assert set(local["backend"]) == {"python_basic_permutation"}
    assert local["p_value_available"].all()
    assert local["permutations"].min() > 0


def test_local_moran_without_permutation_is_not_lisa_evidence(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[2]
    spec = _resolve_case_spec(case_dir)
    spec["local_moran_permutations"] = 0
    panel = pd.read_csv(spec["data"])
    result = run_moran_preflight(panel, spec["weights"], spec, tmp_path / "moran")
    assert "LOCAL_MORAN_PERMUTATION_NOT_RUN" in _codes(result)
    local = pd.read_csv(tmp_path / "moran" / "tables" / "local_moran_by_year.csv")
    assert set(local["backend"]) == {"python_basic_no_permutation"}
    assert set(local["quadrant"]) == {"not_tested"}


def test_spatial_se_comparison_outputs_cutoff_grid(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[3]
    spec = _resolve_case_spec(case_dir)
    spec["spatial_se_cutoffs_km"] = [10, 100]
    panel = pd.read_csv(spec["data"])
    result = run_spatial_se_comparison(panel, spec["weights"], spec, tmp_path / "se")
    assert result["status"] == "ok"
    assert "SPATIAL_HAC_UNIFORM_KERNEL" not in _codes(result)
    assert result["is_full_conley"] is True
    table = pd.read_csv(tmp_path / "se" / "tables" / "spatial_se_comparison.csv")
    assert {"conley_bartlett_distance", "cluster:city:numpy"} & set(table["se_type"].astype(str))
    hac_rows = table[table["se_type"].astype(str) == "conley_bartlett_distance"]
    assert set(hac_rows["kernel"].astype(str)) == {"bartlett_distance"}
    assert hac_rows["is_full_conley"].astype(bool).all()
    assert (tmp_path / "se" / "figures" / "spatial_se_cutoff_sensitivity.png").exists()


def test_spatial_exposure_writes_local_did_common_output(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[3]
    spec = _resolve_case_spec(case_dir)
    panel = pd.read_csv(spec["data"])
    result = run_spatial_exposure_did(panel, spec["weights"], spec, tmp_path / "exposure")
    assert result["artifacts"]["did_common_output"] == "did_common_output.json"
    common = json.loads((tmp_path / "exposure" / "did_common_output.json").read_text(encoding="utf-8"))
    assert common["estimator"] == "spatial_exposure_local_twfe"
    assert common["main_effect"]["term"] == "_local_treatment"
    assert common["dynamic_effects_path"] is None
    assert "W*treatment" in common["note"]


def test_spatial_model_adapter_parses_impact_decomposition(tmp_path: Path) -> None:
    impacts = tmp_path / "impacts.csv"
    pd.DataFrame(
        [
            {"model": "SDM", "effect": "treat", "direct": 1.0, "indirect": 0.4, "total": 1.4, "std_error": 0.2, "p_value": 0.01}
        ]
    ).to_csv(impacts, index=False)
    result = parse_impact_decomposition(impacts, tmp_path / "adapter")
    assert result["status"] == "ok"
    table = pd.read_csv(tmp_path / "adapter" / "tables" / "spatial_impact_decomposition.csv")
    assert {"direct_effect", "indirect_effect", "total_effect"}.issubset(table.columns)

    ctx = make_run_context(
        "spatial_panel_model_adapter",
        "python",
        {"impact_decomposition": str(impacts)},
        "run",
        str(tmp_path / "runs"),
    )
    manifest = spatial_panel_model_adapter(ctx)
    assert manifest["status"] == "ok"
    assert ctx.artifact("model_table.csv").exists()


def test_spatial_w_sensitivity_wrapper_records_sign_flip(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[-1]
    spec = _resolve_case_spec(case_dir)
    ctx = make_run_context("spatial_w_sensitivity", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_w_sensitivity(ctx)
    assert manifest["status"] == "ok"
    risk = json.loads(ctx.artifact("reviewer_risk.json").read_text(encoding="utf-8"))
    assert "W_SENSITIVITY_SIGN_FLIP" in {item["code"] for item in risk["risks"]}
    assert ctx.artifact("tables/w_sensitivity_main_effects.csv").exists()


def test_spatial_se_wrapper_registers_artifacts(tmp_path: Path) -> None:
    case_dir = materialize_spatial_fixtures(FIXTURE_DIR)[3]
    spec = _resolve_case_spec(case_dir)
    spec["spatial_se_cutoffs_km"] = [20, 100]
    ctx = make_run_context("spatial_se_comparison", "python", spec, "run", str(tmp_path / "runs"))
    manifest = spatial_se_comparison(ctx)
    assert manifest["status"] == "ok"
    artifact_manifest = json.loads(ctx.artifact("artifact_manifest.json").read_text(encoding="utf-8"))
    paths = {item["path"] for item in artifact_manifest["artifacts"]}
    assert "tables/spatial_se_comparison.csv" in paths
    assert "figures/spatial_se_cutoff_sensitivity.png" in paths
