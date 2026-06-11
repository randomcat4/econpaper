from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_yaml_or_json(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyYAML is required to read data_contract.yaml.") from exc
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("data contract must be a mapping/object.")
    return data


def load_data_contract(path: str | Path) -> dict[str, Any]:
    return _load_yaml_or_json(Path(path))


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(item) for item in value]


def required_columns(contract: dict[str, Any]) -> list[str]:
    panel = contract.get("panel") if isinstance(contract.get("panel"), dict) else {}
    spatial = contract.get("spatial") if isinstance(contract.get("spatial"), dict) else {}
    columns = [
        panel.get("unit_id"),
        panel.get("time_id"),
        panel.get("outcome"),
        panel.get("treatment"),
        panel.get("first_treat_year"),
        spatial.get("longitude"),
        spatial.get("latitude"),
    ]
    columns.extend(_listify(panel.get("covariates")))
    return [str(col) for col in columns if col]


def validate_data_contract(
    contract: dict[str, Any],
    df: Any,
    *,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    base = Path(base_dir or ".")
    panel = contract.get("panel") if isinstance(contract.get("panel"), dict) else {}
    spatial = contract.get("spatial") if isinstance(contract.get("spatial"), dict) else {}

    columns = set(map(str, getattr(df, "columns", [])))
    missing = [col for col in required_columns(contract) if col not in columns]
    if missing:
        errors.append(
            {
                "code": "missing_columns",
                "message": f"Data is missing columns required by data contract: {missing}",
                "columns": missing,
            }
        )

    unit = panel.get("unit_id")
    time = panel.get("time_id")
    if unit and time and unit in columns and time in columns:
        duplicated = int(df.duplicated([unit, time]).sum())
        if duplicated:
            errors.append(
                {
                    "code": "id_time_not_unique",
                    "message": f"{duplicated} duplicated unit-time rows found.",
                    "columns": [unit, time],
                }
            )

    for role in ("outcome", "treatment"):
        col = panel.get(role)
        if col and col in columns:
            missing_count = int(df[col].isna().sum())
            if missing_count:
                errors.append(
                    {
                        "code": f"{role}_missing",
                        "message": f"{missing_count} rows have missing {role} values.",
                        "column": col,
                    }
                )

    treatment = panel.get("treatment")
    first_treat = panel.get("first_treat_year")
    if treatment and first_treat and treatment in columns and first_treat in columns and time in columns:
        try:
            import pandas as pd

            frame = df[[unit, time, treatment, first_treat]].copy() if unit in columns else df[[time, treatment, first_treat]].copy()
            frame["_s4e_time"] = pd.to_numeric(frame[time], errors="coerce")
            frame["_s4e_treat"] = pd.to_numeric(frame[treatment], errors="coerce")
            frame["_s4e_first"] = pd.to_numeric(frame[first_treat], errors="coerce")
            inconsistent = int(
                (
                    (frame["_s4e_first"].fillna(0) > 0)
                    & (frame["_s4e_time"] >= frame["_s4e_first"])
                    & (frame["_s4e_treat"] != 1)
                ).sum()
            )
            if inconsistent:
                warnings.append(
                    {
                        "code": "first_treat_year_inconsistent",
                        "message": f"{inconsistent} post-adoption rows are not coded as treated.",
                    }
                )
        except Exception as exc:
            warnings.append(
                {
                    "code": "first_treat_year_check_failed",
                    "message": str(exc),
                }
            )

    for role, bounds in {"longitude": (-180, 180), "latitude": (-90, 90)}.items():
        col = spatial.get(role)
        if col and col in columns:
            try:
                import pandas as pd

                numeric = pd.to_numeric(df[col], errors="coerce")
            except Exception:
                numeric = df[col]
            out_of_bounds = int(((numeric < bounds[0]) | (numeric > bounds[1])).sum())
            if out_of_bounds:
                errors.append(
                    {
                        "code": f"{role}_out_of_bounds",
                        "message": f"{out_of_bounds} {role} values are outside {bounds}.",
                        "column": col,
                    }
                )

    for item in spatial.get("weights") or []:
        if not isinstance(item, dict):
            continue
        value = item.get("path")
        if not value:
            errors.append({"code": "spatial_weight_path_missing", "message": "A spatial weight recipe is missing path."})
            continue
        path = Path(str(value))
        if not path.is_absolute():
            path = base / path
        if not path.exists():
            errors.append(
                {
                    "code": "spatial_weight_path_not_found",
                    "message": f"Spatial weight file does not exist: {path}",
                    "path": str(path),
                }
            )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "required_columns": required_columns(contract),
    }


def write_validated_contract(path: Path, contract: dict[str, Any], validation: dict[str, Any]) -> None:
    payload = dict(contract)
    payload["_skill4econ_validation"] = validation
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml

        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    except Exception:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_contract_errors(path: Path, validation: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
