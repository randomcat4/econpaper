from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


KNOWN_NORMALIZED_STATUSES = {
    "success",
    "success_with_warnings",
    "partial_success",
    "skipped",
    "failed",
}

NON_CLAIMABLE_STATUSES = {"partial_success", "skipped", "failed"}
NON_CLAIMABLE_AGENT_STATUSES = {
    "success_diagnostic_only",
    "success_sensitivity_only",
    "success_adapter_only",
    "success_not_for_claim",
    "partial_backend_unavailable",
    "blocked_missing_dependency",
    "blocked_interface_only",
    "blocked_parser_only",
    "skipped",
    "failed",
}
NON_CLAIMABLE_CLAIM_LEVELS = {
    "diagnostic",
    "sensitivity_only",
    "adapter_only",
    "exploratory_only",
    "failed",
    "skipped",
}
NON_CLAIMABLE_READINESS = {
    "supplementary_only",
    "exploratory_only",
    "not_for_claim",
    "not_available",
}
MOCK_WATERMARK = "SMOKE TEST ONLY -- NOT A PAPER DRAFT"


@dataclass
class RunValidationIssue:
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
class RunValidationReport:
    run_dir: Path
    status: str = "passed"
    run_status: str | None = None
    method_or_workflow: str | None = None
    automatic_claims_allowed: bool = False
    automatic_results_allowed: bool = False
    mock_watermark_required: bool = False
    public_watermark: str | None = None
    issues: list[RunValidationIssue] = field(default_factory=list)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        self.status = "failed"
        self.issues.append(RunValidationIssue(code, severity, message, path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "v3.0",
            "status": self.status,
            "run_dir": str(self.run_dir),
            "run_status": self.run_status,
            "method_or_workflow": self.method_or_workflow,
            "automatic_claims_allowed": self.automatic_claims_allowed,
            "automatic_results_allowed": self.automatic_results_allowed,
            "mock_watermark_required": self.mock_watermark_required,
            "public_watermark": self.public_watermark,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _load_json(path: Path, report: RunValidationReport) -> dict[str, Any]:
    if not path.exists():
        report.add_issue("missing_json", "hard_block", f"Required JSON file is missing: {path.name}", path.name)
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.add_issue("invalid_json", "hard_block", f"Could not parse {path.name}: {exc}", path.name)
        return {}
    if not isinstance(payload, dict):
        report.add_issue("json_not_object", "hard_block", f"{path.name} must contain a JSON object.", path.name)
        return {}
    return payload


def _optional_json(path: Path, report: RunValidationReport) -> dict[str, Any]:
    if not path.exists():
        return {}
    return _load_json(path, report)


def _known_methods() -> set[str]:
    methods: set[str] = set()
    repo_skill_src = Path(__file__).resolve().parents[1] / "skill4econ" / "src"
    if repo_skill_src.exists() and str(repo_skill_src) not in sys.path:
        sys.path.insert(0, str(repo_skill_src))
    try:
        from skill4econ.python_wrappers import PYTHON_METHODS
        from skill4econ.stata_wrappers import STATA_METHODS
        from skill4econ.workflows import WORKFLOWS

        methods.update(PYTHON_METHODS)
        methods.update(STATA_METHODS)
        methods.update(WORKFLOWS)
    except Exception:
        pass
    return methods


def _validation_report_passed(payload: dict[str, Any]) -> bool:
    return str(payload.get("status") or "").strip().lower() in {"passed", "success", "ok"}


def _has_mock_signal(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {"mock", "mock_llm", "mock_runner", "is_mock", "smoke_test"} and bool(item):
                return True
            if lowered in {"mode", "run_mode", "status"} and str(item).lower() in {"mock", "smoke", "smoke_test"}:
                return True
            if _has_mock_signal(item):
                return True
    elif isinstance(value, list):
        return any(_has_mock_signal(item) for item in value)
    elif isinstance(value, str):
        return value.strip().lower() in {"mock", "smoke", "smoke_test", "mock_runner"}
    return False


def _artifact_manifest_usable(payload: dict[str, Any]) -> bool:
    missing = payload.get("missing_required_artifacts") or []
    return isinstance(payload.get("artifacts"), list) and not missing


def validate_run_dir(run_dir: str | Path, *, known_methods: set[str] | None = None) -> RunValidationReport:
    run_path = Path(run_dir)
    report = RunValidationReport(run_dir=run_path)
    if not run_path.exists():
        report.add_issue("run_dir_missing", "hard_block", f"Run directory does not exist: {run_path}", str(run_path))
        return report

    status = _load_json(run_path / "status.json", report)
    artifact_manifest = _load_json(run_path / "artifact_manifest.json", report)
    validation_report = _load_json(run_path / "validation_report.json", report)
    manifest = _optional_json(run_path / "manifest.json", report)
    run_config = _optional_json(run_path / "run_config_resolved.json", report)
    audit = _optional_json(run_path / "audit.json", report)

    run_status = str(status.get("status") or manifest.get("status") or "").strip().lower()
    method = str(
        status.get("method_or_workflow")
        or status.get("method")
        or manifest.get("workflow")
        or manifest.get("method")
        or audit.get("workflow")
        or audit.get("method")
        or ""
    ).strip()
    report.run_status = run_status or None
    report.method_or_workflow = method or None

    if run_status not in KNOWN_NORMALIZED_STATUSES:
        report.add_issue(
            "unknown_run_status",
            "hard_block",
            f"Unknown run status `{run_status or '<missing>'}` cannot produce automatic verified claims.",
            "status.json",
        )

    methods = known_methods if known_methods is not None else _known_methods()
    if not method:
        report.add_issue("missing_method", "hard_block", "Run status does not identify a method or workflow.", "status.json")
    elif method not in methods:
        reason = "Known method registry was unavailable." if not methods else "Method was absent from the known registry."
        report.add_issue(
            "unknown_method",
            "hard_block",
            f"Unknown method/workflow `{method}` cannot be treated as paper-ready automatically. {reason}",
            "status.json",
        )

    if not _validation_report_passed(validation_report):
        report.add_issue(
            "validation_report_not_passed",
            "hard_block",
            "Missing or non-passing validation_report.json prevents automatic Results writing.",
            "validation_report.json",
        )

    if not _artifact_manifest_usable(artifact_manifest):
        report.add_issue(
            "artifact_manifest_not_claimable",
            "hard_block",
            "Missing, empty, or incomplete artifact_manifest.json prevents claimable result writing.",
            "artifact_manifest.json",
        )

    if run_status in NON_CLAIMABLE_STATUSES:
        report.add_issue(
            "non_claimable_run_status",
            "hard_block",
            f"Run status `{run_status}` cannot produce verified empirical claims automatically.",
            "status.json",
        )

    agent_status = str(status.get("agent_status") or "").strip()
    if agent_status in NON_CLAIMABLE_AGENT_STATUSES:
        report.add_issue(
            "non_claimable_agent_status",
            "hard_block",
            f"Agent status `{agent_status}` is not claimable.",
            "status.json",
        )

    claim_level = str(status.get("claim_level") or manifest.get("claim_level") or "").strip()
    if claim_level in NON_CLAIMABLE_CLAIM_LEVELS:
        report.add_issue(
            "non_claimable_claim_level",
            "hard_block",
            f"Claim level `{claim_level}` cannot produce verified main result claims.",
            "status.json",
        )

    readiness = str(status.get("paper_readiness") or manifest.get("paper_readiness") or "").strip()
    if readiness in NON_CLAIMABLE_READINESS:
        report.add_issue(
            "non_claimable_paper_readiness",
            "hard_block",
            f"Paper readiness `{readiness}` is not paper-ready.",
            "status.json",
        )

    if status.get("main_claim_available") is not True:
        report.add_issue(
            "main_claim_unavailable",
            "hard_block",
            "main_claim_available is not true, so automatic verified result prose is disabled.",
            "status.json",
        )

    if _has_mock_signal({"status": status, "manifest": manifest, "run_config": run_config, "audit": audit}):
        report.mock_watermark_required = True
        report.public_watermark = MOCK_WATERMARK
        report.add_issue(
            "mock_output_not_paper_draft",
            "hard_block",
            "Mock/smoke output cannot masquerade as a real manuscript draft.",
            "run_config_resolved.json",
        )

    report.automatic_claims_allowed = report.status == "passed"
    report.automatic_results_allowed = report.automatic_claims_allowed
    return report


def _author_report_text(report: RunValidationReport) -> str:
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Run Validation",
        "",
        f"- Status: `{report.status}`",
        f"- Automatic verified claims allowed: `{str(report.automatic_claims_allowed).lower()}`",
        f"- Automatic Results writing allowed: `{str(report.automatic_results_allowed).lower()}`",
    ]
    if report.public_watermark:
        lines.extend(["", f"**{report.public_watermark}**"])
    lines.extend(["", "## Blocking Issues", ""])
    if report.issues:
        for issue in report.issues:
            lines.append(f"- `{issue.code}` ({issue.severity}): {issue.message}")
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Author-asserted Claims",
            "",
            "No author overrides were supplied in this validation step.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_run_validation(run_dir: str | Path, out_dir: str | Path) -> RunValidationReport:
    report = validate_run_dir(run_dir)
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "run_validation.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(report), encoding="utf-8")
    return report
