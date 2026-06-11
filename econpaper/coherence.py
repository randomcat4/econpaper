from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .section_writer import WRITING_ORDER


COHERENCE_VERSION = "v3.0"
PLACEHOLDER_RE = re.compile(r"\{\{\s*(?P<kind>[A-Za-z_]+)\s*:\s*(?P<claim_id>[^}]+?)\s*\}\}")
HEDGE_RE = re.compile(r"\b(may|might|could|suggestive|consistent with|appears to|possibly)\b", re.IGNORECASE)


@dataclass
class CoherenceFinding:
    code: str
    tier: str
    message: str
    section: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "tier": self.tier,
            "message": self.message,
            "section": self.section,
            "details": self.details,
        }


@dataclass
class CoherenceResult:
    report: dict[str, Any]
    status: str = "passed"
    findings: list[CoherenceFinding] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(finding.tier == "hard_block" for finding in self.findings)

    def add_finding(
        self,
        code: str,
        tier: str,
        message: str,
        *,
        section: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if tier == "hard_block":
            self.status = "failed"
        self.findings.append(CoherenceFinding(code=code, tier=tier, message=message, section=section, details=details or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": COHERENCE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "report": self.report,
            "findings": [finding.to_dict() for finding in self.findings],
        }


def run_global_coherence(
    *,
    sections_dir: str | Path,
    claim_ledger_path: str | Path,
    table_paths: list[str | Path] | None = None,
) -> CoherenceResult:
    sections_path = Path(sections_dir)
    result = CoherenceResult(report={})
    claim_ledger = _load_json(Path(claim_ledger_path), result, "claim_ledger")
    sections = _load_sections(sections_path, result)
    explicit_tables = [Path(path) for path in table_paths or []]

    _check_required_sections(sections, result)
    _check_claim_ledger_hard_blocks(claim_ledger, result)
    _check_placeholder_consistency(sections, result)
    _check_table_references(sections, sections_path, explicit_tables, result)
    _check_hedging_density(sections, result)

    claims = claim_ledger.get("claims", []) if isinstance(claim_ledger, dict) else []
    result.report = {
        "version": COHERENCE_VERSION,
        "status": "failed" if result.has_hard_blocks else "passed",
        "section_count": len(sections),
        "safe_claims": [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "safe"],
        "flagged_claims": [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "flag_and_confirm"],
        "author_asserted_claims": [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "author_asserted"],
        "hard_blocks": [finding.to_dict() for finding in result.findings if finding.tier == "hard_block"],
        "style_advice": [finding.to_dict() for finding in result.findings if finding.tier == "style_advice"],
        "coherence_findings": [finding.to_dict() for finding in result.findings],
    }
    result.status = result.report["status"]
    return result


def write_global_coherence(
    *,
    sections_dir: str | Path,
    claim_ledger_path: str | Path,
    out_dir: str | Path,
    table_paths: list[str | Path] | None = None,
) -> CoherenceResult:
    result = run_global_coherence(sections_dir=sections_dir, claim_ledger_path=claim_ledger_path, table_paths=table_paths)
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    (internal / "global_coherence.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: CoherenceResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_finding(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.add_finding(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}")
        return {}
    if not isinstance(payload, dict):
        result.add_finding(f"{label}_not_object", "hard_block", f"{label} must be a JSON object.")
        return {}
    return payload


def _load_sections(sections_dir: Path, result: CoherenceResult) -> dict[str, str]:
    if not sections_dir.exists():
        result.add_finding("sections_dir_missing", "hard_block", f"Sections directory does not exist: {sections_dir}")
        return {}
    sections: dict[str, str] = {}
    for path in sections_dir.glob("*.md"):
        try:
            sections[path.name] = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            result.add_finding("section_not_utf8", "hard_block", f"Section is not UTF-8 readable: {exc}", section=path.name)
    return sections


def _check_required_sections(sections: dict[str, str], result: CoherenceResult) -> None:
    missing = [filename for filename in WRITING_ORDER if filename not in sections]
    for filename in missing:
        result.add_finding("required_section_missing", "hard_block", f"Required section `{filename}` is missing.", section=filename)


def _check_claim_ledger_hard_blocks(claim_ledger: dict[str, Any], result: CoherenceResult) -> None:
    for item in claim_ledger.get("hard_blocks", []) if isinstance(claim_ledger, dict) else []:
        code = item.get("code") if isinstance(item, dict) else "claim_ledger_hard_block"
        result.add_finding("claim_ledger_hard_block", "hard_block", f"Claim ledger hard block remains unresolved: {code}.")


def _check_placeholder_consistency(sections: dict[str, str], result: CoherenceResult) -> None:
    placeholders = {name: _claim_placeholders(text) for name, text in sections.items()}
    abstract_claims = placeholders.get("00_abstract.md", set())
    result_claims = placeholders.get("04_results.md", set())
    conclusion_claims = placeholders.get("09_conclusion.md", set())
    missing_from_results = abstract_claims - result_claims
    if missing_from_results:
        result.add_finding(
            "abstract_result_not_in_results",
            "hard_block",
            "Abstract uses result placeholders that are absent from the Results section.",
            section="00_abstract.md",
            details={"claim_ids": sorted(missing_from_results)},
        )
    missing_from_conclusion = (abstract_claims & result_claims) - conclusion_claims
    if missing_from_conclusion:
        result.add_finding(
            "conclusion_missing_main_result",
            "flag_and_confirm",
            "Conclusion does not repeat all abstract/results main-result placeholders.",
            section="09_conclusion.md",
            details={"claim_ids": sorted(missing_from_conclusion)},
        )


def _claim_placeholders(text: str) -> set[str]:
    return {match.group("claim_id").strip() for match in PLACEHOLDER_RE.finditer(text)}


def _check_table_references(
    sections: dict[str, str],
    sections_dir: Path,
    explicit_tables: list[Path],
    result: CoherenceResult,
) -> None:
    known_tables = {path.resolve() for path in explicit_tables if path.exists()}
    root = sections_dir.parent
    for section, text in sections.items():
        for match in re.finditer(r"Table reference:\s*`([^`]+)`", text):
            raw = match.group(1)
            path = Path(raw)
            candidates = [path]
            if not path.is_absolute():
                candidates.extend([root / path, sections_dir / path])
            if not any(candidate.exists() or candidate.resolve() in known_tables for candidate in candidates):
                result.add_finding(
                    "dangling_table_reference",
                    "hard_block",
                    f"Table reference does not resolve to an existing file: {raw}",
                    section=section,
                )


def _check_hedging_density(sections: dict[str, str], result: CoherenceResult) -> None:
    for section, text in sections.items():
        if section in {"08_limitations.md", "06_mechanisms.md"}:
            continue
        paragraphs = [item.strip() for item in re.split(r"\n\s*\n", text) if item.strip()]
        for idx, paragraph in enumerate(paragraphs, start=1):
            matches = HEDGE_RE.findall(paragraph)
            if len(matches) > 2:
                result.add_finding(
                    "hedging_density_high",
                    "style_advice",
                    "Paragraph uses more than two hedge phrases outside limitations/mechanisms.",
                    section=section,
                    details={"paragraph": idx, "hedge_count": len(matches)},
                )


def _author_report_text(result: CoherenceResult) -> str:
    report = result.report
    hard_blocks = [finding for finding in result.findings if finding.tier == "hard_block"]
    flagged = [finding for finding in result.findings if finding.tier == "flag_and_confirm"]
    style = [finding for finding in result.findings if finding.tier == "style_advice"]
    safe_claims = report.get("safe_claims", [])
    flagged_claims = report.get("flagged_claims", [])
    author_asserted = report.get("author_asserted_claims", [])
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Status Overview",
        "",
        f"- Status: `{result.status}`",
        f"- Sections checked: `{report.get('section_count', 0)}`",
        f"- Safe claims: `{len(safe_claims)}`",
        f"- Flagged claims: `{len(flagged_claims)}`",
        f"- Author-asserted claims: `{len(author_asserted)}`",
        f"- Hard blocks: `{len(hard_blocks)}`",
        "",
        "## Safe Claims",
        "",
    ]
    lines.extend([f"- `{claim.get('claim_id')}` {claim.get('prose_template')}" for claim in safe_claims] if safe_claims else ["- None."])
    lines.extend(["", "## Flagged And Downgraded Claims", ""])
    lines.extend([f"- `{claim.get('claim_id')}`: {', '.join(claim.get('gate_reasons', []))}" for claim in flagged_claims] if flagged_claims else ["- None."])
    lines.extend(["", "## Author-Asserted Claims", ""])
    lines.extend([f"- `{claim.get('claim_id')}` original status preserved." for claim in author_asserted] if author_asserted else ["- None."])
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{finding.code}`: {finding.message}" for finding in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Missing Diagnostics And Citations", ""])
    missing = [finding for finding in flagged if "missing" in finding.code or "citation" in finding.code]
    lines.extend([f"- `{finding.code}`: {finding.message}" for finding in missing] if missing else ["- None detected in global coherence."])
    lines.extend(["", "## Economic Magnitude Gaps", ""])
    magnitude_claims = [
        claim for claim in flagged_claims if "magnitude_context_missing" in claim.get("gate_reasons", [])
    ]
    lines.extend([f"- `{claim.get('claim_id')}` needs magnitude context." for claim in magnitude_claims] if magnitude_claims else ["- None detected in claim ledger."])
    lines.extend(["", "## Global Coherence Findings", ""])
    non_style = [finding for finding in result.findings if finding.tier != "style_advice"]
    lines.extend([f"- `{finding.code}` ({finding.tier}): {finding.message}" for finding in non_style] if non_style else ["- None."])
    if style:
        lines.extend(["", "## Style Advice", ""])
        lines.extend([f"- `{finding.code}` in `{finding.section}`: {finding.message}" for finding in style])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve hard blocks before marking the manuscript pack complete.")
    elif flagged_claims or flagged:
        lines.append("- Address flagged design/magnitude/coherence items or record author assertions.")
    else:
        lines.append("- Continue to incremental rerun packaging and release-gate checks.")
    lines.extend(["", "## Expected Referee Questions", ""])
    questions: list[str] = []
    for claim in flagged_claims:
        questions.extend(claim.get("reviewer_questions", []))
    lines.extend([f"- {question}" for question in questions] if questions else ["- None generated from current claim ledger."])
    return "\n".join(lines) + "\n"
