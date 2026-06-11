from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


RERUN_VERSION = "v3.0"
PROTECTED_RE = re.compile(
    r"<!--\s*ECONPAPER:PROTECTED START(?P<meta>.*?)-->(?P<body>.*?)<!--\s*ECONPAPER:PROTECTED END\s*-->",
    re.DOTALL,
)


@dataclass
class RerunIssue:
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
class IncrementalRerunResult:
    diff: dict[str, Any]
    status: str = "passed"
    issues: list[RerunIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(RerunIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": RERUN_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "diff": self.diff,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def run_incremental_rerun(
    *,
    previous_pack_dir: str | Path,
    updated_pack_dir: str | Path,
    allow_regenerate_protected: bool = False,
) -> IncrementalRerunResult:
    previous = Path(previous_pack_dir)
    updated = Path(updated_pack_dir)
    result = IncrementalRerunResult(
        diff={
            "version": RERUN_VERSION,
            "previous_pack_dir": str(previous),
            "updated_pack_dir": str(updated),
            "allow_regenerate_protected": allow_regenerate_protected,
            "claim_status_changes": [],
            "new_claims": [],
            "removed_claims": [],
            "protected_sections": [],
            "copied_ledgers": [],
        }
    )
    if not previous.exists():
        result.add_issue("previous_pack_missing", "hard_block", f"Previous pack does not exist: {previous}", str(previous))
    if not updated.exists():
        result.add_issue("updated_pack_missing", "hard_block", f"Updated pack does not exist: {updated}", str(updated))
    if result.has_hard_blocks:
        return result

    previous_claims = _claims_by_id(_load_json(previous / "claim_ledger.json", result, "previous_claim_ledger"))
    updated_claims = _claims_by_id(_load_json(updated / "claim_ledger.json", result, "updated_claim_ledger"))
    _diff_claim_statuses(previous_claims, updated_claims, result)
    _plan_section_updates(previous, updated, allow_regenerate_protected, result)
    return result


def write_incremental_rerun(
    *,
    previous_pack_dir: str | Path,
    updated_pack_dir: str | Path,
    out_dir: str | Path,
    allow_regenerate_protected: bool = False,
) -> IncrementalRerunResult:
    result = run_incremental_rerun(
        previous_pack_dir=previous_pack_dir,
        updated_pack_dir=updated_pack_dir,
        allow_regenerate_protected=allow_regenerate_protected,
    )
    previous = Path(previous_pack_dir)
    updated = Path(updated_pack_dir)
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    if not result.has_hard_blocks:
        _write_section_outputs(previous, updated, out_path, result)
        _copy_ledgers(updated, out_path, result)
    (internal / "rerun_diff.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: IncrementalRerunResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", str(path))
        return {}
    return payload if isinstance(payload, dict) else {}


def _claims_by_id(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    claims = ledger.get("claims", []) if isinstance(ledger, dict) else []
    return {str(claim.get("claim_id")): claim for claim in claims if isinstance(claim, dict) and claim.get("claim_id")}


def _diff_claim_statuses(
    previous_claims: dict[str, dict[str, Any]],
    updated_claims: dict[str, dict[str, Any]],
    result: IncrementalRerunResult,
) -> None:
    for claim_id, previous in previous_claims.items():
        updated = updated_claims.get(claim_id)
        if not updated:
            result.diff["removed_claims"].append({"claim_id": claim_id, "previous_status": previous.get("status")})
            continue
        if previous.get("status") != updated.get("status"):
            result.diff["claim_status_changes"].append(
                {
                    "claim_id": claim_id,
                    "before": previous.get("status"),
                    "after": updated.get("status"),
                    "before_reasons": previous.get("gate_reasons", []),
                    "after_reasons": updated.get("gate_reasons", []),
                }
            )
    for claim_id, updated in updated_claims.items():
        if claim_id not in previous_claims:
            result.diff["new_claims"].append({"claim_id": claim_id, "status": updated.get("status")})


def _plan_section_updates(
    previous: Path,
    updated: Path,
    allow_regenerate_protected: bool,
    result: IncrementalRerunResult,
) -> None:
    previous_sections = previous / "sections"
    updated_sections = updated / "sections"
    if not updated_sections.exists():
        result.add_issue("updated_sections_missing", "hard_block", f"Updated sections directory missing: {updated_sections}", str(updated_sections))
        return
    for updated_file in updated_sections.glob("*.md"):
        previous_file = previous_sections / updated_file.name
        protected = previous_file.exists() and _protected_blocks(previous_file.read_text(encoding="utf-8"))
        if protected and not allow_regenerate_protected:
            result.diff["protected_sections"].append(
                {
                    "section": updated_file.name,
                    "action": "preserve_previous_write_suggestion",
                    "protected_blocks": protected,
                }
            )
        elif protected and allow_regenerate_protected:
            result.diff["protected_sections"].append(
                {
                    "section": updated_file.name,
                    "action": "regenerated_with_explicit_permission",
                    "protected_blocks": protected,
                }
            )


def _protected_blocks(text: str) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for idx, match in enumerate(PROTECTED_RE.finditer(text), start=1):
        meta = match.group("meta").strip()
        block_id_match = re.search(r"id=['\"]?([A-Za-z0-9_.:-]+)", meta)
        blocks.append(
            {
                "block_id": block_id_match.group(1) if block_id_match else f"protected_{idx:03d}",
                "start": match.start(),
                "end": match.end(),
            }
        )
    return blocks


def _write_section_outputs(previous: Path, updated: Path, out_path: Path, result: IncrementalRerunResult) -> None:
    out_sections = out_path / "sections"
    suggestions = out_path / "suggestions"
    out_sections.mkdir(parents=True, exist_ok=True)
    suggestions.mkdir(parents=True, exist_ok=True)
    protected_actions = {item["section"]: item["action"] for item in result.diff["protected_sections"]}
    for updated_file in (updated / "sections").glob("*.md"):
        previous_file = previous / "sections" / updated_file.name
        action = protected_actions.get(updated_file.name)
        if action == "preserve_previous_write_suggestion" and previous_file.exists():
            (out_sections / updated_file.name).write_text(previous_file.read_text(encoding="utf-8"), encoding="utf-8")
            (suggestions / updated_file.name).write_text(updated_file.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            (out_sections / updated_file.name).write_text(updated_file.read_text(encoding="utf-8"), encoding="utf-8")


def _copy_ledgers(updated: Path, out_path: Path, result: IncrementalRerunResult) -> None:
    for name in ["claim_ledger.json", "evidence_ledger.json", "slots.json"]:
        source = updated / name
        if source.exists():
            shutil.copy2(source, out_path / name)
            result.diff["copied_ledgers"].append(name)


def _author_report_text(result: IncrementalRerunResult) -> str:
    changes = result.diff.get("claim_status_changes", [])
    protected = result.diff.get("protected_sections", [])
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Incremental Rerun Status",
        "",
        f"- Status: `{result.status}`",
        f"- Claim status changes: `{len(changes)}`",
        f"- New claims: `{len(result.diff.get('new_claims', []))}`",
        f"- Removed claims: `{len(result.diff.get('removed_claims', []))}`",
        f"- Protected sections: `{len(protected)}`",
        "",
        "## Claim Status Diff",
        "",
    ]
    if changes:
        for item in changes:
            lines.append(f"- `{item['claim_id']}`: `{item['before']}` -> `{item['after']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Protected Human Edits", ""])
    if protected:
        for item in protected:
            lines.append(f"- `{item['section']}`: {item['action']}")
    else:
        lines.append("- None.")
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Repair missing previous/updated pack inputs before rerun.")
    elif protected:
        lines.append("- Review suggestions for protected sections before accepting regenerated text.")
    else:
        lines.append("- Continue to release-gate checks.")
    return "\n".join(lines) + "\n"
