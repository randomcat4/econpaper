from __future__ import annotations

import csv
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


PACKAGE_ROOT = Path(__file__).resolve().parent
ROOT = PACKAGE_ROOT.parents[1]
REPO_ROOT = ROOT.parent
DEFAULT_RUNS = ROOT / "runs"


@dataclass
class RunContext:
    method: str
    engine: str
    state: str
    spec: dict[str, Any]
    run_dir: Path
    repo_root: Path = REPO_ROOT

    def artifact(self, name: str) -> Path:
        return self.run_dir / name


class Skill4EconError(RuntimeError):
    """Raised for actionable user-facing failures."""


def utc_stamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def read_spec(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover - depends on environment
            raise Skill4EconError(
                "YAML specs require PyYAML. Use JSON or run in the EvoScientist env."
            ) from exc
        data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise Skill4EconError("Spec must load to a mapping/object.")
    return data


def make_run_context(
    method: str,
    engine: str,
    spec: dict[str, Any],
    state: str,
    output_dir: str | None,
) -> RunContext:
    base = Path(output_dir or spec.get("output_dir") or DEFAULT_RUNS)
    if not base.is_absolute():
        base = ROOT / base
    run_dir = base / method / f"{utc_stamp()}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return RunContext(method=method, engine=engine, state=state, spec=spec, run_dir=run_dir)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_yaml_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import yaml

        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    except Exception:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")


def _load_dependency_payload(ctx: RunContext, extra: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("dependency_report", "dependencies"):
        value = extra.get(key)
        if isinstance(value, dict):
            return value
    path = ctx.artifact("dependency_report.json")
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _rerun_command(ctx: RunContext) -> str:
    output_arg = str(ctx.run_dir.parent)
    if ctx.engine == "workflow":
        spec_path = ctx.spec.get("_spec_path") or "SPEC"
        return (
            "conda run -n base python -m skill4econ.cli workflow "
            f"--name {ctx.method} --spec {spec_path} --output {output_arg} --run"
        )
    spec_path = ctx.spec.get("_spec_path") or "SPEC"
    return (
        "conda run -n base python -m skill4econ.cli run "
        f"--engine {ctx.engine} --method {ctx.method} --spec {spec_path} --output {output_arg} --run"
    )


def _ensure_minimal_model_table(ctx: RunContext) -> None:
    if ctx.artifact("model_table.csv").exists() or ctx.artifact("model_table.json").exists():
        return
    write_model_table(
        ctx,
        [
            {
                "note": "No coefficient table was produced by this diagnostic/adapter run.",
                "model": ctx.method,
                "engine": ctx.engine,
                "status": ctx.state,
            }
        ],
    )


def _status_payload(
    ctx: RunContext,
    *,
    legacy_status: str,
    reviewer_risk: dict[str, Any],
    extra: dict[str, Any],
    timestamp: str,
) -> dict[str, Any]:
    from .contracts.agent_status import infer_agent_status
    from .contracts.claim_levels import infer_claim_contract
    from .contracts.run_status import normalize_run_status

    risk_codes = [
        str(item.get("code"))
        for item in reviewer_risk.get("risks", [])
        if isinstance(item, dict) and item.get("code")
    ]
    missing_dependencies: list[str] = []
    if legacy_status == "missing_dependency":
        missing_dependencies.append(str(extra.get("package") or "unknown"))
    dependency_payload = extra.get("dependency_report") or extra.get("dependencies")
    if isinstance(dependency_payload, dict):
        for name, info in (dependency_payload.get("modules") or {}).items():
            if isinstance(info, dict) and not info.get("available"):
                missing_dependencies.append(str(name))
    method_or_workflow = str(extra.get("workflow") or ctx.method)
    claim = infer_claim_contract(
        method_or_workflow=method_or_workflow,
        status=legacy_status,
        extra=extra,
        reviewer_risk=reviewer_risk,
    )
    normalized_status = normalize_run_status(
        legacy_status,
        risk_level=str(reviewer_risk.get("risk_level") or ""),
    )
    agent_status = infer_agent_status(
        legacy_status=legacy_status,
        normalized_status=normalized_status,
        claim_level=str(claim.get("claim_level") or ""),
        paper_readiness=str(claim.get("paper_readiness") or ""),
        main_claim_available=bool(claim.get("main_claim_available")),
        risk_level=str(reviewer_risk.get("risk_level") or ""),
        risk_codes=sorted(set(risk_codes)),
        missing_dependencies=sorted(set(missing_dependencies)),
        extra=extra,
    )
    return {
        "status": normalized_status,
        "agent_status": agent_status,
        "legacy_status": legacy_status,
        "method_or_workflow": method_or_workflow,
        "method": ctx.method,
        "engine": ctx.engine,
        "state": ctx.state,
        "run_id": timestamp,
        "run_dir": str(ctx.run_dir),
        "primary_failure_reason": extra.get("error") if legacy_status in {"failed", "fatal"} else None,
        "skipped_reason": extra.get("purpose") if legacy_status in {"missing_dependency", "interface_only"} else None,
        "missing_dependencies": sorted(set(missing_dependencies)),
        "risk_codes": sorted(set(risk_codes)),
        "rerun_command": _rerun_command(ctx),
        **claim,
    }


def _build_reviewer_risk(ctx: RunContext, status: str, extra: dict[str, Any]):
    from .contracts.claim_levels import EXPLORATORY_METHOD_HINTS
    from .contracts.reviewer_risk import ReviewerRiskCollector

    warnings = list(extra.get("warnings") or [])
    method_or_workflow = str(extra.get("workflow") or ctx.method)
    if method_or_workflow in EXPLORATORY_METHOD_HINTS or extra.get("estimator_is_fallback"):
        existing_codes = {str(item.get("code")) for item in warnings if isinstance(item, dict)}
        if "FALLBACK_ESTIMATOR_NOT_PAPER_READY" not in existing_codes:
            warnings.append(
                {
                    "severity": "red",
                    "code": "FALLBACK_ESTIMATOR_NOT_PAPER_READY",
                    "message": (
                        f"{method_or_workflow} uses a local fallback or screening estimator. "
                        "The run may be useful for diagnostics, plots, or early exploration, "
                        "but it is not a publication-grade estimator."
                    ),
                    "action": (
                        "Route paper claims to a certified Stata/R/package backend or keep "
                        "this output explicitly exploratory/not-for-claim."
                    ),
                }
            )
    if status == "missing_dependency":
        warnings.append(
            {
                "severity": "yellow",
                "code": "backend_unavailable",
                "message": str(extra.get("package") or "A backend dependency is unavailable."),
                "action": str(extra.get("purpose") or "Install or configure the backend before claiming this estimator."),
            }
        )
    elif status == "failed" and not warnings:
        warnings.append(
            {
                "severity": "red",
                "code": "estimator_step_failed",
                "message": str(extra.get("error") or "The estimator/workflow failed."),
                "action": "Inspect audit.json, stdout/stderr, and model logs before using this output.",
            }
        )
    method_card = extra.get("method_card") if isinstance(extra.get("method_card"), dict) else {}
    return ReviewerRiskCollector.from_warnings(
        str(extra.get("workflow") or ctx.method),
        warnings,
        safe_claims=extra.get("safe_claims") if isinstance(extra.get("safe_claims"), list) else None,
        unsafe_claims=method_card.get("claim_limits") if isinstance(method_card.get("claim_limits"), list) else None,
    )


def _write_run_log(
    ctx: RunContext,
    *,
    status: str,
    timestamp: str,
    reviewer_risk: dict[str, Any],
    extra: dict[str, Any],
) -> None:
    lines = [
        f"# Run Log: {ctx.method}",
        "",
        f"- status: `{status}`",
        f"- engine: `{ctx.engine}`",
        f"- state: `{ctx.state}`",
        f"- timestamp_utc: `{timestamp}`",
        f"- run_dir: `{ctx.run_dir}`",
        f"- reviewer_risk_level: `{reviewer_risk.get('risk_level')}`",
    ]
    if reviewer_risk.get("risk_level") == "fatal":
        lines.insert(2, "**FATAL REVIEWER RISK: inspect reviewer_risk.json before using these artifacts.**")
        lines.insert(3, "")
    if extra.get("error"):
        lines.extend(["", "## Error", "", str(extra.get("error"))])
    if extra.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for item in extra.get("warnings") or []:
            lines.append(f"- `{item.get('severity')}` `{item.get('code')}`: {item.get('message')}")
    log_text = "\n".join(lines) + "\n"
    write_text(ctx.artifact("run_log.md"), log_text)
    write_text(ctx.artifact("run_log.txt"), log_text)


def write_manifest(ctx: RunContext, status: str, **extra: Any) -> dict[str, Any]:
    timestamp = utc_stamp()
    dependency_payload = _load_dependency_payload(ctx, extra)
    if dependency_payload:
        from .contracts.artifact_manifest import build_backend_status

        write_json(ctx.artifact("backend_status.json"), build_backend_status(dependency_payload))
    elif status == "missing_dependency":
        write_json(
            ctx.artifact("backend_status.json"),
            {
                "backend": str(extra.get("package") or "unknown"),
                "available": False,
                "status": "backend_unavailable",
                "message": str(extra.get("purpose") or extra.get("error") or "Backend dependency unavailable."),
            },
        )
    if status == "missing_dependency":
        write_text(
            ctx.artifact("backend_unavailable.md"),
            "\n".join(
                [
                    "# Backend Unavailable",
                    "",
                    f"- method: `{ctx.method}`",
                    f"- engine: `{ctx.engine}`",
                    f"- missing: `{extra.get('package') or 'unknown'}`",
                    f"- purpose: {extra.get('purpose') or extra.get('error') or 'Not provided.'}",
                    "",
                    "No estimator output was fabricated. Configure the backend and rerun this exact spec.",
                ]
            )
            + "\n",
        )
    run_config = {
        "method": ctx.method,
        "engine": ctx.engine,
        "state": ctx.state,
        "status": status,
        "run_dir": str(ctx.run_dir),
        "timestamp_utc": timestamp,
        "spec": ctx.spec,
        "rerun_command": _rerun_command(ctx),
    }
    _write_yaml_payload(ctx.artifact("run_config_resolved.yaml"), run_config)
    write_json(ctx.artifact("run_config_resolved.json"), run_config)
    risk_collector = _build_reviewer_risk(ctx, status, extra)
    risk_collector.to_json(ctx.artifact("reviewer_risk.json"))
    risk_collector.to_markdown(ctx.artifact("reviewer_risk.md"))
    reviewer_risk_payload = risk_collector.to_dict()
    _ensure_minimal_model_table(ctx)
    status_payload = _status_payload(
        ctx,
        legacy_status=status,
        reviewer_risk=reviewer_risk_payload,
        extra=extra,
        timestamp=timestamp,
    )
    write_json(ctx.artifact("status.json"), status_payload)
    _write_run_log(
        ctx,
        status=status,
        timestamp=timestamp,
        reviewer_risk=reviewer_risk_payload,
        extra=extra,
    )
    payload: dict[str, Any] = {
        "status": status,
        "method": ctx.method,
        "engine": ctx.engine,
        "state": ctx.state,
        "run_dir": str(ctx.run_dir),
        "timestamp_utc": timestamp,
        "spec": ctx.spec,
        "artifacts": sorted(p.name for p in ctx.run_dir.iterdir() if p.is_file()),
        "rerun_command": _rerun_command(ctx),
        "claim_level": status_payload["claim_level"],
        "paper_readiness": status_payload["paper_readiness"],
        "main_claim_available": status_payload["main_claim_available"],
        "agent_status": status_payload["agent_status"],
        "risk_codes": status_payload["risk_codes"],
    }
    payload.update(extra)
    write_json(ctx.artifact("manifest.json"), payload)
    from .contracts.artifact_manifest import write_artifact_manifest

    artifact_manifest = write_artifact_manifest(
        ctx.artifact("artifact_manifest.json"),
        workflow=str(extra.get("workflow") or ctx.method),
        run_id=timestamp,
        run_dir=ctx.run_dir,
        status=status,
        dependency_report=dependency_payload,
        input_contract=str(ctx.spec.get("data_contract")) if ctx.spec.get("data_contract") else None,
    )
    payload["artifact_manifest"] = str(ctx.artifact("artifact_manifest.json"))
    payload["missing_required_artifacts"] = artifact_manifest.get("missing_required_artifacts", [])
    write_json(ctx.artifact("manifest.json"), payload)
    return payload


def _failure_warning_from_error(message: str) -> dict[str, Any] | None:
    mappings = [
        (
            "SDM_IMPACTS_MISSING",
            {
                "code": "SDM_IMPACTS_MISSING",
                "message": "Spatial model output did not include a complete direct/indirect/total impact decomposition.",
                "action": "Rerun the backend with impact decomposition enabled before reporting SDM indirect effects.",
            },
        ),
        (
            "BACKEND_PARSE_FAILED",
            {
                "code": "BACKEND_PARSE_FAILED",
                "message": "Backend parser failed to read a valid machine-readable result.",
                "action": "Fix the backend output file or parser fixture; do not use partial parsed results.",
            },
        ),
        (
            "BACKEND_RESULT_MISSING",
            {
                "code": "BACKEND_RESULT_MISSING",
                "message": "Backend execution did not produce the required output artifact.",
                "action": "Inspect backend logs and rerun; do not treat stdout success as an estimate.",
            },
        ),
        (
            "BACKEND_TIMEOUT",
            {
                "code": "BACKEND_TIMEOUT",
                "message": "Backend execution exceeded the configured timeout.",
                "action": "Move this run to the slow/nightly matrix or increase the explicit timeout.",
            },
        ),
        (
            "BACKEND_INVALID_RESULT",
            {
                "code": "BACKEND_INVALID_RESULT",
                "message": "Backend result violated the expected adapter contract.",
                "action": "Fix the backend adapter or parser fixture before using this result.",
            },
        ),
    ]
    for marker, warning in mappings:
        if marker in message:
            return {"severity": "red", **warning}
    return None


def failure_manifest(ctx: RunContext, exc: Exception) -> dict[str, Any]:
    warning = _failure_warning_from_error(str(exc))
    warnings = [warning] if warning else []
    write_audit(ctx, "failed", [str(exc)], error_type=exc.__class__.__name__, warnings=warnings)
    return write_manifest(ctx, "failed", error=str(exc), error_type=exc.__class__.__name__, warnings=warnings)


def write_audit(ctx: RunContext, status: str, messages: list[str], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "method": ctx.method,
        "engine": ctx.engine,
        "state": ctx.state,
        "messages": messages,
    }
    payload.update(extra)
    write_json(ctx.artifact("audit.json"), payload)
    return payload


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def data_path_from_spec(spec: dict[str, Any]) -> Path | None:
    value = spec.get("data") or spec.get("input") or spec.get("input_path")
    if not value:
        return None
    path = Path(str(value))
    if not path.is_absolute():
        workspace_path = REPO_ROOT / path
        repo_path = ROOT / path
        path = workspace_path if workspace_path.exists() else repo_path
    return path


def read_table(spec: dict[str, Any]):
    import pandas as pd

    path = data_path_from_spec(spec)
    if path is None:
        raise Skill4EconError("Spec must provide data/input/input_path.")
    if not path.exists():
        raise Skill4EconError(f"Input data not found: {path}")
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return pd.read_excel(path), path
    if suffix == ".csv":
        return pd.read_csv(path), path
    raise Skill4EconError(f"Unsupported input format: {suffix}. Use CSV or XLSX.")


def require_columns(df: Any, columns: list[str], role: str) -> list[str]:
    missing = [c for c in columns if c and c not in df.columns]
    if missing:
        raise Skill4EconError(f"Missing {role} columns: {missing}")
    return missing


def listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in value]


def write_model_table(ctx: RunContext, rows: list[dict[str, Any]]) -> Path:
    path = ctx.artifact("model_table.csv")
    fieldnames = sorted({key for row in rows for key in row.keys()}) or ["note"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def dependency_report() -> dict[str, Any]:
    modules = {
        "pandas": "pandas",
        "numpy": "numpy",
        "scipy": "scipy",
        "statsmodels": "statsmodels.api",
        "sklearn": "sklearn",
        "linearmodels": "linearmodels",
        "xgboost": "xgboost",
        "matplotlib": "matplotlib",
        "seaborn": "seaborn",
        "econml": "econml",
        "dowhy": "dowhy",
        "doubleml": "doubleml",
        "causalml": "causalml",
        "lightgbm": "lightgbm",
        "pyreadstat": "pyreadstat",
    }
    report: dict[str, Any] = {"python": sys.executable, "modules": {}}
    for name, import_name in modules.items():
        try:
            module = importlib.import_module(import_name)
            report["modules"][name] = {
                "available": True,
                "version": getattr(module, "__version__", "unknown"),
                "import": import_name,
            }
        except Exception as exc:
            report["modules"][name] = {
                "available": False,
                "error": exc.__class__.__name__,
                "message": str(exc),
                "import": import_name,
            }
    report["vendor_sources"] = {
        path.name: str(path)
        for path in (ROOT / "vendor_sources").glob("*")
        if path.is_dir()
    }
    lock_path = ROOT / "vendor_sources.lock.json"
    if lock_path.exists():
        report["vendor_sources_lock"] = {
            "path": str(lock_path),
            "sha256": file_sha256(lock_path),
            "lock_status": "unlocked_source_reference_only",
        }

    from .config import (
        dea_discovery_chain,
        resolve_dea_backend,
        resolve_stata,
        stata_discovery_chain,
    )

    stata_path, stata_source = resolve_stata()
    report["stata"] = {
        "executable": str(stata_path) if stata_path else None,
        "available": stata_path is not None,
        "source": stata_source,
        "discovery_chain": stata_discovery_chain(),
    }
    rscript = shutil.which("Rscript")
    report["r"] = {
        "executable": rscript,
        "available": rscript is not None,
        "source": "PATH" if rscript else "missing",
    }

    dea_override, dea_source = resolve_dea_backend()
    report["dea_backend"] = {
        "vendored": True,
        "vendored_module": "skill4econ.backends.dea",
        "override_path": str(dea_override) if dea_override else None,
        "source": dea_source,
        "discovery_chain": dea_discovery_chain(),
    }
    return report


def run_subprocess(
    cmd: list[str],
    cwd: Path,
    timeout: int,
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    with stdout_path.open("w", encoding="utf-8", errors="replace") as out, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as err:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=out,
            stderr=err,
            timeout=timeout,
            check=False,
            text=True,
        )
    return int(proc.returncode)


def copy_if_needed(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)


def missing_dependency(ctx: RunContext, package: str, purpose: str) -> dict[str, Any]:
    msg = (
        f"{package} is not installed. Purpose: {purpose}. "
        "Per skill4econ policy, no package was installed automatically."
    )
    write_audit(ctx, "missing_dependency", [msg], package=package, purpose=purpose)
    return write_manifest(ctx, "missing_dependency", package=package, purpose=purpose)
