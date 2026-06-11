from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_CORE_ARTIFACTS = [
    "manifest.json",
    "artifact_manifest.json",
    "reviewer_risk.json",
    "run_config_resolved.yaml",
    "run_config_resolved.json",
    "run_log.md",
    "run_log.txt",
    "status.json",
    "model_table.csv",
]

TABLE_SUFFIXES = {".csv", ".xlsx", ".xls"}
FIGURE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
SCRIPT_SUFFIXES = {".do", ".py", ".r", ".sh", ".bat"}
LOG_SUFFIXES = {".log", ".txt", ".md"}


def _as_posix(path: Path) -> str:
    return path.as_posix()


def infer_artifact_type(path: Path) -> str:
    suffix = path.suffix.lower()
    name = path.name.lower()
    if suffix in TABLE_SUFFIXES:
        return "table"
    if suffix in FIGURE_SUFFIXES:
        return "figure"
    if suffix in SCRIPT_SUFFIXES:
        return "script"
    if suffix == ".json":
        return "metadata" if "manifest" in name or "risk" in name else "model_result"
    if suffix in {".yaml", ".yml"}:
        return "config"
    if suffix in LOG_SUFFIXES:
        return "log"
    return "artifact"


def infer_artifact_role(path: Path) -> str:
    name = path.name.lower()
    if name == "model_table.csv":
        return "main_result"
    if "event_study" in name and path.suffix.lower() in FIGURE_SUFFIXES:
        return "dynamic_effect"
    if "diagnostic" in name or "audit" in name:
        return "diagnostic"
    if "manifest" in name:
        return "manifest"
    if "risk" in name:
        return "reviewer_risk"
    if "rerun" in name:
        return "rerun_script"
    if name in {"run_log.md", "stata.log", "run.log", "stdout.txt", "stderr.txt"}:
        return "execution_log"
    if name.endswith("_spec.yml") or name.endswith("_spec.yaml") or name == "run_config_resolved.yaml":
        return "resolved_config"
    if "data_summary" in name or "sample_construction" in name:
        return "sample_diagnostic"
    return "supporting"


def _artifact_record(path: Path, run_dir: Path, required_names: set[str], producer: str) -> dict[str, Any]:
    relative = path.relative_to(run_dir)
    rel_text = _as_posix(relative)
    required = rel_text in required_names or path.name in required_names
    return {
        "path": rel_text,
        "type": infer_artifact_type(path),
        "role": infer_artifact_role(path),
        "required": required,
        "required_for_paper": required,
        "producer": producer,
        "exists": path.exists(),
        "bytes": int(path.stat().st_size) if path.exists() else None,
    }


def build_backend_status(dependency_report: dict[str, Any] | None) -> dict[str, Any]:
    report = dependency_report or {}
    modules = report.get("modules") if isinstance(report.get("modules"), dict) else {}
    return {
        "stata": "available" if report.get("stata", {}).get("available") else "missing",
        "r": "available" if report.get("r", {}).get("available") else "missing",
        "python": "available",
        "python_packages": {
            name: "available" if info.get("available") else "missing"
            for name, info in modules.items()
            if isinstance(info, dict)
        },
        "dea_backend": "available" if report.get("dea_backend", {}).get("vendored") else "missing",
    }


def build_artifact_manifest(
    *,
    workflow: str,
    run_id: str,
    run_dir: Path,
    status: str,
    dependency_report: dict[str, Any] | None = None,
    required_artifacts: list[str] | None = None,
    input_contract: str | None = None,
) -> dict[str, Any]:
    required_names = set(required_artifacts or REQUIRED_CORE_ARTIFACTS)
    artifacts = [
        _artifact_record(path, run_dir, required_names, workflow)
        for path in sorted(run_dir.rglob("*"))
        if path.is_file()
    ]
    listed = {item["path"] for item in artifacts} | {Path(item["path"]).name for item in artifacts}
    missing = sorted(name for name in required_names if name not in listed)
    return {
        "workflow": workflow,
        "run_id": run_id,
        "status": status,
        "input_contract": input_contract,
        "artifacts": artifacts,
        "backend_status": build_backend_status(dependency_report),
        "missing_required_artifacts": missing,
    }


def write_artifact_manifest(
    path: Path,
    *,
    workflow: str,
    run_id: str,
    run_dir: Path,
    status: str,
    dependency_report: dict[str, Any] | None = None,
    required_artifacts: list[str] | None = None,
    input_contract: str | None = None,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    payload = build_artifact_manifest(
        workflow=workflow,
        run_id=run_id,
        run_dir=run_dir,
        status=status,
        dependency_report=dependency_report,
        required_artifacts=required_artifacts,
        input_contract=input_contract,
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
