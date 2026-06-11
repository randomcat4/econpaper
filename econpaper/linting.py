from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .run_validation import MOCK_WATERMARK, RunValidationReport, validate_run_dir


SUPPORTED_DRAFT_SUFFIXES = {".tex", ".md", ".markdown"}
LINT_VERSION = "v3.0"


@dataclass(frozen=True)
class CitationUse:
    command: str
    key: str
    span_start: int
    span_end: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "key": self.key,
            "span_start": self.span_start,
            "span_end": self.span_end,
        }


@dataclass(frozen=True)
class NumericUse:
    raw: str
    value: float
    span_start: int
    span_end: int
    context: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "value": self.value,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "context": self.context,
        }


@dataclass
class LintFinding:
    finding_id: str
    code: str
    tier: str
    overridable: bool
    message: str
    path: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    author_override: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "code": self.code,
            "tier": self.tier,
            "overridable": self.overridable,
            "message": self.message,
            "path": self.path,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "details": self.details,
            "author_override": self.author_override,
        }


@dataclass
class LintReport:
    draft_path: Path
    run_dir: Path
    refs_path: Path | None
    status: str = "passed"
    findings: list[LintFinding] = field(default_factory=list)
    citation_uses: list[CitationUse] = field(default_factory=list)
    cite_needed: list[dict[str, str]] = field(default_factory=list)
    numeric_uses: list[NumericUse] = field(default_factory=list)
    table_refs: list[str] = field(default_factory=list)
    figure_refs: list[str] = field(default_factory=list)
    evidence_values: list[dict[str, Any]] = field(default_factory=list)
    run_validation: RunValidationReport | None = None
    author_overrides: dict[str, Any] = field(default_factory=dict)

    @property
    def has_hard_blocks(self) -> bool:
        return any(finding.tier == "hard_block" for finding in self.findings)

    def add_finding(
        self,
        code: str,
        tier: str,
        message: str,
        *,
        overridable: bool,
        path: str | None = None,
        span_start: int | None = None,
        span_end: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> LintFinding:
        finding = LintFinding(
            finding_id=f"lint_{len(self.findings) + 1:04d}",
            code=code,
            tier=tier,
            overridable=overridable,
            message=message,
            path=path,
            span_start=span_start,
            span_end=span_end,
            details=details or {},
        )
        self.findings.append(finding)
        if tier == "hard_block":
            self.status = "failed"
        return finding

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": LINT_VERSION,
            "status": self.status,
            "draft_path": str(self.draft_path),
            "run_dir": str(self.run_dir),
            "refs_path": str(self.refs_path) if self.refs_path else None,
            "has_hard_blocks": self.has_hard_blocks,
            "findings": [finding.to_dict() for finding in self.findings],
            "citation_uses": [use.to_dict() for use in self.citation_uses],
            "cite_needed": self.cite_needed,
            "numeric_uses": [use.to_dict() for use in self.numeric_uses],
            "table_refs": self.table_refs,
            "figure_refs": self.figure_refs,
            "evidence_values": self.evidence_values,
            "run_validation": self.run_validation.to_dict() if self.run_validation else None,
            "author_overrides": self.author_overrides,
        }


def parse_bibtex_keys(text: str) -> set[str]:
    return {match.group(1).strip() for match in re.finditer(r"@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", text)}


def extract_citation_uses(text: str) -> list[CitationUse]:
    uses: list[CitationUse] = []
    pattern = re.compile(r"\\(?P<command>cite[a-zA-Z*]*)(?:\s*\[[^\]]*\]){0,2}\s*\{(?P<keys>[^}]+)\}")
    for match in pattern.finditer(text):
        for key in match.group("keys").split(","):
            normalized = key.strip()
            if normalized:
                uses.append(CitationUse(match.group("command"), normalized, match.start(), match.end()))
    return uses


def extract_cite_needed(text: str) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []
    for idx, match in enumerate(re.finditer(r"\[CITE_NEEDED:\s*([^\]]+)\]", text), start=1):
        markers.append({"claim_id": f"cite_needed_{idx:03d}", "reason": match.group(1).strip()})
    return markers


def extract_table_refs(text: str) -> list[str]:
    refs = re.findall(r"\\(?:autoref|ref|Cref|cref)\s*\{\s*(tab:[^}]+)\}", text)
    refs.extend(re.findall(r"\bTable\s+([A-Za-z0-9_.:-]+)", text, flags=re.IGNORECASE))
    return sorted(set(refs))


def extract_figure_refs(text: str) -> list[str]:
    refs = re.findall(r"\\(?:autoref|ref|Cref|cref)\s*\{\s*(fig:[^}]+)\}", text)
    refs.extend(re.findall(r"\bFigure\s+([A-Za-z0-9_.:-]+)", text, flags=re.IGNORECASE))
    return sorted(set(refs))


def extract_numeric_uses(text: str) -> list[NumericUse]:
    uses: list[NumericUse] = []
    pattern = re.compile(r"(?<![A-Za-z0-9_])[-+]?(?:\d+\.\d+|\d+)(?:\s*%)?")
    for match in pattern.finditer(text):
        raw = match.group(0).strip()
        if _is_obvious_non_claim_number(text, match.start(), match.end(), raw):
            continue
        numeric_part = raw.replace("%", "").strip()
        try:
            value = float(numeric_part)
        except ValueError:
            continue
        context = text[max(0, match.start() - 80) : min(len(text), match.end() + 80)].replace("\n", " ")
        uses.append(NumericUse(raw=raw, value=value, span_start=match.start(), span_end=match.end(), context=context))
    return uses


def _is_obvious_non_claim_number(text: str, start: int, end: int, raw: str) -> bool:
    before = text[max(0, start - 32) : start].lower()
    after = text[end : min(len(text), end + 16)].lower()
    digits = raw.replace("%", "").strip().lstrip("+-")
    if re.fullmatch(r"\d{4}", digits) and 1800 <= int(digits) <= 2100:
        return True
    if re.search(r"\b(?:table|figure|fig\.|section|sec\.|appendix|equation|eq\.)\s*$", before):
        return True
    if before.endswith(("tab:", "fig:", "eq:", "sec:")):
        return True
    if re.search(r"\\(?:ref|autoref|cref|Cref)\s*\{\s*$", before):
        return True
    if re.match(r"\s*[,;]?\s*pp?\.", after):
        return True
    return False


def run_lint(
    draft_path: str | Path,
    *,
    run_dir: str | Path,
    refs_path: str | Path | None,
    out_dir: str | Path,
    author_overrides_path: str | Path | None = None,
) -> LintReport:
    draft = Path(draft_path)
    run_path = Path(run_dir)
    refs = Path(refs_path) if refs_path else None
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)

    report = LintReport(draft_path=draft, run_dir=run_path, refs_path=refs)

    if draft.suffix.lower() not in SUPPORTED_DRAFT_SUFFIXES:
        report.add_finding(
            "unsupported_draft_type",
            "hard_block",
            f"Unsupported draft type `{draft.suffix}`. Use .tex or .md.",
            overridable=False,
            path=str(draft),
        )
        text = ""
    else:
        text = _read_text_file(draft, report, required=True)

    author_overrides = _load_author_overrides(author_overrides_path, report)
    report.author_overrides = author_overrides

    run_validation = validate_run_dir(run_path)
    report.run_validation = run_validation
    for issue in run_validation.issues:
        report.add_finding(
            f"run_validation_{issue.code}",
            issue.severity,
            issue.message,
            overridable=False if issue.severity == "hard_block" else True,
            path=issue.path,
        )

    refs_text = _read_text_file(refs, report, required=True) if refs else ""
    citekeys = parse_bibtex_keys(refs_text)
    if refs and not citekeys:
        report.add_finding(
            "refs_bib_empty",
            "hard_block",
            "refs.bib was provided but no BibTeX keys were parsed.",
            overridable=False,
            path=str(refs),
        )

    report.citation_uses = extract_citation_uses(text)
    report.cite_needed = extract_cite_needed(text)
    _check_citations(report, citekeys)

    report.numeric_uses = extract_numeric_uses(text)
    ledger = _load_evidence_ledger(run_path, report)
    report.evidence_values = _evidence_values(ledger)
    _check_numeric_claims(report)

    report.table_refs = extract_table_refs(text)
    report.figure_refs = extract_figure_refs(text)
    _check_language_risks(text, report)
    _check_basic_style(text, report)
    _apply_author_overrides(report)

    _write_outputs(report, out_path, citekeys, text)
    return report


def _read_text_file(path: Path | None, report: LintReport, *, required: bool) -> str:
    if path is None:
        return ""
    if not path.exists():
        if required:
            report.add_finding(
                "missing_input_file",
                "hard_block",
                f"Required input file is missing: {path}",
                overridable=False,
                path=str(path),
            )
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        report.add_finding(
            "input_not_utf8",
            "hard_block",
            f"Input file must be UTF-8 readable: {exc}",
            overridable=False,
            path=str(path),
        )
    except OSError as exc:
        report.add_finding(
            "input_read_failed",
            "hard_block",
            f"Could not read input file: {exc}",
            overridable=False,
            path=str(path),
        )
    return ""


def _load_author_overrides(path: str | Path | None, report: LintReport) -> dict[str, Any]:
    if path is None:
        return {}
    override_path = Path(path)
    if not override_path.exists():
        report.add_finding(
            "author_overrides_missing",
            "hard_block",
            f"Author overrides file does not exist: {override_path}",
            overridable=False,
            path=str(override_path),
        )
        return {}
    try:
        payload = json.loads(override_path.read_text(encoding="utf-8"))
    except Exception as exc:
        report.add_finding(
            "author_overrides_invalid_json",
            "hard_block",
            f"Could not parse author overrides JSON: {exc}",
            overridable=False,
            path=str(override_path),
        )
        return {}
    if not isinstance(payload, dict):
        report.add_finding(
            "author_overrides_not_object",
            "hard_block",
            "Author overrides JSON must be an object.",
            overridable=False,
            path=str(override_path),
        )
        return {}
    return payload


def _check_citations(report: LintReport, citekeys: set[str]) -> None:
    for use in report.citation_uses:
        if use.key not in citekeys:
            report.add_finding(
                "missing_citekey",
                "hard_block",
                f"Citation key `{use.key}` is used in the draft but absent from refs.bib.",
                overridable=False,
                path=str(report.draft_path),
                span_start=use.span_start,
                span_end=use.span_end,
                details={"citekey": use.key, "command": use.command},
            )


def _load_evidence_ledger(run_dir: Path, report: LintReport) -> dict[str, Any]:
    candidates = [
        run_dir / "evidence_ledger.json",
        run_dir / "reports" / "internal" / "evidence_ledger.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except Exception as exc:
                report.add_finding(
                    "invalid_evidence_ledger",
                    "hard_block",
                    f"Could not parse evidence ledger: {exc}",
                    overridable=False,
                    path=str(candidate),
                )
                return {}
            if not isinstance(payload, dict):
                report.add_finding(
                    "invalid_evidence_ledger",
                    "hard_block",
                    "Evidence ledger must contain a JSON object.",
                    overridable=False,
                    path=str(candidate),
                )
                return {}
            return payload
    if report.numeric_uses:
        report.add_finding(
            "evidence_ledger_missing",
            "hard_block",
            "Numeric claims require an evidence_ledger.json with cell-level values.",
            overridable=False,
            path=str(run_dir),
        )
    return {}


def _evidence_values(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    items = ledger.get("evidence_items", [])
    if not isinstance(items, list):
        return values
    for item in items:
        if not isinstance(item, dict):
            continue
        coerced = _coerce_number(item.get("value"))
        if coerced is None:
            continue
        values.append(
            {
                "evidence_id": item.get("evidence_id"),
                "artifact_id": item.get("artifact_id"),
                "model_id": item.get("model_id"),
                "statistic": item.get("statistic"),
                "display_type": item.get("display_type"),
                "value": coerced,
                "raw_value": item.get("value"),
            }
        )
    return values


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if stripped.endswith("%"):
            stripped = stripped[:-1].strip()
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _check_numeric_claims(report: LintReport) -> None:
    if not report.numeric_uses:
        return
    if not report.evidence_values:
        return
    for use in report.numeric_uses:
        matched = [value for value in report.evidence_values if _numbers_match(use.value, float(value["value"]))]
        if matched:
            continue
        nearest = min(
            report.evidence_values,
            key=lambda item: abs(float(item["value"]) - use.value),
            default=None,
        )
        report.add_finding(
            "ledger_inconsistent_number",
            "hard_block",
            f"Draft number `{use.raw}` is not present in the evidence ledger.",
            overridable=False,
            path=str(report.draft_path),
            span_start=use.span_start,
            span_end=use.span_end,
            details={
                "draft_value": use.value,
                "nearest_ledger_value": nearest,
                "context": use.context,
            },
        )


def _numbers_match(left: float, right: float) -> bool:
    tolerance = max(0.0005, abs(right) * 0.0005)
    return abs(left - right) <= tolerance


def _check_language_risks(text: str, report: LintReport) -> None:
    patterns = {
        "causal_language_flag": [
            r"\bcausal\b",
            r"\bcauses?\b",
            r"\beffect of\b",
            r"\bimpact of\b",
            r"\bidentif(?:y|ies|ication)\b",
        ],
        "mechanism_language_flag": [
            r"\bmechanism\b",
            r"\bchannel\b",
            r"\bmediates?\b",
            r"\bproves? the channel\b",
            r"\bconfirms? the mechanism\b",
        ],
        "external_validity_language_flag": [
            r"\bexternal validity\b",
            r"\bgeneraliz(?:e|es|able|ation)\b",
            r"\bglobally\b",
            r"\bworldwide\b",
            r"\ball countries\b",
        ],
        "novelty_or_literature_claim_flag": [
            r"\bfirst paper\b",
            r"\bno previous stud(?:y|ies)\b",
            r"\bclosest paper\b",
            r"\bunlike all prior work\b",
            r"\bliterature establishes\b",
            r"\bconsensus is\b",
        ],
        "contribution_claim_flag": [
            r"\bcontribut(?:e|es|ion)\b",
            r"\bwe add to\b",
            r"\bwe extend\b",
        ],
    }
    messages = {
        "causal_language_flag": "Causal or identification language needs design-gate confirmation.",
        "mechanism_language_flag": "Mechanism language needs diagnostics or author confirmation.",
        "external_validity_language_flag": "External-validity language needs scope support or author confirmation.",
        "novelty_or_literature_claim_flag": "Novelty or literature-positioning language needs citations, notes, or author confirmation.",
        "contribution_claim_flag": "Contribution language should be backed by intake or author confirmation.",
    }
    lowered = text.lower()
    for code, regexes in patterns.items():
        for regex in regexes:
            match = re.search(regex, lowered)
            if not match:
                continue
            report.add_finding(
                code,
                "flag_and_confirm",
                messages[code],
                overridable=True,
                path=str(report.draft_path),
                span_start=match.start(),
                span_end=match.end(),
                details={"matched_text": text[match.start() : match.end()]},
            )
            break


def _check_basic_style(text: str, report: LintReport) -> None:
    if len(re.findall(r"\ba growing literature\b", text, flags=re.IGNORECASE)) >= 2:
        report.add_finding(
            "repeated_generic_literature_phrase",
            "style_advice",
            "Repeated generic literature phrasing is stylistic advice only; it does not block the draft.",
            overridable=True,
            path=str(report.draft_path),
        )


def _apply_author_overrides(report: LintReport) -> None:
    overrides = report.author_overrides.get("overrides") if isinstance(report.author_overrides, dict) else None
    if not isinstance(overrides, list):
        return
    by_code: dict[str, dict[str, Any]] = {}
    by_id: dict[str, dict[str, Any]] = {}
    for item in overrides:
        if not isinstance(item, dict):
            continue
        if item.get("finding_id"):
            by_id[str(item["finding_id"])] = item
        if item.get("code"):
            by_code[str(item["code"])] = item
    for finding in report.findings:
        override = by_id.get(finding.finding_id) or by_code.get(finding.code)
        if not override:
            continue
        reason = str(override.get("reason") or "").strip()
        if not reason:
            finding.details["override_rejected"] = "Author override reason is required."
            continue
        if not finding.overridable:
            finding.details["override_rejected"] = "This finding is non-overridable."
            continue
        finding.author_override = {
            "asserted": True,
            "original_tier": finding.tier,
            "reason": reason,
        }
        finding.tier = "author_asserted"
    report.status = "failed" if report.has_hard_blocks else "passed"


def _write_outputs(report: LintReport, out_dir: Path, citekeys: set[str], draft_text: str) -> None:
    internal = out_dir / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    citation_index = {
        "version": LINT_VERSION,
        "refs_bib_present": bool(report.refs_path and report.refs_path.exists()),
        "citekeys": sorted(citekeys),
        "citation_uses": [use.to_dict() for use in report.citation_uses],
    }
    citation_safety = {
        "version": LINT_VERSION,
        "refs_bib_present": bool(report.refs_path and report.refs_path.exists()),
        "citekeys": sorted(citekeys),
        "missing_citekeys": sorted(
            {
                str(finding.details.get("citekey"))
                for finding in report.findings
                if finding.code == "missing_citekey" and finding.details.get("citekey")
            }
        ),
        "cite_needed": report.cite_needed,
        "external_notes_used": [],
        "findings": [_citation_finding_for_schema(finding) for finding in report.findings if _is_citation_finding(finding)],
    }
    numeric_report = {
        "version": LINT_VERSION,
        "numeric_uses": [use.to_dict() for use in report.numeric_uses],
        "evidence_values": report.evidence_values,
        "findings": [finding.to_dict() for finding in report.findings if "number" in finding.code or "ledger" in finding.code],
    }

    (internal / "run_validation.json").write_text(
        json.dumps(report.run_validation.to_dict() if report.run_validation else {}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (internal / "citation_index.json").write_text(json.dumps(citation_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "citation_safety_report.json").write_text(
        json.dumps(citation_safety, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (internal / "numeric_claims.json").write_text(json.dumps(numeric_report, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "lint_report.json").write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "AUTHOR_REPORT.md").write_text(_author_report_text(report), encoding="utf-8")
    _write_annotated_draft(report, out_dir, draft_text)


def _author_report_text(report: LintReport) -> str:
    hard_blocks = [finding for finding in report.findings if finding.tier == "hard_block"]
    flagged = [finding for finding in report.findings if finding.tier == "flag_and_confirm"]
    author_asserted = [finding for finding in report.findings if finding.tier == "author_asserted"]
    style = [finding for finding in report.findings if finding.tier == "style_advice"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Status Overview",
        "",
        f"- Lint status: `{report.status}`",
        f"- Hard blocks: `{len(hard_blocks)}`",
        f"- Flag-and-confirm items: `{len(flagged)}`",
        f"- Author-asserted items: `{len(author_asserted)}`",
    ]
    if report.run_validation and report.run_validation.public_watermark:
        lines.extend(["", f"**{report.run_validation.public_watermark}**"])
    lines.extend(["", "## Non-Overridable Hard Blocks", ""])
    lines.extend(_finding_lines(hard_blocks) if hard_blocks else ["- None."])
    lines.extend(["", "## Flagged And Downgraded Claims", ""])
    lines.extend(_finding_lines(flagged) if flagged else ["- None."])
    lines.extend(["", "## Author-Asserted Claims", ""])
    lines.extend(_finding_lines(author_asserted, include_override=True) if author_asserted else ["- None."])
    lines.extend(["", "## Citation Safety", ""])
    if report.citation_uses:
        lines.append(f"- Citation commands checked: `{len(report.citation_uses)}`")
    else:
        lines.append("- Citation commands checked: `0`")
    if report.cite_needed:
        for marker in report.cite_needed:
            lines.append(f"- `{marker['claim_id']}`: [CITE_NEEDED] {marker['reason']}")
    lines.extend(["", "## Numeric Claims", ""])
    if report.numeric_uses:
        lines.append(f"- Numeric claims extracted: `{len(report.numeric_uses)}`")
        lines.append(f"- Ledger numeric values available: `{len(report.evidence_values)}`")
    else:
        lines.append("- Numeric claims extracted: `0`")
    lines.extend(["", "## Style Advice", ""])
    lines.extend(_finding_lines(style) if style else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Resolve hard blocks first: missing citekeys, invented/unmapped numbers, or mock-as-real signals.")
    if flagged:
        lines.append("- Add author notes, design diagnostics, or explicit author assertions for flag-and-confirm claims.")
    if not hard_blocks and not flagged:
        lines.append("- No blocking lint issues found. Continue to claim-ledger and section-writing checks.")
    return "\n".join(lines) + "\n"


def _finding_lines(findings: list[LintFinding], *, include_override: bool = False) -> list[str]:
    lines: list[str] = []
    for finding in findings:
        lines.append(f"- `{finding.finding_id}` `{finding.code}` ({finding.tier}): {finding.message}")
        if include_override and finding.author_override:
            lines.append(f"  Author reason: {finding.author_override['reason']}")
    return lines


def _write_annotated_draft(report: LintReport, out_dir: Path, draft_text: str) -> None:
    suffix = ".md" if report.draft_path.suffix.lower() in {".md", ".markdown"} else ".tex"
    target = out_dir / f"annotated_draft{suffix}"
    lines: list[str] = []
    if suffix == ".md":
        lines.append("<!--")
        lines.append("ECONPAPER LINT ANNOTATIONS")
        if report.run_validation and report.run_validation.public_watermark:
            lines.append(report.run_validation.public_watermark)
        for finding in report.findings:
            lines.append(f"- [{finding.tier}] {finding.finding_id} {finding.code}: {finding.message}")
        lines.append("-->")
        lines.append("")
        if report.run_validation and report.run_validation.public_watermark:
            lines.append(f"**{MOCK_WATERMARK}**")
            lines.append("")
    else:
        lines.append("% ECONPAPER LINT ANNOTATIONS")
        if report.run_validation and report.run_validation.public_watermark:
            lines.append(f"% {report.run_validation.public_watermark}")
        for finding in report.findings:
            lines.append(f"% - [{finding.tier}] {finding.finding_id} {finding.code}: {finding.message}")
        lines.append("")
        if report.run_validation and report.run_validation.public_watermark:
            lines.append(f"\\textbf{{{MOCK_WATERMARK}}}")
            lines.append("")
    lines.append(draft_text)
    target.write_text("\n".join(lines), encoding="utf-8")


def _is_citation_finding(finding: LintFinding) -> bool:
    return finding.code in {"missing_citekey", "refs_bib_empty", "missing_input_file", "novelty_or_literature_claim_flag"}


def _citation_finding_for_schema(finding: LintFinding) -> dict[str, Any]:
    tier = finding.tier
    if tier == "author_asserted":
        tier = str((finding.author_override or {}).get("original_tier") or "flag_and_confirm")
    return {
        "finding_id": finding.finding_id,
        "tier": tier,
        "overridable": finding.overridable,
        "message": finding.message,
        "code": finding.code,
        "author_override": finding.author_override,
    }
