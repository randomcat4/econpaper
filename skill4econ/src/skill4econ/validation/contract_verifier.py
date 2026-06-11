from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..contracts.claim_levels import CLAIM_LEVEL_VALUES, PAPER_READINESS_VALUES
from ..contracts.risk_registry import invalid_risk_codes
from ..contracts.run_status import RUN_STATUS_VALUES
from .schema_loader import load_schema

try:  # jsonschema is part of the local conda environment; keep verifier import-safe.
    from jsonschema import Draft202012Validator, ValidationError
except Exception:  # pragma: no cover - exercised only on minimal environments.
    Draft202012Validator = None  # type: ignore[assignment]
    ValidationError = Exception  # type: ignore[assignment]


REQUIRED_FILES = [
    "manifest.json",
    "audit.json",
    "reviewer_risk.json",
    "artifact_manifest.json",
    "run_config_resolved.json",
    "run_config_resolved.yaml",
    "run_log.md",
    "run_log.txt",
    "status.json",
    "model_table.csv",
]

JSON_SCHEMAS = {
    "manifest.json": "manifest.schema.json",
    "audit.json": "audit.schema.json",
    "reviewer_risk.json": "reviewer_risk.schema.json",
    "artifact_manifest.json": "artifact_manifest.schema.json",
    "status.json": "status.schema.json",
}


@dataclass
class ValidationIssue:
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass
class ValidationReport:
    run_dir: Path
    strict: bool = False
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    checked_files: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "failed" if self.errors else "passed"

    def error(self, code: str, message: str, path: str | None = None) -> None:
        self.errors.append(ValidationIssue(code, message, path))

    def warn(self, code: str, message: str, path: str | None = None) -> None:
        self.warnings.append(ValidationIssue(code, message, path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "strict": self.strict,
            "run_dir": str(self.run_dir),
            "errors": [item.to_dict() for item in self.errors],
            "warnings": [item.to_dict() for item in self.warnings],
            "checked_files": self.checked_files,
        }


def _load_json(path: Path, report: ValidationReport) -> dict[str, Any]:
    report.checked_files.append(path.name)
    if not path.exists():
        report.error("missing_json", f"Required JSON file is missing: {path.name}", path.name)
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.error("invalid_json", f"Could not parse {path.name}: {exc}", path.name)
        return {}
    if not isinstance(data, dict):
        report.error("json_not_object", f"{path.name} must contain a JSON object.", path.name)
        return {}
    return data


def _validate_json_schema(file_name: str, payload: dict[str, Any], report: ValidationReport) -> None:
    schema_name = JSON_SCHEMAS.get(file_name)
    if not schema_name:
        return
    if Draft202012Validator is None:
        report.warn("schema_validator_unavailable", "jsonschema is unavailable; schema validation skipped.", file_name)
        return
    try:
        schema = load_schema(schema_name)
        Draft202012Validator(schema).validate(payload)
    except ValidationError as exc:
        report.error("schema_validation_failed", f"{file_name} violates {schema_name}: {exc.message}", file_name)
    except Exception as exc:
        report.warn("schema_validation_unavailable", f"Could not validate {file_name} against {schema_name}: {exc}", file_name)


def _risk_codes(reviewer_risk: dict[str, Any]) -> list[str]:
    return [
        str(item.get("code"))
        for item in reviewer_risk.get("risks", [])
        if isinstance(item, dict) and item.get("code")
    ]


def _validate_required_files(run_dir: Path, report: ValidationReport) -> None:
    for name in REQUIRED_FILES:
        report.checked_files.append(name)
        if not (run_dir / name).exists():
            report.error("missing_required_file", f"Required contract artifact is missing: {name}", name)


def _validate_status(status: dict[str, Any], report: ValidationReport) -> None:
    for field_name in [
        "status",
        "method_or_workflow",
        "run_id",
        "engine",
        "claim_level",
        "paper_readiness",
        "main_claim_available",
        "risk_codes",
        "run_dir",
        "rerun_command",
    ]:
        if field_name not in status:
            report.error("status_missing_field", f"status.json missing `{field_name}`.", "status.json")
    if status.get("status") not in RUN_STATUS_VALUES:
        report.error("invalid_run_status", f"Unknown normalized status: {status.get('status')}", "status.json")
    if status.get("claim_level") not in CLAIM_LEVEL_VALUES:
        report.error("invalid_claim_level", f"Unknown claim_level: {status.get('claim_level')}", "status.json")
    if status.get("paper_readiness") not in PAPER_READINESS_VALUES:
        report.error("invalid_paper_readiness", f"Unknown paper_readiness: {status.get('paper_readiness')}", "status.json")
    if status.get("main_claim_available") is True and status.get("claim_level") in {
        "adapter_only",
        "sensitivity_only",
        "failed",
        "skipped",
    }:
        report.error(
            "main_claim_inconsistent",
            "main_claim_available=true is incompatible with adapter/sensitivity/failed/skipped claim_level.",
            "status.json",
        )
    if status.get("paper_readiness") == "paper_ready" and status.get("missing_dependencies"):
        report.error("paper_ready_with_missing_dependency", "paper_ready cannot have missing dependencies.", "status.json")
    if status.get("status") == "failed" and report.strict:
        report.error("strict_failed_run", "Strict validation rejects failed analytic status.", "status.json")


def _validate_reviewer_risk(reviewer_risk: dict[str, Any], status: dict[str, Any], report: ValidationReport) -> None:
    codes = _risk_codes(reviewer_risk)
    invalid = invalid_risk_codes(codes)
    if invalid:
        report.error("unregistered_risk_code", f"Unregistered reviewer risk code(s): {invalid}", "reviewer_risk.json")
    status_codes = set(map(str, status.get("risk_codes") or []))
    reviewer_codes = set(codes)
    if status_codes != reviewer_codes:
        report.error(
            "risk_code_mismatch",
            f"status.json risk_codes {sorted(status_codes)} != reviewer_risk.json codes {sorted(reviewer_codes)}",
            "status.json",
        )
    if status.get("paper_readiness") == "paper_ready":
        degradations = {
            str(item.get("claim_degradation"))
            for item in reviewer_risk.get("risks", [])
            if isinstance(item, dict) and item.get("claim_degradation")
        }
        if {"not_for_claim", "failed"}.intersection(degradations):
            report.error("paper_ready_degraded", "paper_ready run has risk degradation to not_for_claim/failed.", "reviewer_risk.json")
    if status.get("status") == "success":
        fatal_risks = [
            item.get("code")
            for item in reviewer_risk.get("risks", [])
            if isinstance(item, dict)
            and (str(item.get("severity")).lower() == "fatal" or item.get("claim_degradation") == "failed")
        ]
        if fatal_risks:
            report.error(
                "success_with_fatal_risk",
                f"status=success is incompatible with fatal/failed reviewer risk(s): {fatal_risks}",
                "reviewer_risk.json",
            )


def _validate_artifact_manifest(run_dir: Path, artifact_manifest: dict[str, Any], report: ValidationReport) -> None:
    missing = artifact_manifest.get("missing_required_artifacts") or []
    if missing:
        report.error("artifact_manifest_missing_required", f"artifact_manifest reports missing required artifacts: {missing}", "artifact_manifest.json")
    for item in artifact_manifest.get("artifacts") or []:
        if not isinstance(item, dict):
            report.error("artifact_entry_invalid", f"Artifact entry must be object: {item}", "artifact_manifest.json")
            continue
        rel = item.get("path")
        if not rel:
            report.error("artifact_path_missing", f"Artifact entry missing path: {item}", "artifact_manifest.json")
            continue
        path = run_dir / str(rel)
        if not path.exists():
            report.error("artifact_path_not_found", f"artifact_manifest path does not exist: {rel}", str(rel))
        if "required" not in item:
            report.warn("artifact_required_field_missing", f"Artifact entry lacks `required`: {rel}", "artifact_manifest.json")
        if "exists" not in item:
            report.warn("artifact_exists_field_missing", f"Artifact entry lacks `exists`: {rel}", "artifact_manifest.json")
        if "producer" not in item:
            report.warn("artifact_producer_field_missing", f"Artifact entry lacks `producer`: {rel}", "artifact_manifest.json")


def _validate_manifest(manifest: dict[str, Any], status: dict[str, Any], report: ValidationReport) -> None:
    if not (manifest.get("rerun_command") or status.get("rerun_command")):
        report.error("rerun_command_missing", "manifest/status must include rerun_command.", "manifest.json")
    for key in ["claim_level", "paper_readiness", "main_claim_available"]:
        if key in manifest and key in status and manifest.get(key) != status.get(key):
            report.warn("manifest_status_mismatch", f"manifest.{key} != status.{key}", "manifest.json")


def _validate_run_config(run_config: dict[str, Any], report: ValidationReport) -> None:
    if not (run_config.get("spec") is not None or run_config.get("config") is not None):
        report.error(
            "run_config_missing_spec",
            "run_config_resolved.json must include resolved spec/config information.",
            "run_config_resolved.json",
        )
    if not run_config.get("rerun_command"):
        report.warn("run_config_rerun_missing", "run_config_resolved.json lacks rerun_command.", "run_config_resolved.json")


def _read_csv_rows(path: Path, report: ValidationReport) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            return list(reader), list(reader.fieldnames or [])
    except Exception as exc:
        report.error("csv_read_failed", f"Could not read {path.name}: {exc}", path.name)
        return [], []


def _is_numeric_value(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    try:
        float(text)
    except Exception:
        return False
    return True


def _row_has_numeric_estimate(row: dict[str, Any]) -> bool:
    return any(
        _is_numeric_value(row.get(field))
        for field in [
            "coef",
            "estimate",
            "att",
            "effect",
            "direct_effect",
            "indirect_effect",
            "total_effect",
        ]
    )


def _resolve_recorded_path(run_path: Path, value: Any) -> Path | None:
    if value is None or str(value).strip() == "":
        return None
    path = Path(str(value))
    return path if path.is_absolute() else run_path / path


def _validate_model_table(run_path: Path, audit: dict[str, Any], report: ValidationReport) -> None:
    model_table = run_path / "model_table.csv"
    if not model_table.exists():
        return
    text = model_table.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        report.error("model_table_empty", "model_table.csv is empty.", "model_table.csv")
        return
    rows, columns = _read_csv_rows(model_table, report)
    if not (audit.get("method") or audit.get("workflow")):
        report.warn("audit_method_missing", "audit.json lacks method/workflow for model_table provenance comparison.", "audit.json")
    if not audit.get("engine"):
        report.warn("audit_engine_missing", "audit.json lacks engine for model_table provenance comparison.", "audit.json")
    source_columns = {
        "source_path",
        "source_file",
        "source_run_dir",
        "source_model_table",
        "source_artifact",
    }.intersection(set(columns))
    if audit.get("steps") and not source_columns:
        report.warn(
            "model_table_source_columns_missing",
            "Workflow model_table.csv lacks source columns linking rows back to child runs.",
            "model_table.csv",
        )
    for idx, row in enumerate(rows, 2):
        status = str(row.get("status") or "").strip().lower()
        if status in {"failed", "fatal", "missing_dependency", "skipped", "interface_only"} and _row_has_numeric_estimate(row):
            report.error(
                "failed_model_table_has_estimate",
                f"Row {idx} has status={status} but also contains numeric estimate columns.",
                "model_table.csv",
            )
        for field in source_columns:
            recorded = _resolve_recorded_path(run_path, row.get(field))
            if recorded is not None and not recorded.exists():
                report.error(
                    "model_table_source_missing",
                    f"Row {idx} records missing source path in {field}: {row.get(field)}",
                    "model_table.csv",
                )


def _step_failed_or_skipped(step: dict[str, Any], child_status: dict[str, Any]) -> bool:
    status = str(step.get("status") or child_status.get("legacy_status") or child_status.get("status") or "").lower()
    normalized = str(child_status.get("status") or "").lower()
    return status in {"failed", "fatal", "missing_dependency", "skipped", "interface_only"} or normalized in {"failed", "skipped"}


def _validate_child_runs(
    run_path: Path,
    status: dict[str, Any],
    report: ValidationReport,
    *,
    _seen: set[Path],
) -> None:
    step_results_path = run_path / "step_results.json"
    if not step_results_path.exists():
        return
    step_payload = _load_json(step_results_path, report)
    steps = step_payload.get("steps") if isinstance(step_payload, dict) else None
    if not isinstance(steps, list):
        report.error("step_results_invalid", "step_results.json must contain a list at `steps`.", "step_results.json")
        return
    parent_claims_main = status.get("main_claim_available") is True or status.get("paper_readiness") == "paper_ready"
    for idx, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            report.error("step_result_invalid", f"Step {idx} is not an object.", "step_results.json")
            continue
        run_dir_value = step.get("run_dir")
        if not run_dir_value:
            report.error("step_run_dir_missing", f"Step {idx} lacks run_dir.", "step_results.json")
            continue
        child_path = Path(str(run_dir_value))
        if not child_path.is_absolute():
            child_path = run_path / child_path
        if not child_path.exists():
            report.error("child_run_dir_missing", f"Child run directory does not exist: {child_path}", "step_results.json")
            continue
        child_report = validate_run_dir(child_path, strict=False, _seen=_seen)
        report.checked_files.append(f"{child_path.name}/contract")
        if child_report.errors:
            report.error(
                "child_run_contract_failed",
                f"Child run contract failed for step {idx}: {[item.code for item in child_report.errors]}",
                "step_results.json",
            )
        child_status_path = child_path / "status.json"
        try:
            child_status = json.loads(child_status_path.read_text(encoding="utf-8")) if child_status_path.exists() else {}
        except Exception:
            child_status = {}
        if bool(step.get("critical")) and parent_claims_main and _step_failed_or_skipped(step, child_status):
            report.error(
                "paper_ready_with_failed_critical_child",
                f"Parent claims paper-ready/main output while critical step {idx} is failed/skipped.",
                "step_results.json",
            )
        if _step_failed_or_skipped(step, child_status):
            child_table = child_path / "model_table.csv"
            if child_table.exists():
                child_rows, _ = _read_csv_rows(child_table, report)
                if any(_row_has_numeric_estimate(row) for row in child_rows):
                    report.error(
                        "failed_child_has_estimate_rows",
                        f"Failed/skipped child step {idx} has numeric estimate rows.",
                        str(child_table),
                    )


def validate_run_dir(run_dir: str | Path, *, strict: bool = False, _seen: set[Path] | None = None) -> ValidationReport:
    run_path = Path(run_dir)
    report = ValidationReport(run_dir=run_path, strict=strict)
    resolved = run_path.resolve()
    seen = _seen if _seen is not None else set()
    if resolved in seen:
        report.warn("recursive_run_skipped", f"Run directory already validated in this recursion: {run_path}", str(run_path))
        return report
    seen.add(resolved)
    if not run_path.exists():
        report.error("run_dir_missing", f"Run directory does not exist: {run_path}", str(run_path))
        return report
    _validate_required_files(run_path, report)
    manifest = _load_json(run_path / "manifest.json", report)
    status = _load_json(run_path / "status.json", report)
    reviewer_risk = _load_json(run_path / "reviewer_risk.json", report)
    artifact_manifest = _load_json(run_path / "artifact_manifest.json", report)
    audit = _load_json(run_path / "audit.json", report)
    run_config = _load_json(run_path / "run_config_resolved.json", report)
    for file_name, payload in {
        "manifest.json": manifest,
        "status.json": status,
        "reviewer_risk.json": reviewer_risk,
        "artifact_manifest.json": artifact_manifest,
        "audit.json": audit,
    }.items():
        if payload:
            _validate_json_schema(file_name, payload, report)
    if not audit:
        report.error("audit_empty", "audit.json is missing or empty.", "audit.json")
    if status:
        _validate_status(status, report)
    if reviewer_risk and status:
        _validate_reviewer_risk(reviewer_risk, status, report)
    if artifact_manifest:
        _validate_artifact_manifest(run_path, artifact_manifest, report)
    if manifest and status:
        _validate_manifest(manifest, status, report)
    if run_config:
        _validate_run_config(run_config, report)
    if audit:
        _validate_model_table(run_path, audit, report)
    if status:
        _validate_child_runs(run_path, status, report, _seen=seen)
    for log_name in ("run_log.md", "run_log.txt"):
        log_path = run_path / log_name
        if log_path.exists() and not log_path.read_text(encoding="utf-8", errors="replace").strip():
            report.error("run_log_empty", f"{log_name} is empty.", log_name)
    return report


def write_validation_report(run_dir: str | Path, *, strict: bool = False) -> ValidationReport:
    report = validate_run_dir(run_dir, strict=strict)
    path = Path(run_dir) / "validation_report.json"
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return report
