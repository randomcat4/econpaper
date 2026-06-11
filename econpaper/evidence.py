from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EVIDENCE_VERSION = "v3.0"

STAT_COLUMNS = {
    "coef": ("coefficient", "coefficient"),
    "coefficient": ("coefficient", "coefficient"),
    "estimate": ("coefficient", "coefficient"),
    "effect": ("coefficient", "coefficient"),
    "std_error": ("standard_error", "standard_error"),
    "standard_error": ("standard_error", "standard_error"),
    "se": ("standard_error", "standard_error"),
    "p_value": ("p_value", "p_value"),
    "pvalue": ("p_value", "p_value"),
    "p": ("p_value", "p_value"),
    "t_stat": ("t_stat", "t_stat"),
    "z_stat": ("t_stat", "t_stat"),
    "t": ("t_stat", "t_stat"),
    "n": ("n", "n"),
    "nobs": ("n", "n"),
    "n_obs": ("n", "n"),
    "N": ("n", "n"),
}

SUMMARY_COLUMNS = {
    "mean": ("mean", "mean"),
    "sd": ("sd", "sd"),
    "std": ("sd", "sd"),
    "standard_deviation": ("sd", "sd"),
}


@dataclass
class EvidenceIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class EvidenceBuildResult:
    ledger: dict[str, Any]
    magnitude_semantics: dict[str, Any]
    status: str = "passed"
    issues: list[EvidenceIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(EvidenceIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": EVIDENCE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "ledger": self.ledger,
            "magnitude_semantics": self.magnitude_semantics,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def build_evidence_ledger(
    *,
    run_dir: str | Path,
    intake_profile_path: str | Path | None = None,
    model_table_paths: list[str | Path] | None = None,
    summary_stats_path: str | Path | None = None,
) -> EvidenceBuildResult:
    run_path = Path(run_dir)
    result = EvidenceBuildResult(
        ledger={
            "version": EVIDENCE_VERSION,
            "run_id": _run_id(run_path),
            "artifacts": [],
            "evidence_items": [],
            "variable_semantics": {},
        },
        magnitude_semantics={},
    )
    if not run_path.exists():
        result.add_issue("run_dir_missing", "hard_block", f"Run directory does not exist: {run_path}", str(run_path))
        return result

    model_tables = [Path(path) for path in model_table_paths] if model_table_paths else _discover_model_tables(run_path)
    if not model_tables:
        result.add_issue(
            "structured_model_table_missing",
            "hard_block",
            "No structured model_table.csv or model_table.json was found; table paths alone are not evidence.",
            str(run_path),
        )
    for path in model_tables:
        _ingest_model_table(path, run_path, result)

    intake_profile = _load_optional_json(Path(intake_profile_path), result) if intake_profile_path else {}
    result.ledger["variable_semantics"] = _variable_semantics_from_intake(intake_profile, result)

    summary_path = Path(summary_stats_path) if summary_stats_path else _discover_summary_stats(run_path)
    if summary_path:
        _ingest_summary_stats(summary_path, run_path, result)

    result.magnitude_semantics = _build_magnitude_semantics(result.ledger)
    return result


def write_evidence_ledger(
    *,
    run_dir: str | Path,
    out_dir: str | Path,
    intake_profile_path: str | Path | None = None,
    model_table_paths: list[str | Path] | None = None,
    summary_stats_path: str | Path | None = None,
) -> EvidenceBuildResult:
    result = build_evidence_ledger(
        run_dir=run_dir,
        intake_profile_path=intake_profile_path,
        model_table_paths=model_table_paths,
        summary_stats_path=summary_stats_path,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    ledger_text = json.dumps(result.ledger, ensure_ascii=False, indent=2)
    (out_path / "evidence_ledger.json").write_text(ledger_text, encoding="utf-8")
    (internal / "evidence_ledger.json").write_text(ledger_text, encoding="utf-8")
    (internal / "evidence_ledger_build.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "magnitude_semantics.json").write_text(
        json.dumps(result.magnitude_semantics, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _run_id(run_dir: Path) -> str:
    for filename in ["status.json", "manifest.json", "audit.json"]:
        path = run_dir / filename
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if isinstance(payload, dict) and payload.get("run_id"):
            return str(payload["run_id"])
    return run_dir.name


def _discover_model_tables(run_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    manifest_path = run_dir / "artifact_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        except Exception:
            manifest = {}
        for item in manifest.get("artifacts", []) if isinstance(manifest, dict) else []:
            if not isinstance(item, dict):
                continue
            rel = str(item.get("path") or "")
            artifact_type = str(item.get("type") or item.get("artifact_type") or "").lower()
            if "model_table" not in rel.lower() and "model_table" not in artifact_type:
                continue
            path = run_dir / rel
            if path.suffix.lower() in {".csv", ".json"} and path.exists():
                candidates.append(path)
    for pattern in ["model_table.csv", "model_table.json", "**/model_table.csv", "**/model_table.json"]:
        candidates.extend(run_dir.glob(pattern))
    return _unique_paths(candidates)


def _discover_summary_stats(run_dir: Path) -> Path | None:
    for rel in [
        "summary_stats.csv",
        "summary_statistics.csv",
        "tables/summary_stats.csv",
        "tables/summary_statistics.csv",
        "summary_stats.json",
        "summary_statistics.json",
    ]:
        path = run_dir / rel
        if path.exists():
            return path
    return None


def _unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def _ingest_model_table(path: Path, run_dir: Path, result: EvidenceBuildResult) -> None:
    if not path.exists():
        result.add_issue("model_table_missing", "hard_block", f"Model table does not exist: {path}", str(path))
        return
    rows = _read_table_rows(path, result)
    artifact_id = _artifact_id("model_table", path, run_dir)
    result.ledger["artifacts"].append(
        {
            "artifact_id": artifact_id,
            "artifact_type": "model_table",
            "path": _relative_path(path, run_dir),
            "hash": _file_hash(path),
            "claimable": bool(rows),
        }
    )
    if not rows:
        result.add_issue("model_table_no_rows", "hard_block", "Structured model table contains no rows.", str(path))
        return
    before = len(result.ledger["evidence_items"])
    for idx, row in enumerate(rows, start=1):
        _row_to_evidence_items(row, idx, artifact_id, path, run_dir, result)
    if len(result.ledger["evidence_items"]) == before:
        result.add_issue(
            "model_table_no_numeric_cells",
            "hard_block",
            "Structured model table contained rows but no supported numeric cells.",
            str(path),
        )


def _read_table_rows(path: Path, result: EvidenceBuildResult) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        except Exception as exc:
            result.add_issue("model_table_parse_failed", "hard_block", f"Could not parse model table CSV: {exc}", str(path))
            return []
    if suffix == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            result.add_issue("model_table_parse_failed", "hard_block", f"Could not parse model table JSON: {exc}", str(path))
            return []
        return _json_payload_to_rows(payload)
    result.add_issue("unsupported_model_table_type", "hard_block", f"Unsupported model table type: {path.suffix}", str(path))
    return []


def _json_payload_to_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ["rows", "model_table", "coefficients", "coef_table"]:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    rows: list[dict[str, Any]] = []
    main_effect = payload.get("main_effect")
    if isinstance(main_effect, dict):
        rows.append(
            {
                "term": main_effect.get("term") or main_effect.get("label") or "main_effect",
                "coef": _first_present(main_effect, ["estimate", "coef"]),
                "std_error": main_effect.get("std_error"),
                "p_value": main_effect.get("p_value"),
                "model_id": _first_present(payload, ["estimator", "method", "model_id"]),
                "sample_id": payload.get("sample_id"),
                "n_obs": _first_present(payload, ["n_obs", "nobs", "N"]),
            }
        )
    return rows


def _row_to_evidence_items(
    row: dict[str, Any],
    row_idx: int,
    artifact_id: str,
    path: Path,
    run_dir: Path,
    result: EvidenceBuildResult,
) -> None:
    term = _first_present(row, ["term", "variable", "row", "label"]) or f"row_{row_idx}"
    model_id = str(_first_present(row, ["model_id", "model", "estimator", "spec_id"]) or path.stem)
    sample_id = _first_present(row, ["sample_id", "sample", "sample_name"])
    diagnostic_status = _first_present(row, ["diagnostic_status", "status", "claim_level"])
    for column, (statistic, display_type) in STAT_COLUMNS.items():
        if column not in row:
            continue
        value = _coerce_number(row.get(column))
        if value is None:
            continue
        evidence_id = _evidence_id(artifact_id, row_idx, statistic, column)
        result.ledger["evidence_items"].append(
            {
                "evidence_id": evidence_id,
                "artifact_id": artifact_id,
                "model_id": model_id,
                "sample_id": str(sample_id) if sample_id not in {None, ""} else None,
                "row": str(term),
                "column": column,
                "cell_ref": f"{_relative_path(path, run_dir)}#row={row_idx};column={column}",
                "statistic": statistic,
                "value": value,
                "display_type": display_type,
                "variable": str(term),
                "diagnostic_status": str(diagnostic_status) if diagnostic_status not in {None, ""} else None,
                "provenance_hash": _provenance_hash(path, row_idx, column, value),
            }
        )


def _ingest_summary_stats(path: Path, run_dir: Path, result: EvidenceBuildResult) -> None:
    if not path.exists():
        result.add_issue("summary_stats_missing", "flag_and_confirm", f"Summary stats file does not exist: {path}", str(path))
        return
    rows = _read_table_rows(path, result)
    artifact_id = _artifact_id("summary_stats", path, run_dir)
    result.ledger["artifacts"].append(
        {
            "artifact_id": artifact_id,
            "artifact_type": "summary_stats",
            "path": _relative_path(path, run_dir),
            "hash": _file_hash(path),
            "claimable": bool(rows),
        }
    )
    for idx, row in enumerate(rows, start=1):
        variable = str(_first_present(row, ["variable", "term", "name", "row"]) or f"variable_{idx}")
        semantics = result.ledger["variable_semantics"].setdefault(
            variable,
            {
                "label": variable,
                "unit": None,
                "scale": None,
                "mean": None,
                "sd": None,
                "standardization": None,
                "transformation": None,
                "winsorization": None,
                "source": None,
            },
        )
        unit = _first_present(row, ["unit", "units"])
        if unit:
            semantics["unit"] = str(unit)
        for column, (statistic, display_type) in SUMMARY_COLUMNS.items():
            if column not in row:
                continue
            value = _coerce_number(row.get(column))
            if value is None:
                continue
            semantics[statistic] = value
            semantics["source"] = _relative_path(path, run_dir)
            result.ledger["evidence_items"].append(
                {
                    "evidence_id": _evidence_id(artifact_id, idx, statistic, column),
                    "artifact_id": artifact_id,
                    "model_id": "summary_stats",
                    "sample_id": str(_first_present(row, ["sample_id", "sample"]) or "") or None,
                    "row": variable,
                    "column": column,
                    "cell_ref": f"{_relative_path(path, run_dir)}#row={idx};column={column}",
                    "statistic": statistic,
                    "value": value,
                    "display_type": display_type,
                    "variable": variable,
                    "diagnostic_status": None,
                    "provenance_hash": _provenance_hash(path, idx, column, value),
                }
            )


def _variable_semantics_from_intake(intake_profile: dict[str, Any], result: EvidenceBuildResult) -> dict[str, dict[str, Any]]:
    semantics: dict[str, dict[str, Any]] = {}
    entries = intake_profile.get("outcome_magnitude_context", []) if isinstance(intake_profile, dict) else []
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        variable = str(entry.get("variable") or "").strip()
        if not variable or variable.startswith("[AUTHOR_INPUT_NEEDED]"):
            continue
        semantics[variable] = {
            "label": variable,
            "unit": entry.get("unit"),
            "scale": entry.get("scale"),
            "mean": _coerce_number(entry.get("mean")),
            "sd": _coerce_number(entry.get("sd")),
            "standardization": entry.get("standardization"),
            "transformation": entry.get("transformation"),
            "winsorization": entry.get("winsorization"),
            "source": "intake_profile",
            "meaningful_benchmark": entry.get("meaningful_benchmark"),
        }
    if not semantics:
        result.add_issue(
            "variable_semantics_missing",
            "flag_and_confirm",
            "No outcome magnitude context was available; main Results magnitude interpretation will need author input.",
        )
    return semantics


def _build_magnitude_semantics(ledger: dict[str, Any]) -> dict[str, Any]:
    variables: dict[str, dict[str, Any]] = {}
    for variable, semantics in ledger.get("variable_semantics", {}).items():
        missing = [
            field
            for field in ["unit", "mean", "sd"]
            if semantics.get(field) in {None, "", "[AUTHOR_INPUT_NEEDED]"}
        ]
        variables[variable] = {
            "unit": semantics.get("unit"),
            "mean": semantics.get("mean"),
            "sd": semantics.get("sd"),
            "meaningful_benchmark": semantics.get("meaningful_benchmark"),
            "ready_for_magnitude_interpretation": not missing,
            "missing": missing,
        }
    return {
        "version": EVIDENCE_VERSION,
        "variables": variables,
        "ready_variables": sorted([key for key, value in variables.items() if value["ready_for_magnitude_interpretation"]]),
        "missing_variables": sorted([key for key, value in variables.items() if not value["ready_for_magnitude_interpretation"]]),
    }


def _load_optional_json(path: Path, result: EvidenceBuildResult) -> dict[str, Any]:
    if not path.exists():
        result.add_issue("intake_profile_missing", "flag_and_confirm", f"Intake profile does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue("intake_profile_invalid", "flag_and_confirm", f"Could not parse intake profile: {exc}", str(path))
        return {}
    return payload if isinstance(payload, dict) else {}


def _first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return value
    return None


def _coerce_number(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return value
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if not stripped or stripped.lower() in {"nan", "na", "n/a", "none", "."}:
            return None
        if stripped.endswith("%"):
            stripped = stripped[:-1].strip()
        try:
            parsed = float(stripped)
        except ValueError:
            return None
        return int(parsed) if parsed.is_integer() and not re.search(r"[.eE]", stripped) else parsed
    return None


def _artifact_id(kind: str, path: Path, run_dir: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", _relative_path(path, run_dir).replace(".", "_")).strip("_")
    return f"{kind}_{stem or 'artifact'}"


def _evidence_id(artifact_id: str, row_idx: int, statistic: str, column: str) -> str:
    raw = f"ev_{artifact_id}_{row_idx}_{statistic}_{column}"
    return re.sub(r"[^A-Za-z0-9_]+", "_", raw).strip("_")


def _relative_path(path: Path, run_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(run_dir.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _provenance_hash(path: Path, row_idx: int, column: str, value: float | int) -> str:
    raw = f"{path.resolve()}|{row_idx}|{column}|{repr(value)}"
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _author_report_text(result: EvidenceBuildResult) -> str:
    ledger = result.ledger
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    flags = [issue for issue in result.issues if issue.severity == "flag_and_confirm"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Evidence Ledger Status",
        "",
        f"- Status: `{result.status}`",
        f"- Artifacts indexed: `{len(ledger.get('artifacts', []))}`",
        f"- Evidence items: `{len(ledger.get('evidence_items', []))}`",
        f"- Variable semantics: `{len(ledger.get('variable_semantics', {}))}`",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Magnitude Semantics", ""])
    variables = result.magnitude_semantics.get("variables", {})
    if variables:
        for variable, item in variables.items():
            status = "ready" if item["ready_for_magnitude_interpretation"] else "needs author input"
            missing = ", ".join(item["missing"]) if item["missing"] else "none"
            lines.append(f"- `{variable}`: {status}; missing: {missing}")
    else:
        lines.append("- No variable semantics yet.")
    lines.extend(["", "## Flag-And-Confirm Items", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in flags] if flags else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Add a structured `model_table.csv` or `model_table.json`; table/PDF paths alone cannot support numeric claims.")
    elif flags:
        lines.append("- Supply outcome units, means, and standard deviations before writing magnitude interpretations.")
    else:
        lines.append("- Continue to deterministic numeric rendering and claim-ledger construction.")
    return "\n".join(lines) + "\n"
