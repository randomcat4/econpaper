from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth import subscription_status
from .evidence import write_evidence_ledger
from .intake import write_intake_profile
from .quality_suite import write_quality_suite_manifest
from .release_gate import write_release_gate
from .run_validation import write_run_validation
from .write_pack import write_manuscript_pack


@dataclass
class OneClickResult:
    status_path: Path
    payload: dict[str, Any]

    @property
    def has_hard_blocks(self) -> bool:
        return bool(self.payload.get("status") == "failed")

    def to_dict(self) -> dict[str, Any]:
        return self.payload


def run_oneclick(
    *,
    case_id: str | None = None,
    out_root: str | Path,
    run_dir: str | Path | None = None,
    raw_data_dir: str | Path | None = None,
    intake_profile_path: str | Path | None = None,
    answers_path: str | Path | None = None,
    spec_path: str | Path | None = None,
    refs_path: str | Path | None = None,
    venue: str = "generic-field-journal",
    latex_command: str = "auto",
    model_table_paths: list[str | Path] | None = None,
    summary_stats_path: str | Path | None = None,
    human_eval_path: str | Path | None = None,
    target_venue: str | None = None,
    preferred_contribution: str | None = None,
    project_title: str | None = None,
    field: str | None = None,
    skip_codex_review: bool = False,
    codex_timeout: int = 180,
    require_auth: bool = True,
) -> OneClickResult:
    root = Path(out_root) / datetime.now().strftime("%Y%m%d_%H%M%S")
    root.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "version": "v3.0",
        "case_id": case_id,
        "out_dir": str(root),
        "stages": [],
        "status": "running",
    }

    auth = subscription_status(timeout=20).to_dict()
    status["auth"] = auth
    status["stages"].append(
        {
            "name": "auth",
            "status": "passed" if not auth.get("has_hard_blocks") else "failed",
            "hard_blocks": [issue.get("code") for issue in auth.get("issues", []) if isinstance(issue, dict)],
        }
    )
    if require_auth and auth.get("has_hard_blocks"):
        status["status"] = "failed"
        status["reason"] = "subscription_auth_missing"
        return _write_status(root, status)

    if _has_custom_inputs(
        run_dir=run_dir,
        raw_data_dir=raw_data_dir,
        intake_profile_path=intake_profile_path,
        answers_path=answers_path,
        spec_path=spec_path,
        refs_path=refs_path,
        model_table_paths=model_table_paths,
    ):
        return _run_custom_oneclick(
            root=root,
            status=status,
            case_id=case_id,
            run_dir=run_dir,
            raw_data_dir=raw_data_dir,
            intake_profile_path=intake_profile_path,
            answers_path=answers_path,
            spec_path=spec_path,
            refs_path=refs_path,
            venue=venue,
            latex_command=latex_command,
            model_table_paths=model_table_paths,
            summary_stats_path=summary_stats_path,
            human_eval_path=human_eval_path,
            target_venue=target_venue,
            preferred_contribution=preferred_contribution,
            project_title=project_title,
            field=field,
        )

    smoke = _load_smoke_module()
    if not case_id:
        status["status"] = "failed"
        status["reason"] = "input_missing"
        status["required"] = {
            "registered_case": "--case",
            "custom_project": ["--run-dir or --raw-data-dir", "--intake or --answers/--spec", "--refs"],
        }
        return _write_status(root, status)

    case = next((item for item in smoke.CASES if item.case_id == case_id), None)
    if case is None:
        status["status"] = "failed"
        status["reason"] = "unknown_case"
        status["available_cases"] = [item.case_id for item in smoke.CASES]
        return _write_status(root, status)

    backend_certification = smoke._run_backend_certification(root)
    status["backend_certification"] = backend_certification
    status["stages"].append(
        {
            "name": "backend_certification",
            "status": backend_certification.get("status") or "unknown",
            "artifact": backend_certification.get("artifact"),
        }
    )

    codex_path = None if skip_codex_review else smoke._codex_subscription_path()
    case_result = smoke._run_case(
        case=case,
        root=root,
        codex_path=codex_path,
        codex_timeout=codex_timeout,
        backend_certification=backend_certification,
    )
    status["case"] = case_result
    pack_dir = Path(case_result["paths"]["pack_dir"])
    skill_payload = case_result.get("skill4econ") or {}
    validation_payload = skill_payload.get("validation") if isinstance(skill_payload.get("validation"), dict) else {}
    skill_passed = (
        skill_payload.get("returncode") in {0, None}
        and validation_payload.get("status", "passed") == "passed"
    )
    status["stages"].extend(
        [
            {
                "name": "skill4econ",
                "status": "passed" if skill_passed else "failed",
                "mode": skill_payload.get("mode"),
                "run_dir": case_result["paths"].get("skill4econ_run_dir"),
                "validation_status": validation_payload.get("status"),
            },
            {
                "name": "write",
                "status": "passed" if (case_result.get("write") or {}).get("returncode") == 0 else "failed",
            },
            {
                "name": "compile",
                "status": "passed" if (case_result.get("static_checks") or {}).get("pdf_exists") else "failed",
            },
            {
                "name": "release_gate",
                "status": (case_result.get("release_gate") or {}).get("status"),
                "finding_codes": (case_result.get("release_gate") or {}).get("finding_codes") or [],
            },
        ]
    )

    quality = write_quality_suite_manifest(out_dir=pack_dir / "quality_suite")
    status["quality_suite"] = quality.to_dict()
    status["stages"].append({"name": "quality_suite", "status": quality.status})
    request_path = _write_human_eval_request(pack_dir, case_result)
    status["human_eval_request"] = str(request_path)

    release_codes = set((case_result.get("release_gate") or {}).get("finding_codes") or [])
    pdf_ok = bool((case_result.get("static_checks") or {}).get("pdf_exists"))
    write_ok = (case_result.get("write") or {}).get("returncode") == 0
    backend_ok = (case_result.get("backends") or {}).get("status") in {"live", "partially-live"}
    if write_ok and pdf_ok and backend_ok and release_codes == {"human_eval_missing"} and not quality.has_hard_blocks:
        status["status"] = "passed_pending_human_eval"
    else:
        status["status"] = "failed"
    return _write_status(pack_dir, status)


def _has_custom_inputs(
    *,
    run_dir: str | Path | None,
    raw_data_dir: str | Path | None,
    intake_profile_path: str | Path | None,
    answers_path: str | Path | None,
    spec_path: str | Path | None,
    refs_path: str | Path | None,
    model_table_paths: list[str | Path] | None,
) -> bool:
    return any(
        value is not None
        for value in [
            run_dir,
            raw_data_dir,
            intake_profile_path,
            answers_path,
            spec_path,
            refs_path,
        ]
    ) or bool(model_table_paths)


def _run_custom_oneclick(
    *,
    root: Path,
    status: dict[str, Any],
    case_id: str | None,
    run_dir: str | Path | None,
    raw_data_dir: str | Path | None,
    intake_profile_path: str | Path | None,
    answers_path: str | Path | None,
    spec_path: str | Path | None,
    refs_path: str | Path | None,
    venue: str,
    latex_command: str,
    model_table_paths: list[str | Path] | None,
    summary_stats_path: str | Path | None,
    human_eval_path: str | Path | None,
    target_venue: str | None,
    preferred_contribution: str | None,
    project_title: str | None,
    field: str | None,
) -> OneClickResult:
    status["mode"] = "custom_project"
    custom_run_dir = Path(run_dir) if run_dir else Path(raw_data_dir) if raw_data_dir else None
    pack_dir = root / "manuscript_pack"
    status["paths"] = {
        "root": str(root),
        "run_dir": str(custom_run_dir) if custom_run_dir else None,
        "raw_data_dir": str(raw_data_dir) if raw_data_dir else None,
        "pack_dir": str(pack_dir),
    }
    input_manifest = _write_input_manifest(
        root,
        run_dir=custom_run_dir,
        raw_data_dir=Path(raw_data_dir) if raw_data_dir else None,
        model_table_paths=[Path(path) for path in model_table_paths or []],
        refs_path=Path(refs_path) if refs_path else None,
        intake_profile_path=Path(intake_profile_path) if intake_profile_path else None,
        answers_path=Path(answers_path) if answers_path else None,
        spec_path=Path(spec_path) if spec_path else None,
    )
    status["input_manifest"] = str(input_manifest)
    status["stages"].append({"name": "input_manifest", "status": "passed", "artifact": str(input_manifest)})

    missing = _custom_required_missing(
        run_dir=custom_run_dir,
        intake_profile_path=intake_profile_path,
        answers_path=answers_path,
        spec_path=spec_path,
        refs_path=refs_path,
    )
    if missing:
        status["status"] = "failed"
        status["reason"] = "custom_inputs_missing"
        status["missing_inputs"] = missing
        status["stages"].append({"name": "prepare_inputs", "status": "failed", "missing": missing})
        return _write_status(root, status)
    status["stages"].append({"name": "prepare_inputs", "status": "passed"})

    intake_path = Path(intake_profile_path) if intake_profile_path else _build_custom_intake(
        root,
        answers_path=answers_path,
        spec_path=spec_path,
        target_venue=target_venue or venue,
        preferred_contribution=preferred_contribution,
        project_title=project_title,
        field=field,
        status=status,
    )
    if intake_path is None:
        status["status"] = "failed"
        status["reason"] = "intake_failed"
        return _write_status(root, status)

    run_validation = write_run_validation(custom_run_dir, root / "run_validation")
    status["stages"].append(
        {
            "name": "validate_run",
            "status": run_validation.status,
            "artifact": str(root / "run_validation" / "reports" / "internal" / "run_validation.json"),
            "issue_codes": [issue.code for issue in run_validation.issues],
        }
    )

    evidence = write_evidence_ledger(
        run_dir=custom_run_dir,
        out_dir=root / "evidence_probe",
        intake_profile_path=intake_path,
        model_table_paths=model_table_paths,
        summary_stats_path=summary_stats_path,
    )
    status["stages"].append(
        {
            "name": "evidence",
            "status": evidence.status,
            "artifact": str(root / "evidence_probe" / "evidence_ledger.json"),
            "issue_codes": [issue.code for issue in evidence.issues],
        }
    )

    write_result = write_manuscript_pack(
        run_dir=custom_run_dir,
        intake_profile_path=intake_path,
        refs_path=refs_path,
        venue=venue,
        out_dir=pack_dir,
        latex_command=latex_command,
        model_table_paths=model_table_paths,
    )
    status["write"] = write_result.to_dict()
    status["stages"].append(
        {
            "name": "write",
            "status": write_result.status,
            "artifact": str(pack_dir / "reports" / "internal" / "write_pack_manifest.json"),
            "issue_codes": [issue.code for issue in write_result.issues],
        }
    )

    release = write_release_gate(
        pack_dir=pack_dir,
        human_eval_path=human_eval_path,
        out_dir=root / "release_gate",
    )
    release_codes = [finding.code for finding in release.findings]
    status["release_gate"] = release.to_dict()
    status["stages"].append(
        {
            "name": "release_gate",
            "status": release.status,
            "artifact": str(root / "release_gate" / "reports" / "internal" / "release_gate.json"),
            "finding_codes": release_codes,
        }
    )

    quality = write_quality_suite_manifest(out_dir=pack_dir / "quality_suite")
    status["quality_suite"] = quality.to_dict()
    status["stages"].append({"name": "quality_suite", "status": quality.status})
    request_path = _write_human_eval_request(pack_dir, {"case_id": case_id or "custom_project", "release_gate": {"finding_codes": release_codes}})
    status["human_eval_request"] = str(request_path)

    if write_result.status == "passed" and set(release_codes) == {"human_eval_missing"} and not quality.has_hard_blocks:
        status["status"] = "passed_pending_human_eval"
    else:
        status["status"] = "failed"
    return _write_status(pack_dir if pack_dir.exists() else root, status)


def _custom_required_missing(
    *,
    run_dir: Path | None,
    intake_profile_path: str | Path | None,
    answers_path: str | Path | None,
    spec_path: str | Path | None,
    refs_path: str | Path | None,
) -> list[str]:
    missing: list[str] = []
    if run_dir is None:
        missing.append("--run-dir or --raw-data-dir")
    elif not run_dir.exists():
        missing.append(f"run directory does not exist: {run_dir}")
    if not intake_profile_path and not answers_path and not spec_path:
        missing.append("--intake or --answers/--spec")
    if not refs_path:
        missing.append("--refs")
    elif not Path(refs_path).exists():
        missing.append(f"refs file does not exist: {refs_path}")
    return missing


def _build_custom_intake(
    root: Path,
    *,
    answers_path: str | Path | None,
    spec_path: str | Path | None,
    target_venue: str | None,
    preferred_contribution: str | None,
    project_title: str | None,
    field: str | None,
    status: dict[str, Any],
) -> Path | None:
    intake_dir = root / "intake"
    result = write_intake_profile(
        out_dir=intake_dir,
        answers_path=answers_path,
        spec_path=spec_path,
        target_venue=target_venue,
        preferred_contribution=preferred_contribution,
        project_title=project_title,
        field=field,
    )
    status["intake"] = result.to_dict()
    status["stages"].append(
        {
            "name": "intake",
            "status": result.status,
            "artifact": str(intake_dir / "intake_profile.json"),
            "issue_codes": [issue.code for issue in result.issues],
        }
    )
    return None if result.has_hard_blocks else intake_dir / "intake_profile.json"


def _write_input_manifest(
    root: Path,
    *,
    run_dir: Path | None,
    raw_data_dir: Path | None,
    model_table_paths: list[Path],
    refs_path: Path | None,
    intake_profile_path: Path | None,
    answers_path: Path | None,
    spec_path: Path | None,
) -> Path:
    manifest = {
        "version": "v3.0",
        "mode": "custom_project_inputs",
        "run_dir": _path_entry(run_dir),
        "raw_data_dir": _path_entry(raw_data_dir),
        "model_tables": [_path_entry(path) for path in model_table_paths],
        "refs": _path_entry(refs_path),
        "intake": _path_entry(intake_profile_path),
        "answers": _path_entry(answers_path),
        "spec": _path_entry(spec_path),
        "raw_data_files": _file_inventory(raw_data_dir) if raw_data_dir else [],
        "run_dir_files": _file_inventory(run_dir) if run_dir and run_dir != raw_data_dir else [],
        "note": "Custom oneclick records input files but does not infer empirical results from raw data.",
    }
    path = root / "input_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _path_entry(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir() if path.exists() else False,
        "size": path.stat().st_size if path.exists() and path.is_file() else None,
    }


def _file_inventory(root: Path | None, *, max_files: int = 500) -> list[dict[str, Any]]:
    if root is None or not root.exists() or not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if len(rows) >= max_files:
            rows.append({"truncated": True, "max_files": max_files})
            break
        rel = path.relative_to(root).as_posix()
        rows.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
        )
    return rows


def _file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_smoke_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_multi_paper_smoke.py"
    spec = importlib.util.spec_from_file_location("econpaper_oneclick_smoke", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load smoke script: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_human_eval_request(pack_dir: Path, case_result: dict[str, Any]) -> Path:
    target = pack_dir / "human_eval" / "REQUEST.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    codes = ", ".join((case_result.get("release_gate") or {}).get("finding_codes") or [])
    text = f"""# Human Evaluation Request

Case: `{case_result.get("case_id")}`

Please attach at least five scholar evaluations in `human_eval.json`.

Required fields per evaluation:

- `reviewer_role`
- `generated_text_retention`
- `time_saved`
- `silent_fabrication_reported`
- `author_report_clearer`
- `feedback_attached`

Current release-gate findings: `{codes or "none"}`.
"""
    target.write_text(text, encoding="utf-8")
    return target


def _write_status(base: Path, payload: dict[str, Any]) -> OneClickResult:
    path = base / "oneclick_status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return OneClickResult(status_path=path, payload=payload)
