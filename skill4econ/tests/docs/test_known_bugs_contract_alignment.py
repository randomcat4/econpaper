from __future__ import annotations

from pathlib import Path

from skill4econ.contracts.known_gaps import KNOWN_GAPS, known_gap_ids
from skill4econ.contracts.risk_registry import REGISTERED_RISK_CODES


DOC = Path(__file__).resolve().parents[2] / "docs" / "KNOWN_BUGS.md"


def test_known_bugs_have_machine_gap_entries() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "spatial_exposure_did" in text
    assert "spatial_spdep_lisa" in text
    assert "spatial_panel_model_adapter" in text
    assert "spatial_se_comparison" in text
    assert "spatial_w_sensitivity" in text
    assert "PSM/IPW" in text
    assert known_gap_ids() >= {
        "spatial_exposure_reduced_form",
        "spdep_lisa_dependency_gated",
        "spatial_structural_adapter_only",
        "spatial_se_sensitivity_only",
        "w_sensitivity_user_supplied_grid",
        "psm_did_support_not_main_modern_did",
        "dea_second_stage_not_certified",
        "vendor_sources_not_commit_pinned",
    }


def test_known_gap_risk_codes_are_registered() -> None:
    for gap in KNOWN_GAPS:
        for code in gap.get("risk_codes", []):
            assert code in REGISTERED_RISK_CODES, (gap["id"], code)


def test_known_bugs_points_to_windows_first_smoke_cli() -> None:
    text = DOC.read_text(encoding="utf-8")
    assert "python -m skill4econ.cli smoke --suite spatial --strict" in text
