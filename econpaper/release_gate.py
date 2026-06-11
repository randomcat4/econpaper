from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Any


RELEASE_GATE_VERSION = "v3.0"
PLACEHOLDER_RE = re.compile(r"\{\{[^}]+\}\}")
MAGNITUDE_RE = re.compile(r"(standard deviations?|% of the mean|percentage points? of|AUTHOR_INPUT_NEEDED: magnitude)", re.IGNORECASE)


@dataclass
class ReleaseGateFinding:
    code: str
    tier: str
    message: str
    path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "tier": self.tier,
            "message": self.message,
            "path": self.path,
            "details": self.details,
        }


@dataclass
class ReleaseGateResult:
    status: str = "passed"
    findings: list[ReleaseGateFinding] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    @property
    def has_hard_blocks(self) -> bool:
        return any(finding.tier == "hard_block" for finding in self.findings)

    def add_finding(
        self,
        code: str,
        tier: str,
        message: str,
        *,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if tier == "hard_block":
            self.status = "failed"
        self.findings.append(ReleaseGateFinding(code=code, tier=tier, message=message, path=path, details=details or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": RELEASE_GATE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "metrics": self.metrics,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def run_release_gate(*, pack_dir: str | Path, human_eval_path: str | Path | None = None) -> ReleaseGateResult:
    pack = Path(pack_dir)
    result = ReleaseGateResult(metrics={"pack_dir": str(pack)})
    if not pack.exists():
        result.add_finding("pack_dir_missing", "hard_block", f"Pack directory does not exist: {pack}", path=str(pack))
        return result
    _check_author_report(pack, result)
    _check_claim_ledger(pack, result)
    _check_global_coherence(pack, result)
    _check_sections(pack, result)
    _check_run_validation(pack, result)
    _check_human_eval(Path(human_eval_path) if human_eval_path else None, result)
    result.status = "failed" if result.has_hard_blocks else "passed"
    return result


def write_release_gate(*, pack_dir: str | Path, out_dir: str | Path, human_eval_path: str | Path | None = None) -> ReleaseGateResult:
    result = run_release_gate(pack_dir=pack_dir, human_eval_path=human_eval_path)
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    (internal / "release_gate.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _check_author_report(pack: Path, result: ReleaseGateResult) -> None:
    report = pack / "AUTHOR_REPORT.md"
    if not report.exists():
        result.add_finding("author_report_missing", "hard_block", "Consolidated AUTHOR_REPORT.md is required.", path=str(report))


def _check_claim_ledger(pack: Path, result: ReleaseGateResult) -> None:
    ledger_path = pack / "claim_ledger.json"
    if not ledger_path.exists():
        result.add_finding("claim_ledger_missing", "hard_block", "claim_ledger.json is required for release.", path=str(ledger_path))
        return
    ledger = _load_json(ledger_path, result, "claim_ledger")
    hard_blocks = ledger.get("hard_blocks", []) if isinstance(ledger, dict) else []
    hard_claims = [claim for claim in ledger.get("claims", []) if isinstance(claim, dict) and claim.get("status") == "hard_block"]
    if hard_blocks or hard_claims or ledger.get("status") == "failed":
        result.add_finding(
            "claim_ledger_not_release_ready",
            "hard_block",
            "Claim ledger still contains hard blocks or failed status.",
            path=str(ledger_path),
            details={"hard_blocks": hard_blocks, "hard_claim_count": len(hard_claims)},
        )


def _check_global_coherence(pack: Path, result: ReleaseGateResult) -> None:
    path = pack / "reports" / "internal" / "global_coherence.json"
    if not path.exists():
        result.add_finding("global_coherence_missing", "hard_block", "global_coherence.json is required for release.", path=str(path))
        return
    payload = _load_json(path, result, "global_coherence")
    if payload.get("status") == "failed" or payload.get("has_hard_blocks"):
        result.add_finding("global_coherence_failed", "hard_block", "Global coherence report is failed.", path=str(path))


def _check_sections(pack: Path, result: ReleaseGateResult) -> None:
    sections = pack / "sections"
    if not sections.exists():
        result.add_finding("sections_missing", "hard_block", "Rendered sections directory is required.", path=str(sections))
        return
    for path in sections.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text):
            result.add_finding(
                "unrendered_numeric_placeholder",
                "hard_block",
                "Release sections must not contain unresolved numeric placeholders.",
                path=str(path),
            )
    results_path = sections / "04_results.md"
    if not results_path.exists():
        result.add_finding("results_section_missing", "hard_block", "Results section is required.", path=str(results_path))
        return
    results_text = results_path.read_text(encoding="utf-8")
    if not MAGNITUDE_RE.search(results_text):
        result.add_finding(
            "results_magnitude_missing",
            "hard_block",
            "Main Results must include economic magnitude interpretation or explicit author-input-needed magnitude gap.",
            path=str(results_path),
        )


def _check_run_validation(pack: Path, result: ReleaseGateResult) -> None:
    path = pack / "reports" / "internal" / "run_validation.json"
    if not path.exists():
        return
    payload = _load_json(path, result, "run_validation")
    if payload.get("mock_watermark_required") or payload.get("public_watermark"):
        result.add_finding("mock_output_not_release_ready", "hard_block", "Mock/smoke output cannot pass release gate.", path=str(path))


def _check_human_eval(path: Path | None, result: ReleaseGateResult) -> None:
    if path is None:
        result.add_finding("human_eval_missing", "hard_block", "Human release gate requires at least five scholar evaluations.")
        return
    if not path.exists():
        result.add_finding("human_eval_missing", "hard_block", f"Human evaluation file does not exist: {path}", path=str(path))
        return
    payload = _load_json(path, result, "human_eval")
    evaluations = payload.get("evaluations", []) if isinstance(payload, dict) else []
    if not isinstance(evaluations, list) or len(evaluations) < 5:
        result.add_finding("human_eval_too_few", "hard_block", "At least five scholar evaluations are required.", path=str(path))
        return
    retentions = [_as_float(item.get("generated_text_retention")) for item in evaluations if isinstance(item, dict)]
    retentions = [value for value in retentions if value is not None]
    time_saved = sum(1 for item in evaluations if isinstance(item, dict) and item.get("time_saved") is True)
    fabrications = sum(1 for item in evaluations if isinstance(item, dict) and item.get("silent_fabrication_reported") is True)
    clearer = sum(1 for item in evaluations if isinstance(item, dict) and item.get("author_report_clearer") is True)
    feedback = sum(1 for item in evaluations if isinstance(item, dict) and item.get("feedback_attached") is True)
    med = median(retentions) if retentions else 0.0
    result.metrics["human_eval"] = {
        "count": len(evaluations),
        "median_generated_text_retention": med,
        "time_saved_count": time_saved,
        "silent_fabrication_reports": fabrications,
        "author_report_clearer_count": clearer,
        "feedback_attached_count": feedback,
    }
    if med < 0.50:
        result.add_finding("human_eval_retention_low", "hard_block", "Median generated-text retention must be at least 50%.", path=str(path))
    if time_saved < 4:
        result.add_finding("human_eval_time_saved_low", "hard_block", "At least four of five users must report meaningful time saved.", path=str(path))
    if fabrications:
        result.add_finding("human_eval_fabrication_reported", "hard_block", "No user may report silent number or citation fabrication.", path=str(path))
    if clearer < 3:
        result.add_finding("human_eval_author_report_clarity_low", "hard_block", "At least three users must say AUTHOR_REPORT clarified next actions.", path=str(path))
    if feedback < len(evaluations):
        result.add_finding("human_eval_feedback_missing", "hard_block", "All human-evaluation feedback must be attached.", path=str(path))


def _load_json(path: Path, result: ReleaseGateResult, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.add_finding(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", path=str(path))
        return {}
    if not isinstance(payload, dict):
        result.add_finding(f"{label}_not_object", "hard_block", f"{label} must be a JSON object.", path=str(path))
        return {}
    return payload


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _author_report_text(result: ReleaseGateResult) -> str:
    hard_blocks = [finding for finding in result.findings if finding.tier == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Release Gate Status",
        "",
        f"- Status: `{result.status}`",
        f"- Hard blocks: `{len(hard_blocks)}`",
        "",
        "## Human Evaluation Metrics",
        "",
    ]
    human = result.metrics.get("human_eval")
    if human:
        for key, value in human.items():
            lines.append(f"- `{key}`: `{value}`")
    else:
        lines.append("- Not supplied.")
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{finding.code}`: {finding.message}" for finding in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve release blockers before declaring v3 complete.")
    else:
        lines.append("- Release gate passed.")
    return "\n".join(lines) + "\n"
