from __future__ import annotations

import pytest

from skill4econ.core import make_run_context
from skill4econ.contracts.agent_status import infer_agent_status, is_claimable_agent_status
from skill4econ.contracts.stata_safety import StataSpecSafetyError, validate_stata_spec
from skill4econ.python_wrappers import dea_sbm_malmquist_adapter


def test_agent_status_claimable_only_for_main_paper_ready() -> None:
    status = infer_agent_status(
        legacy_status="ok",
        normalized_status="success",
        claim_level="main_estimate",
        paper_readiness="paper_ready",
        main_claim_available=True,
        risk_level="none",
        risk_codes=[],
        missing_dependencies=[],
        extra={},
    )
    assert status == "claimable_success"
    assert is_claimable_agent_status(status)


def test_agent_status_distinguishes_adapter_success_from_claimable_success() -> None:
    status = infer_agent_status(
        legacy_status="ok",
        normalized_status="success",
        claim_level="adapter_only",
        paper_readiness="not_available",
        main_claim_available=False,
        risk_level="none",
        risk_codes=[],
        missing_dependencies=[],
        extra={},
    )
    assert status == "success_adapter_only"
    assert not is_claimable_agent_status(status)


def test_agent_status_backend_risk_is_partial_backend_unavailable() -> None:
    status = infer_agent_status(
        legacy_status="ok",
        normalized_status="success_with_warnings",
        claim_level="main_estimate",
        paper_readiness="paper_ready",
        main_claim_available=True,
        risk_level="medium",
        risk_codes=["BACKEND_RESULT_MISSING"],
        missing_dependencies=[],
        extra={},
    )
    assert status == "partial_backend_unavailable"


def test_stata_safety_allows_common_inlist_condition() -> None:
    validate_stata_spec(
        {
            "y": "y",
            "x": ["x1", "c.x2#c.x3"],
            "id": "firm_id",
            "time": "year",
            "sample_if": "inlist(year, 2018, 2019)",
        }
    )


def test_stata_safety_rejects_command_separator_in_varlist() -> None:
    with pytest.raises(StataSpecSafetyError):
        validate_stata_spec({"y": "y", "x": ["x1; shell erase important.dta"]})


def test_stata_safety_rejects_w_grid_command_injection() -> None:
    with pytest.raises(StataSpecSafetyError):
        validate_stata_spec({"w_grid": [{"name": "W", "options": "normalize(row); shell erase x"}]})


def test_dea_second_stage_request_is_blocked_not_reported_ok(tmp_path) -> None:
    ctx = make_run_context(
        "dea_sbm_malmquist_adapter",
        "python",
        {
            "second_stage": {"requested": True, "model": "naive_tobit"},
            "dea": {"dmus": 3, "periods": 2, "nx": 2, "ny": 2, "nb": 1, "undesirable": 1, "sup": 0},
        },
        "run",
        str(tmp_path / "runs"),
    )

    manifest = dea_sbm_malmquist_adapter(ctx)

    assert manifest["status"] == "failed"
    assert manifest["agent_status"] == "failed"
    assert "DEA_SECOND_STAGE_NAIVE_TOBIT" in manifest["risk_codes"]
    assert manifest["main_claim_available"] is False
