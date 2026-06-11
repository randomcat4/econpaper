from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SECTION_WRITER_VERSION = "v3.0"
AUTHOR_INPUT_NEEDED = "[AUTHOR_INPUT_NEEDED]"
CITE_NEEDED = "[CITE_NEEDED: preferred related-literature references]"
WRITING_ORDER = [
    "02_data.md",
    "03_empirical_strategy.md",
    "04_results.md",
    "05_robustness.md",
    "06_mechanisms.md",
    "07_heterogeneity.md",
    "08_limitations.md",
    "09_conclusion.md",
    "00_abstract.md",
    "01_introduction.md",
    "10_related_literature_skeleton.md",
]


@dataclass
class SectionWriterIssue:
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
class SectionWriterResult:
    sections: dict[str, str]
    audit: dict[str, Any]
    status: str = "passed"
    issues: list[SectionWriterIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(SectionWriterIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SECTION_WRITER_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "audit": self.audit,
            "sections": sorted(self.sections),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def generate_sections(
    *,
    claim_ledger_path: str | Path,
    intake_profile_path: str | Path,
    citation_index_path: str | Path | None = None,
    table_path: str | Path | None = None,
) -> SectionWriterResult:
    result = SectionWriterResult(
        sections={},
        audit={
            "version": SECTION_WRITER_VERSION,
            "writing_order": WRITING_ORDER,
            "safe_claim_ids_used": [],
            "author_asserted_claim_ids_used": [],
            "flagged_claim_ids_not_written_as_verified": [],
            "table_path": str(table_path) if table_path else None,
        },
    )
    claim_ledger = _load_json(Path(claim_ledger_path), result, "claim_ledger")
    intake = _load_json(Path(intake_profile_path), result, "intake_profile")
    citation_index = _load_json(Path(citation_index_path), result, "citation_index") if citation_index_path else {}

    if claim_ledger.get("status") == "failed" or claim_ledger.get("hard_blocks"):
        result.add_issue("claim_ledger_has_hard_blocks", "hard_block", "Section writer will not write verified result claims from a failed claim ledger.", str(claim_ledger_path))

    claims = claim_ledger.get("claims", []) if isinstance(claim_ledger, dict) else []
    safe_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "safe"]
    author_asserted_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "author_asserted"]
    flagged_claims = [claim for claim in claims if isinstance(claim, dict) and claim.get("status") == "flag_and_confirm"]
    if result.has_hard_blocks:
        safe_claims = []
    result.audit["safe_claim_ids_used"] = [claim["claim_id"] for claim in safe_claims]
    result.audit["author_asserted_claim_ids_used"] = [claim["claim_id"] for claim in author_asserted_claims]
    result.audit["flagged_claim_ids_not_written_as_verified"] = [claim["claim_id"] for claim in flagged_claims]

    result.sections = {
        "02_data.md": _data_section(intake),
        "03_empirical_strategy.md": _strategy_section(intake),
        "04_results.md": _results_section(safe_claims, author_asserted_claims, flagged_claims, table_path, blocked=result.has_hard_blocks),
        "05_robustness.md": _placeholder_section("Robustness", "robustness checks, sensitivity analyses, and alternative specifications"),
        "06_mechanisms.md": _placeholder_section("Mechanisms", "mechanism diagnostics or author-confirmed mechanism claims"),
        "07_heterogeneity.md": _placeholder_section("Heterogeneity", "heterogeneity groups, subgroup definitions, and multiple-testing policy"),
        "08_limitations.md": _limitations_section(flagged_claims, intake),
        "09_conclusion.md": _conclusion_section(safe_claims, author_asserted_claims, intake, blocked=result.has_hard_blocks),
        "00_abstract.md": _abstract_section(safe_claims, author_asserted_claims, intake, blocked=result.has_hard_blocks),
        "01_introduction.md": _introduction_skeleton(intake),
        "10_related_literature_skeleton.md": _related_literature_skeleton(citation_index),
    }
    return result


def write_sections(
    *,
    claim_ledger_path: str | Path,
    intake_profile_path: str | Path,
    out_dir: str | Path,
    citation_index_path: str | Path | None = None,
    table_path: str | Path | None = None,
) -> SectionWriterResult:
    result = generate_sections(
        claim_ledger_path=claim_ledger_path,
        intake_profile_path=intake_profile_path,
        citation_index_path=citation_index_path,
        table_path=table_path,
    )
    out_path = Path(out_dir)
    sections_dir = out_path / "sections"
    internal = out_path / "reports" / "internal"
    sections_dir.mkdir(parents=True, exist_ok=True)
    internal.mkdir(parents=True, exist_ok=True)
    for filename, text in result.sections.items():
        (sections_dir / filename).write_text(text, encoding="utf-8")
    (internal / "section_generation.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: SectionWriterResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", str(path))
        return {}
    if not isinstance(payload, dict):
        result.add_issue(f"{label}_not_object", "hard_block", f"{label} must be a JSON object.", str(path))
        return {}
    return payload


def _data_section(intake: dict[str, Any]) -> str:
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    timing = intake.get("treatment_timing", {}) if isinstance(intake, dict) else {}
    outcomes = intake.get("outcome_magnitude_context", []) if isinstance(intake, dict) else []
    lines = [
        "# Data",
        "",
        f"The unit of observation is {_value(design.get('unit_of_observation'), 'unit of observation')}.",
        f"The sample scope is {_value(design.get('sample_scope'), 'sample scope')}.",
        f"The treatment, exposure, or shock is {_value(timing.get('treatment_name'), 'treatment/exposure/shock definition')}.",
        f"Treatment timing is {_value(timing.get('timing_type'), 'treatment timing type')}.",
        "",
        "## Outcome Magnitude Context",
        "",
    ]
    if outcomes:
        for item in outcomes:
            if not isinstance(item, dict):
                continue
            variable = _value(item.get("variable"), "outcome variable")
            unit = _value(item.get("unit"), f"unit for {variable}")
            mean = _value(item.get("mean"), f"mean for {variable}")
            sd = _value(item.get("sd"), f"standard deviation for {variable}")
            lines.append(f"- `{variable}` is measured in {unit}; mean: {mean}; standard deviation: {sd}.")
    else:
        lines.append(f"- {AUTHOR_INPUT_NEEDED}: outcome magnitude context.")
    return "\n".join(lines) + "\n"


def _strategy_section(intake: dict[str, Any]) -> str:
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    timing = intake.get("treatment_timing", {}) if isinstance(intake, dict) else {}
    lines = [
        "# Empirical Strategy",
        "",
        f"The author-declared design is {_value(design.get('design_type'), 'declared design type')}.",
        f"The estimand is {_value(design.get('estimand'), 'estimand in author language')}.",
        f"The event-time unit is {_value(timing.get('event_time_unit'), 'event-time unit')}.",
        f"The anticipation window is {_value(timing.get('anticipation_window'), 'anticipation window')}.",
        "",
        "Identification and causal language remain subject to design gates and author confirmation.",
    ]
    return "\n".join(lines) + "\n"


def _results_section(
    safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    flagged_claims: list[dict[str, Any]],
    table_path: str | Path | None,
    *,
    blocked: bool,
) -> str:
    lines = ["# Results", ""]
    if table_path:
        lines.append(f"Table reference: `{Path(table_path).as_posix()}`.")
        lines.append("")
    if blocked:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: resolve claim-ledger hard blocks before writing verified result claims.")
    elif safe_claims:
        for claim in safe_claims:
            lines.append(claim["prose_template"])
    else:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: no safe main-result claims are available yet.")
    if author_asserted_claims:
        lines.extend(["", "## Author-Asserted Statements", ""])
        for claim in author_asserted_claims:
            lines.append(f"- Author asserted: {claim['prose_template']}")
    if flagged_claims:
        lines.extend(["", "## Not Written As Verified Claims", ""])
        for claim in flagged_claims:
            reasons = ", ".join(claim.get("gate_reasons", [])) or "flag_and_confirm"
            lines.append(f"- `{claim['claim_id']}` requires confirmation before verified prose: {reasons}.")
    return "\n".join(lines) + "\n"


def _placeholder_section(title: str, needed: str) -> str:
    return f"# {title}\n\n{AUTHOR_INPUT_NEEDED}: {needed}.\n"


def _limitations_section(flagged_claims: list[dict[str, Any]], intake: dict[str, Any]) -> str:
    sample_scope = _value((intake.get("author_declared_design") or {}).get("sample_scope"), "sample scope") if isinstance(intake, dict) else _value(None, "sample scope")
    lines = ["# Limitations", "", f"The current sample scope is {sample_scope}."]
    if flagged_claims:
        lines.extend(["", "The following claims require author or design confirmation before stronger language is used:"])
        for claim in flagged_claims:
            lines.append(f"- `{claim['claim_id']}`: {', '.join(claim.get('gate_reasons', []))}.")
    else:
        lines.append("")
        lines.append(f"{AUTHOR_INPUT_NEEDED}: limitations and external-validity scope.")
    return "\n".join(lines) + "\n"


def _conclusion_section(
    safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    intake: dict[str, Any],
    *,
    blocked: bool,
) -> str:
    contribution = _value(intake.get("contribution_statement") if isinstance(intake, dict) else None, "contribution statement")
    lines = ["# Conclusion", "", f"Contribution to carry forward: {contribution}"]
    if blocked:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: resolve hard blocks before summarizing verified results.")
    elif safe_claims:
        lines.append("The conclusion should summarize the same ledger-backed main result used in Results:")
        lines.append(safe_claims[0]["prose_template"])
    elif author_asserted_claims:
        lines.append("Only author-asserted claims are currently available; keep them labeled until evidence gates pass.")
    else:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: verified main result claim.")
    return "\n".join(lines) + "\n"


def _abstract_section(
    safe_claims: list[dict[str, Any]],
    author_asserted_claims: list[dict[str, Any]],
    intake: dict[str, Any],
    *,
    blocked: bool,
) -> str:
    project = intake.get("project", {}) if isinstance(intake, dict) else {}
    design = intake.get("author_declared_design", {}) if isinstance(intake, dict) else {}
    contribution = _value(intake.get("contribution_statement") if isinstance(intake, dict) else None, "contribution statement")
    lines = [
        "# Abstract",
        "",
        f"Working title: {_value(project.get('title_working'), 'working title')}.",
        f"Design: {_value(design.get('design_type'), 'declared design type')}.",
        contribution,
    ]
    if blocked:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: verified abstract result after hard blocks are resolved.")
    elif safe_claims:
        lines.append(safe_claims[0]["prose_template"])
    elif author_asserted_claims:
        lines.append("Author-asserted result language is available but should remain labeled outside the final abstract.")
    else:
        lines.append(f"{AUTHOR_INPUT_NEEDED}: ledger-backed result sentence.")
    return "\n".join(lines) + "\n"


def _introduction_skeleton(intake: dict[str, Any]) -> str:
    project = intake.get("project", {}) if isinstance(intake, dict) else {}
    motivation = _value(intake.get("research_motivation") if isinstance(intake, dict) else None, "research motivation")
    contribution = _value(intake.get("contribution_statement") if isinstance(intake, dict) else None, "contribution statement")
    context = intake.get("institutional_context", []) if isinstance(intake, dict) else []
    lines = [
        "# Introduction Skeleton",
        "",
        f"- Working title: {_value(project.get('title_working'), 'working title')}.",
        f"- Motivation: {motivation}",
        f"- Contribution: {contribution}",
        "- Institutional context:",
    ]
    if context:
        for item in context:
            if isinstance(item, dict):
                lines.append(f"  - {item.get('fact', AUTHOR_INPUT_NEEDED)}")
    else:
        lines.append(f"  - {AUTHOR_INPUT_NEEDED}: institutional, historical, or regulatory context.")
    return "\n".join(lines) + "\n"


def _related_literature_skeleton(citation_index: dict[str, Any]) -> str:
    citekeys = citation_index.get("citekeys", []) if isinstance(citation_index, dict) else []
    lines = ["# Related Literature Skeleton", ""]
    lines.append("This section intentionally avoids literature-search prose in P0.")
    if citekeys:
        keys = ", ".join(f"`{key}`" for key in citekeys[:10])
        lines.append(f"Supplied bibliography keys available for author positioning: {keys}.")
        lines.append("Use author-provided notes before turning these keys into literature claims.")
    else:
        lines.append(CITE_NEEDED)
    return "\n".join(lines) + "\n"


def _value(value: Any, label: str) -> str:
    if value is None or value == "":
        return f"{AUTHOR_INPUT_NEEDED}: {label}"
    return str(value)


def _author_report_text(result: SectionWriterResult) -> str:
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Section Generation Status",
        "",
        f"- Status: `{result.status}`",
        f"- Sections written: `{len(result.sections)}`",
        f"- Safe claims used: `{len(result.audit.get('safe_claim_ids_used', []))}`",
        f"- Author-asserted claims used: `{len(result.audit.get('author_asserted_claim_ids_used', []))}`",
        f"- Flagged claims held back: `{len(result.audit.get('flagged_claim_ids_not_written_as_verified', []))}`",
        "",
        "## Writing Order",
        "",
    ]
    lines.extend([f"- `{item}`" for item in result.audit["writing_order"]])
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve claim-ledger hard blocks and rerun section generation.")
    else:
        lines.append("- Render numeric placeholders, then run global coherence checks.")
    return "\n".join(lines) + "\n"
