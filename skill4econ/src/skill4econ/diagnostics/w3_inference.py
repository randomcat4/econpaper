from __future__ import annotations

import math
from typing import Any, Sequence

from ..adapters.heavy_backend_contract import canonical_backend_result


def _normal_pvalue(stat: float) -> float:
    if not math.isfinite(stat):
        return math.nan
    return float(math.erfc(abs(stat) / math.sqrt(2.0)))


def _as_2d_float(value: Any, *, name: str) -> Any:
    import numpy as np

    arr = np.asarray(value, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.ndim != 2 or arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError(f"{name} must be a finite non-empty vector or matrix.")
    return arr


def _as_1d_float(value: Any, *, name: str) -> Any:
    import numpy as np

    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 0 or not np.isfinite(arr).all():
        raise ValueError(f"{name} must be a finite non-empty vector.")
    return arr


def _cluster_covariance(X: Any, residuals: Any, clusters: Sequence[Any], xtx_inv: Any) -> Any:
    import numpy as np

    groups = np.asarray([str(item) for item in clusters], dtype=object)
    unique_groups = np.unique(groups)
    n, k = X.shape
    meat = np.zeros((k, k), dtype=float)
    for group in unique_groups:
        mask = groups == group
        score = X[mask, :].T @ residuals[mask]
        meat += np.outer(score, score)
    correction = 1.0
    if len(unique_groups) > 1 and n > k:
        correction = (len(unique_groups) / (len(unique_groups) - 1)) * ((n - 1) / (n - k))
    return correction * xtx_inv @ meat @ xtx_inv


def null_imposed_wild_cluster_test(
    y: Sequence[float],
    X: Sequence[Sequence[float]],
    clusters: Sequence[Any],
    R: Sequence[Sequence[float]] | Sequence[float],
    q: Sequence[float] | float | None = None,
    *,
    B: int = 999,
    seed: int = 20260613,
    weight_scheme: str = "rademacher",
) -> dict[str, Any]:
    """Run a null-imposed wild cluster Wald/F test for linear restrictions.

    The bootstrap samples are generated from restricted-model residuals, so this
    is intentionally distinct from unrestricted residual wild bootstrap.
    """

    import numpy as np

    try:
        y_arr = _as_1d_float(y, name="y")
        X_arr = _as_2d_float(X, name="X")
        R_arr = np.asarray(R, dtype=float)
        if R_arr.ndim == 1:
            R_arr = R_arr.reshape(1, -1)
        if R_arr.ndim != 2 or R_arr.size == 0 or not np.isfinite(R_arr).all():
            raise ValueError("R must be a finite non-empty restriction vector or matrix.")
    except ValueError as exc:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_INPUT",
            message=str(exc),
        )
    n, k = X_arr.shape
    if y_arr.shape[0] != n or len(clusters) != n:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="y, X, and clusters must have the same observation count.",
        )
    if R_arr.shape[1] != k:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="R must have one column per regressor in X.",
        )
    if n <= k or np.linalg.matrix_rank(X_arr) < k:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_RANK_DEFICIENT_DESIGN",
            message="The design matrix is rank deficient or has no residual degrees of freedom.",
        )
    if B < 20:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_TOO_FEW_BOOTSTRAP_DRAWS",
            message="Null-imposed WCR requires at least 20 bootstrap draws.",
            extra={"B": int(B)},
        )

    groups = np.asarray([str(item) for item in clusters], dtype=object)
    unique_groups = np.unique(groups)
    if len(unique_groups) < 3:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="result_missing",
            available=False,
            error_code="W3_TOO_FEW_CLUSTERS",
            message="Null-imposed WCR requires at least 3 clusters.",
            extra={"cluster_count": int(len(unique_groups))},
        )

    q_arr = np.zeros(R_arr.shape[0], dtype=float) if q is None else np.asarray(q, dtype=float).reshape(-1)
    if q_arr.shape[0] != R_arr.shape[0] or not np.isfinite(q_arr).all():
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="q must have one value per row of R.",
        )

    xtx_inv = np.linalg.pinv(X_arr.T @ X_arr)
    beta_hat = xtx_inv @ X_arr.T @ y_arr
    restriction_cov = R_arr @ xtx_inv @ R_arr.T
    if np.linalg.matrix_rank(restriction_cov) < R_arr.shape[0]:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_SINGULAR_RESTRICTION",
            message="R (X'X)^-1 R' is singular; the restriction is not estimable.",
        )
    beta_tilde = beta_hat - xtx_inv @ R_arr.T @ np.linalg.pinv(restriction_cov) @ (R_arr @ beta_hat - q_arr)
    resid_hat = y_arr - X_arr @ beta_hat
    v_hat = _cluster_covariance(X_arr, resid_hat, groups, xtx_inv)
    wald_cov = R_arr @ v_hat @ R_arr.T
    if np.linalg.matrix_rank(wald_cov) < R_arr.shape[0]:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_SINGULAR_WALD_COVARIANCE",
            message="Cluster covariance for the tested restriction is singular.",
        )
    diff = R_arr @ beta_hat - q_arr
    constraint_rank = int(R_arr.shape[0])
    f_obs = float(diff.T @ np.linalg.pinv(wald_cov) @ diff / constraint_rank)
    if not math.isfinite(f_obs):
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_STATISTIC",
            message="Observed restriction statistic is not finite.",
        )

    scheme = str(weight_scheme).strip().lower()
    rng = np.random.default_rng(seed)
    exceed = 0
    successful = 0
    resid_tilde = y_arr - X_arr @ beta_tilde
    for _ in range(int(B)):
        if scheme == "rademacher":
            draws = rng.choice([-1.0, 1.0], size=len(unique_groups))
        elif scheme == "webb":
            draws = rng.choice(
                [-math.sqrt(1.5), -1.0, -math.sqrt(0.5), math.sqrt(0.5), 1.0, math.sqrt(1.5)],
                size=len(unique_groups),
            )
        else:
            return canonical_backend_result(
                backend="w3_null_imposed_wcr",
                status="unsupported",
                available=False,
                error_code="W3_UNSUPPORTED_WEIGHT_SCHEME",
                message=f"Unsupported wild cluster weight scheme: {weight_scheme}",
            )
        draw_by_group = dict(zip(unique_groups, draws))
        u_star = np.asarray([draw_by_group[group] for group in groups], dtype=float) * resid_tilde
        y_star = X_arr @ beta_tilde + u_star
        beta_star = xtx_inv @ X_arr.T @ y_star
        resid_star = y_star - X_arr @ beta_star
        v_star = _cluster_covariance(X_arr, resid_star, groups, xtx_inv)
        boot_cov = R_arr @ v_star @ R_arr.T
        if np.linalg.matrix_rank(boot_cov) < R_arr.shape[0]:
            continue
        boot_diff = R_arr @ beta_star - q_arr
        f_boot = float(boot_diff.T @ np.linalg.pinv(boot_cov) @ boot_diff / constraint_rank)
        if not math.isfinite(f_boot):
            continue
        successful += 1
        if f_boot >= f_obs:
            exceed += 1
    if successful < 20:
        return canonical_backend_result(
            backend="w3_null_imposed_wcr",
            status="result_missing",
            available=False,
            error_code="W3_TOO_FEW_VALID_BOOTSTRAP_DRAWS",
            message="Too few valid null-imposed bootstrap draws were produced.",
            extra={"requested_B": int(B), "successful_B": int(successful)},
        )

    warnings: list[dict[str, Any]] = []
    if len(unique_groups) <= 10:
        warnings.append(
            {
                "code": "W3_FEW_CLUSTERS",
                "message": f"Null-imposed WCR ran with G={len(unique_groups)} clusters; finite-sample inference remains fragile.",
            }
        )
    if successful < B:
        warnings.append(
            {
                "code": "W3_BOOTSTRAP_DRAWS_DROPPED",
                "message": f"{B - successful} bootstrap draws had singular covariance and were dropped.",
            }
        )
    p_value = float((1 + exceed) / (1 + successful))
    return canonical_backend_result(
        backend="w3_null_imposed_wcr",
        status="ok",
        available=True,
        message="Null-imposed wild cluster test completed.",
        extra={
            "constraint_rank": constraint_rank,
            "F_obs": f_obs,
            "p_value": p_value,
            "B": int(B),
            "successful_B": int(successful),
            "cluster_count": int(len(unique_groups)),
            "weight_scheme": scheme,
            "seed": int(seed),
            "warnings": warnings,
            "null_imposed": True,
        },
    )


def _kernel_weight(x: float, kernel: str) -> float:
    if x < 0:
        return 0.0
    if kernel in {"triangular", "bartlett"}:
        return max(0.0, 1.0 - x) if x <= 1.0 else 0.0
    if kernel == "uniform":
        return 1.0 if x <= 1.0 else 0.0
    if kernel in {"quadratic", "biweight"}:
        return (1.0 - x * x) ** 2 if x <= 1.0 else 0.0
    raise ValueError(f"Unsupported kernel: {kernel}")


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return float(2 * radius * math.asin(min(1.0, math.sqrt(a))))


def conley_covariance(
    X: Sequence[Sequence[float]],
    y: Sequence[float],
    lon: Sequence[float],
    lat: Sequence[float],
    *,
    time: Sequence[float] | None = None,
    theta_km: float,
    time_bandwidth: float | None = None,
    spatial_kernel: str = "triangular",
    time_kernel: str = "bartlett",
    terms: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Compute a full Conley-style spatial or spatial-time HAC covariance."""

    import numpy as np

    try:
        X_arr = _as_2d_float(X, name="X")
        y_arr = _as_1d_float(y, name="y")
        lon_arr = _as_1d_float(lon, name="lon")
        lat_arr = _as_1d_float(lat, name="lat")
    except ValueError as exc:
        return canonical_backend_result(
            backend="w3_conley",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_INPUT",
            message=str(exc),
        )
    n, k = X_arr.shape
    if y_arr.shape[0] != n or lon_arr.shape[0] != n or lat_arr.shape[0] != n:
        return canonical_backend_result(
            backend="w3_conley",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="X, y, lon, and lat must have the same observation count.",
        )
    if n <= k or np.linalg.matrix_rank(X_arr) < k:
        return canonical_backend_result(
            backend="w3_conley",
            status="invalid_result",
            available=False,
            error_code="W3_RANK_DEFICIENT_DESIGN",
            message="The design matrix is rank deficient or has no residual degrees of freedom.",
        )
    if theta_km <= 0 or not math.isfinite(float(theta_km)):
        return canonical_backend_result(
            backend="w3_conley",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_BANDWIDTH",
            message="theta_km must be positive and finite.",
        )
    time_arr = None
    if time is not None:
        try:
            time_arr = _as_1d_float(time, name="time")
        except ValueError as exc:
            return canonical_backend_result(
                backend="w3_conley",
                status="invalid_result",
                available=False,
                error_code="W3_INVALID_INPUT",
                message=str(exc),
            )
        if time_arr.shape[0] != n:
            return canonical_backend_result(
                backend="w3_conley",
                status="invalid_result",
                available=False,
                error_code="W3_DIMENSION_MISMATCH",
                message="time must have the same observation count as X and y.",
            )
        if time_bandwidth is None or time_bandwidth <= 0 or not math.isfinite(float(time_bandwidth)):
            return canonical_backend_result(
                backend="w3_conley",
                status="invalid_result",
                available=False,
                error_code="W3_INVALID_TIME_BANDWIDTH",
                message="time_bandwidth must be positive when time is provided.",
            )

    try:
        _kernel_weight(0.0, spatial_kernel)
        _kernel_weight(0.0, time_kernel)
    except ValueError as exc:
        return canonical_backend_result(
            backend="w3_conley",
            status="unsupported",
            available=False,
            error_code="W3_UNSUPPORTED_KERNEL",
            message=str(exc),
        )

    xtx_inv = np.linalg.pinv(X_arr.T @ X_arr)
    beta = xtx_inv @ X_arr.T @ y_arr
    resid = y_arr - X_arr @ beta
    meat = np.zeros((k, k), dtype=float)
    used_pairs = 0
    for i in range(n):
        for j in range(n):
            dist = _haversine_km(float(lat_arr[i]), float(lon_arr[i]), float(lat_arr[j]), float(lon_arr[j]))
            ws = _kernel_weight(dist / float(theta_km), spatial_kernel)
            if ws == 0.0:
                continue
            wt = 1.0
            if time_arr is not None:
                dt = abs(float(time_arr[i]) - float(time_arr[j]))
                wt = _kernel_weight(dt / float(time_bandwidth), time_kernel)
                if wt == 0.0:
                    continue
            weight = ws * wt
            meat += weight * np.outer(X_arr[i, :] * resid[i], X_arr[j, :] * resid[j])
            used_pairs += 1
    covariance = xtx_inv @ meat @ xtx_inv
    covariance = (covariance + covariance.T) / 2
    diag = np.diag(covariance)
    if not np.isfinite(covariance).all() or (diag < -1e-10).any():
        return canonical_backend_result(
            backend="w3_conley",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_COVARIANCE",
            message="Conley covariance is non-finite or has negative diagonal entries.",
        )
    stderr = np.sqrt(np.maximum(diag, 0.0))
    names = list(terms or [f"x{i}" for i in range(k)])
    if len(names) != k:
        names = [f"x{i}" for i in range(k)]
    rows = []
    for name, coef, se in zip(names, beta, stderr):
        t_stat = float(coef / se) if se > 0 else math.nan
        rows.append(
            {
                "term": str(name),
                "coef": float(coef),
                "std_error": float(se),
                "t_stat": t_stat,
                "p_value": _normal_pvalue(t_stat),
                "se_type": "conley_full",
                "spatial_kernel": spatial_kernel,
                "time_kernel": time_kernel if time_arr is not None else None,
                "theta_km": float(theta_km),
                "time_bandwidth": float(time_bandwidth) if time_arr is not None else None,
            }
        )
    return canonical_backend_result(
        backend="w3_conley",
        status="ok",
        available=True,
        message="Full Conley covariance completed.",
        extra={
            "is_full_conley": True,
            "covariance": covariance.tolist(),
            "beta": beta.tolist(),
            "rows": rows,
            "n_obs": int(n),
            "n_pairs_used": int(used_pairs),
            "spatial_kernel": spatial_kernel,
            "time_kernel": time_kernel if time_arr is not None else None,
            "theta_km": float(theta_km),
            "time_bandwidth": float(time_bandwidth) if time_arr is not None else None,
        },
    )


def romano_wolf_stepdown(
    stat_vector: Sequence[float],
    bootstrap_draws: Sequence[Sequence[float]],
    *,
    labels: Sequence[str] | None = None,
    alpha: float = 0.05,
    family_id: str = "family",
) -> dict[str, Any]:
    """Adjust p-values with the Romano-Wolf max-stat stepdown algorithm."""

    import numpy as np

    try:
        stat = _as_1d_float(stat_vector, name="stat_vector")
        draws = _as_2d_float(bootstrap_draws, name="bootstrap_draws")
    except ValueError as exc:
        return canonical_backend_result(
            backend="w3_romano_wolf",
            status="invalid_result",
            available=False,
            error_code="W3_INVALID_INPUT",
            message=str(exc),
        )
    b_count, m = draws.shape
    if stat.shape[0] != m:
        return canonical_backend_result(
            backend="w3_romano_wolf",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="bootstrap_draws must have one column per observed statistic.",
        )
    if b_count < 20:
        return canonical_backend_result(
            backend="w3_romano_wolf",
            status="invalid_result",
            available=False,
            error_code="W3_TOO_FEW_BOOTSTRAP_DRAWS",
            message="Romano-Wolf requires at least 20 bootstrap draws.",
            extra={"B": int(b_count)},
        )
    label_list = [str(item) for item in (labels or [f"h{i}" for i in range(m)])]
    if len(label_list) != m:
        return canonical_backend_result(
            backend="w3_romano_wolf",
            status="invalid_result",
            available=False,
            error_code="W3_DIMENSION_MISMATCH",
            message="labels must have one entry per observed statistic.",
        )
    abs_stat = np.abs(stat)
    abs_draws = np.abs(draws)
    order = np.argsort(-abs_stat)
    p_raw = np.asarray([(1 + np.sum(abs_draws[:, h] >= abs_stat[h])) / (b_count + 1) for h in range(m)], dtype=float)
    ordered_step = []
    for pos, h in enumerate(order):
        remaining = order[pos:]
        max_draw = np.max(abs_draws[:, remaining], axis=1)
        ordered_step.append(float((1 + np.sum(max_draw >= abs_stat[h])) / (b_count + 1)))
    ordered_adj = np.maximum.accumulate(np.asarray(ordered_step, dtype=float))
    p_adj = np.zeros(m, dtype=float)
    order_rank = np.zeros(m, dtype=int)
    for rank, h in enumerate(order):
        p_adj[h] = max(float(p_raw[h]), float(ordered_adj[rank]))
        order_rank[h] = rank + 1
    rows = [
        {
            "label": label_list[i],
            "stat_obs": float(stat[i]),
            "p_raw": float(p_raw[i]),
            "p_adj": float(min(1.0, p_adj[i])),
            "rejected": bool(p_adj[i] <= alpha),
            "order": int(order_rank[i]),
            "family_id": family_id,
        }
        for i in range(m)
    ]
    warnings = []
    if b_count < 100:
        warnings.append(
            {
                "code": "W3_FEW_BOOTSTRAP_DRAWS",
                "message": f"Romano-Wolf ran with B={b_count}; adjusted p-values are coarse.",
            }
        )
    return canonical_backend_result(
        backend="w3_romano_wolf",
        status="ok",
        available=True,
        message="Romano-Wolf stepdown adjustment completed.",
        extra={
            "B": int(b_count),
            "m": int(m),
            "alpha": float(alpha),
            "family_id": family_id,
            "rows": rows,
            "order": [int(item) for item in order.tolist()],
            "warnings": warnings,
        },
    )


def validate_mop_effective_f_artifact(
    *,
    effective_f: float | None,
    critical_value: float | None,
    estimator: str = "TSLS",
    tau: float = 0.10,
    source_backend: str | None = None,
) -> dict[str, Any]:
    """Validate a backend-produced Montiel-Olea-Pflueger effective-F artifact.

    This intentionally does not relabel a generic first-stage F statistic as MOP.
    A release-level MOP claim requires a backend or audited implementation that
    supplies both the effective F statistic and the matching critical value.
    """

    if effective_f is None or critical_value is None:
        return canonical_backend_result(
            backend="w3_mop_effective_f",
            status="result_missing",
            available=False,
            error_code="MOP_EFFECTIVE_F_MISSING",
            message="MOP certification requires both effective_f and the matching critical_value.",
            extra={"mop_effective_f_certified": False},
        )
    try:
        f_value = float(effective_f)
        c_value = float(critical_value)
    except (TypeError, ValueError):
        return canonical_backend_result(
            backend="w3_mop_effective_f",
            status="invalid_result",
            available=False,
            error_code="MOP_EFFECTIVE_F_INVALID",
            message="effective_f and critical_value must be numeric.",
            extra={"mop_effective_f_certified": False},
        )
    if not math.isfinite(f_value) or not math.isfinite(c_value) or f_value < 0 or c_value <= 0:
        return canonical_backend_result(
            backend="w3_mop_effective_f",
            status="invalid_result",
            available=False,
            error_code="MOP_EFFECTIVE_F_INVALID",
            message="effective_f must be non-negative and critical_value must be positive.",
            extra={"mop_effective_f_certified": False},
        )
    return canonical_backend_result(
        backend="w3_mop_effective_f",
        status="ok",
        available=True,
        message="Backend-produced MOP effective-F artifact is complete.",
        extra={
            "effective_f": f_value,
            "critical_value": c_value,
            "weak_iv_flag": bool(f_value < c_value),
            "estimator": str(estimator),
            "tau": float(tau),
            "source_backend": source_backend,
            "mop_effective_f_certified": True,
        },
    )
