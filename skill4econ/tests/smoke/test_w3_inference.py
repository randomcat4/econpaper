from __future__ import annotations

import math

import numpy as np
import pytest

from skill4econ.diagnostics.w3_inference import (
    conley_covariance,
    null_imposed_wild_cluster_test,
    romano_wolf_stepdown,
    validate_mop_effective_f_artifact,
)


def test_null_imposed_wcr_fails_closed_with_two_clusters() -> None:
    x = np.linspace(-1.0, 1.0, 8)
    X = np.column_stack([np.ones_like(x), x])
    y = 1.0 + 0.3 * x
    result = null_imposed_wild_cluster_test(y, X, ["a"] * 4 + ["b"] * 4, [0.0, 1.0], B=39)

    assert result["status"] == "result_missing"
    assert result["error_code"] == "W3_TOO_FEW_CLUSTERS"


def test_null_imposed_wcr_outputs_auditable_p_value() -> None:
    clusters = np.repeat(np.arange(6), 5)
    x = np.linspace(-1.0, 1.0, clusters.size)
    X = np.column_stack([np.ones_like(x), x])
    y = 1.0 + 0.25 * x + 0.05 * clusters + 0.02 * np.sin(np.arange(clusters.size))

    result = null_imposed_wild_cluster_test(y, X, clusters, [0.0, 1.0], B=49, seed=123)

    assert result["status"] == "ok"
    assert result["null_imposed"] is True
    assert result["cluster_count"] == 6
    assert result["successful_B"] >= 20
    assert 0.0 <= result["p_value"] <= 1.0
    assert result["F_obs"] >= 0.0


def test_conley_covariance_requires_time_bandwidth_when_time_is_used() -> None:
    X = np.column_stack([np.ones(6), np.arange(6, dtype=float)])
    y = np.array([1.0, 1.2, 1.4, 1.5, 1.7, 1.9])
    lon = np.linspace(0.0, 0.04, 6)
    lat = np.linspace(0.0, 0.04, 6)

    result = conley_covariance(X, y, lon, lat, time=np.arange(6), theta_km=20)

    assert result["status"] == "invalid_result"
    assert result["error_code"] == "W3_INVALID_TIME_BANDWIDTH"


def test_conley_covariance_writes_full_conley_rows() -> None:
    X = np.column_stack([np.ones(8), np.linspace(0.0, 1.0, 8)])
    y = 1.0 + 0.4 * X[:, 1] + 0.02 * np.cos(np.arange(8))
    lon = np.linspace(0.0, 0.05, 8)
    lat = np.linspace(0.0, 0.05, 8)

    result = conley_covariance(
        X,
        y,
        lon,
        lat,
        time=np.repeat([1, 2], 4),
        theta_km=25,
        time_bandwidth=1,
        terms=["const", "x"],
    )

    assert result["status"] == "ok"
    assert result["is_full_conley"] is True
    assert result["n_pairs_used"] > 0
    assert len(result["covariance"]) == 2
    assert {row["se_type"] for row in result["rows"]} == {"conley_full"}
    assert all(math.isfinite(row["std_error"]) for row in result["rows"])


def test_romano_wolf_single_hypothesis_matches_raw_p_value() -> None:
    draws = np.array([[0.1], [0.5], [1.0], [1.5], [2.5], [0.3], [0.4], [0.9], [1.2], [1.6]] * 3)
    result = romano_wolf_stepdown([1.0], draws, labels=["beta"], alpha=0.05)

    assert result["status"] == "ok"
    row = result["rows"][0]
    assert row["p_adj"] == pytest.approx(row["p_raw"])
    assert row["label"] == "beta"


def test_romano_wolf_rejects_dimension_mismatch() -> None:
    result = romano_wolf_stepdown([1.0, 2.0], [[0.5], [1.5]] * 10)

    assert result["status"] == "invalid_result"
    assert result["error_code"] == "W3_DIMENSION_MISMATCH"


def test_mop_effective_f_requires_backend_critical_value_artifact() -> None:
    missing = validate_mop_effective_f_artifact(effective_f=12.0, critical_value=None)
    assert missing["status"] == "result_missing"
    assert missing["mop_effective_f_certified"] is False

    ok = validate_mop_effective_f_artifact(effective_f=16.0, critical_value=15.49, source_backend="stata_weakivtest")
    assert ok["status"] == "ok"
    assert ok["weak_iv_flag"] is False
    assert ok["mop_effective_f_certified"] is True
