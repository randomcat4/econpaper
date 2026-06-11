"""
Post-review citation grounding audit and repair helpers.

This module intentionally stays deterministic and metadata-level. It does not
try to solve full semantic entailment; it creates the freeze-point contract that
keeps citation state, final outputs, and user-visible audit artifacts aligned.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from ..shared.reference_pool import ReferencePool


_CITE_RE = re.compile(r"\\(?:cite|citep|citet|citealt|citealp|citeauthor|citeyear)\{([^}]+)\}")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")

_CITATION_KEYWORDS = {
    "citation",
    "cite",
    "citing",
    "cited",
    "reference",
    "references",
    "ref pool",
    "bibliography",
    "bibtex",
    "literature",
    "related work",
    "prior work",
    "foundation",
    "foundational",
    "grounding",
    "unsupported",
    "evidence",
    "claim",
    "search",
    "retrieval",
    "discovery",
    "fact_lock_conflict",
    "canonical fact",
}

_SUPPORT_RE = re.compile(r"\bsupport(?:s|ed|ing)?\b", re.IGNORECASE)
_SUPPORT_FALSE_POSITIVES = {
    "technical support",
    "support code",
    "support files",
}
_REFERENCE_FALSE_POSITIVE_RE = re.compile(
    r"\b(?:figure|fig\.|table|tab\.|section|sec\.|equation|eq\.)\s+references?\b",
    re.IGNORECASE,
)
_QUERY_FALSE_POSITIVE_RE = re.compile(r"\b(?:api|database|sql|code)\s+quer(?:y|ies)\b", re.IGNORECASE)
_LATEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?\{[^}]*\}")
_SUPPORT_STOPWORDS = {
    "about", "across", "after", "again", "against", "also", "among", "based",
    "because", "between", "claim", "cites", "effect", "from", "have", "into",
    "large", "language", "models", "paper", "papers", "research", "section",
    "study", "their", "these", "this", "using", "with", "would",
}


@dataclass
class CitationGroundingAuditResult:
    status: str = "ok"
    records: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_findings: List[Dict[str, Any]] = field(default_factory=list)
    promoted_refs: List[Dict[str, Any]] = field(default_factory=list)
    removed_citations: List[Dict[str, Any]] = field(default_factory=list)
    softened_claims: List[Dict[str, Any]] = field(default_factory=list)
    repair_attempts: List[Dict[str, Any]] = field(default_factory=list)
    sections_changed: bool = False
    references_changed: bool = False
    requires_recompile: bool = False
    artifact_paths: Dict[str, str] = field(default_factory=dict)
    canonical_references_bib: str = "references.bib"
    compile_bib_snapshots: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "records": self.records,
            "unresolved_findings": self.unresolved_findings,
            "promoted_refs": self.promoted_refs,
            "removed_citations": self.removed_citations,
            "softened_claims": self.softened_claims,
            "repair_attempts": self.repair_attempts,
            "sections_changed": self.sections_changed,
            "references_changed": self.references_changed,
            "requires_recompile": self.requires_recompile,
            "artifact_paths": self.artifact_paths,
            "canonical_references_bib": self.canonical_references_bib,
            "compile_bib_snapshots": self.compile_bib_snapshots,
            "summary": {
                "record_count": len(self.records),
                "unresolved_count": len(self.unresolved_findings),
                "promoted_count": len(self.promoted_refs),
                "removed_citation_count": len(self.removed_citations),
                "softened_claim_count": len(self.softened_claims),
                "warning_count": sum(
                    1 for item in self.unresolved_findings
                    if item.get("severity") == "warning"
                ),
                "severe_count": sum(
                    1 for item in self.unresolved_findings
                    if item.get("severity") == "severe"
                ),
            },
            "tags": sorted({
                str(item.get("source", "audit"))
                for item in self.unresolved_findings
                if item.get("source")
            }),
        }

    def to_markdown(self) -> str:
        lines = [
            "# Citation Grounding Audit",
            "",
            f"- Status: `{self.status}`",
            f"- Records: {len(self.records)}",
            f"- Unresolved findings: {len(self.unresolved_findings)}",
            f"- Promoted refs: {len(self.promoted_refs)}",
            f"- Removed citations: {len(self.removed_citations)}",
            f"- Warning findings: {sum(1 for item in self.unresolved_findings if item.get('severity') == 'warning')}",
            f"- Severe findings: {sum(1 for item in self.unresolved_findings if item.get('severity') == 'severe')}",
            "",
        ]
        if self.unresolved_findings:
            lines.extend(["## Unresolved Findings", ""])
            for item in self.unresolved_findings:
                lines.append(
                    f"- **{item.get('severity', 'warning')}** "
                    f"[{item.get('source', 'audit')}] {item.get('reason') or item.get('message') or ''}"
                )
            lines.append("")
        if self.promoted_refs:
            lines.extend(["## Promoted References", ""])
            for item in self.promoted_refs:
                lines.append(f"- `{item.get('ref_id')}`: {item.get('reason', '')}")
            lines.append("")
        return "\n".join(lines)


def _text_from_issue(issue: Dict[str, Any]) -> str:
    fields = (
        "category",
        "severity",
        "title",
        "description",
        "recommendation",
        "section",
        "section_type",
        "expected_change",
        "issue_type",
        "type",
    )
    values: List[str] = []
    for field_name in fields:
        value = issue.get(field_name)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values.extend(str(v) for v in value)
        elif isinstance(value, dict):
            values.extend(str(v) for v in value.values())
        else:
            values.append(str(value))
    return " ".join(values).lower()


def _matches_citation_issue(text: str) -> bool:
    if not text:
        return False
    for phrase in _SUPPORT_FALSE_POSITIVES:
        text = text.replace(phrase, "")
    text = _REFERENCE_FALSE_POSITIVE_RE.sub("", text)
    text = _QUERY_FALSE_POSITIVE_RE.sub("", text)
    if _SUPPORT_RE.search(text):
        return True
    return any(keyword in text for keyword in _CITATION_KEYWORDS)


def escalate_plan_review_citation_findings(
    plan_review: Optional[Dict[str, Any]],
    plan_review_iterations: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    if not plan_review:
        return []

    raw_issues: List[Dict[str, Any]] = []
    for issue in plan_review.get("issues", []) or []:
        if isinstance(issue, dict):
            raw_issues.append(issue)
    for iteration in plan_review_iterations or plan_review.get("iterations", []) or []:
        if not isinstance(iteration, dict):
            continue
        for issue in iteration.get("issues", []) or []:
            if isinstance(issue, dict):
                raw_issues.append(issue)

    findings: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for issue in raw_issues:
        issue_text = _text_from_issue(issue)
        is_fact_lock = str(issue.get("category", "")).lower() == "fact_lock_conflict"
        if not is_fact_lock and str(plan_review.get("final_status", "")).lower() != "needs_revision":
            continue
        if not is_fact_lock and not _matches_citation_issue(issue_text):
            continue
        key = "|".join([
            str(issue.get("category", "")),
            str(issue.get("title", "")),
            str(issue.get("description", ""))[:120],
        ])
        if key in seen:
            continue
        seen.add(key)
        raw_severity = str(issue.get("severity", "")).lower()
        severity = "severe" if raw_severity in {"blocking", "blocker", "major", "severe"} else "warning"
        findings.append(
            {
                "source": "plan_review",
                "severity": severity,
                "reason": (
                    "Canonical fact-lock conflict from planner review."
                    if is_fact_lock
                    else "Unresolved citation-related planner review issue."
                ),
                "issue": issue,
            }
        )
    return findings


def _split_citations(cite_payload: str) -> List[str]:
    return [part.strip() for part in cite_payload.split(",") if part.strip()]


def _support_tokens(text: str) -> Set[str]:
    cleaned = _LATEX_COMMAND_RE.sub(" ", text or "")
    return {
        token
        for token in re.findall(r"[a-z][a-z-]{3,}", cleaned.lower())
        if token not in _SUPPORT_STOPWORDS
    }


def _claim_to_abstract_support(
    *,
    claim: str,
    ref: Optional[Dict[str, Any]],
    authorized: bool,
) -> tuple[str, str, str]:
    if not ref:
        return "unsupported", "severe", "Citation key is not present in the reference pool."
    if not authorized:
        return (
            "unsupported",
            "severe",
            "Citation key is not authorized for this section after grounding freeze.",
        )

    title = str(ref.get("title") or "")
    abstract = str(ref.get("abstract") or "")
    if not abstract:
        return (
            "unverifiable",
            "warning",
            "Citation is section-authorized, but no abstract is available for claim-level support checking.",
        )

    claim_tokens = _support_tokens(claim)
    evidence_tokens = _support_tokens(f"{title} {abstract}")
    overlap = claim_tokens & evidence_tokens
    if len(overlap) >= 4:
        return (
            "supported",
            "ok",
            f"Claim and title/abstract share support concepts: {', '.join(sorted(overlap)[:8])}.",
        )
    if len(overlap) >= 2:
        return (
            "weak_support",
            "warning",
            f"Claim is partially grounded by title/abstract concepts: {', '.join(sorted(overlap)[:8])}.",
        )
    return (
        "unsupported",
        "severe",
        "Citation is section-authorized, but title/abstract do not support the local claim.",
    )


def extract_claim_citation_records(
    generated_sections: Dict[str, str],
    ref_pool: ReferencePool,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for section_type, content in (generated_sections or {}).items():
        chunks = [c.strip() for c in _SENTENCE_RE.split(content or "") if c.strip()]
        for chunk in chunks:
            cite_keys: List[str] = []
            for match in _CITE_RE.finditer(chunk):
                cite_keys.extend(_split_citations(match.group(1)))
            if not cite_keys:
                continue
            for key in dict.fromkeys(cite_keys):
                ref = ref_pool.get_ref(key)
                validation = (ref or {}).get("validation", {}) if ref else {}
                authorized = key in ref_pool.citable_keys(section_type)
                verdict, severity, reason = _claim_to_abstract_support(
                    claim=chunk,
                    ref=ref,
                    authorized=authorized,
                )
                records.append(
                    {
                        "section_type": section_type,
                        "claim": chunk,
                        "citation_key": key,
                        "support_verdict": verdict,
                        "citation_authorized": authorized,
                        "severity": severity,
                        "reason": reason,
                        "evidence": {
                            "title": (ref or {}).get("title", ""),
                            "abstract": (ref or {}).get("abstract", ""),
                            "validation": validation,
                        },
                    }
                )
    return records


def _sync_sections_results(sections_results: List[Any], generated_sections: Dict[str, str]) -> None:
    for section_result in sections_results or []:
        section_type = getattr(section_result, "section_type", "")
        if section_type in generated_sections:
            content = generated_sections[section_type]
            section_result.latex_content = content
            section_result.word_count = len(content.split())


class CitationGroundingCoordinator:
    def run(
        self,
        *,
        ref_pool: ReferencePool,
        generated_sections: Dict[str, str],
        sections_results: List[Any],
        paper_plan: Optional[Any],
        plan_review: Optional[Dict[str, Any]],
        plan_review_iterations: Optional[List[Dict[str, Any]]],
        citation_budget_usage: Optional[List[Dict[str, Any]]],
        memory: Optional[Any],
        paper_dir: Optional[Path],
        max_repair_iterations: int = 1,
    ) -> CitationGroundingAuditResult:
        del paper_plan, citation_budget_usage, paper_dir, max_repair_iterations
        result = CitationGroundingAuditResult()

        result.records = extract_claim_citation_records(generated_sections, ref_pool)
        for record in result.records:
            if record.get("severity") in {"severe", "warning"}:
                result.unresolved_findings.append(
                    {
                        "source": "claim_citation_audit",
                        "severity": record.get("severity", "warning"),
                        "reason": record.get("reason", ""),
                        "record": record,
                    }
                )

        result.unresolved_findings.extend(
            escalate_plan_review_citation_findings(plan_review, plan_review_iterations)
        )

        # Conservative repair: promote already-known reserve citations only when
        # they are actually cited and carry enough metadata for traceability.
        for record in list(result.records):
            if record.get("citation_authorized") is True:
                continue
            key = str(record.get("citation_key", ""))
            ref = ref_pool.get_ref(key)
            if not ref:
                continue
            title = str(ref.get("title") or "")
            abstract = str(ref.get("abstract") or "")
            if not (title or abstract):
                continue
            section_type = str(record.get("section_type") or "global")
            promoted = ref_pool.promote_ref(
                key,
                evidence=f"Promoted during citation grounding audit for {section_type}: {title[:160]}",
                support_tags=[section_type],
                provenance="citation_grounding_repair",
            )
            result.repair_attempts.append(
                {
                    "action": "promote_reserve_ref",
                    "ref_id": key,
                    "section_type": section_type,
                    "success": promoted,
                }
            )
            if promoted:
                result.promoted_refs.append(
                    {
                        "ref_id": key,
                        "section_type": section_type,
                        "reason": "Cited reserve ref promoted with title/abstract metadata during audit.",
                    }
                )
                result.references_changed = True
                result.requires_recompile = True

        if result.references_changed:
            result.records = extract_claim_citation_records(generated_sections, ref_pool)
            result.unresolved_findings = [
                finding
                for finding in result.unresolved_findings
                if not (
                    finding.get("source") == "claim_citation_audit"
                    and finding.get("record", {}).get("citation_key") in {
                        ref.get("ref_id") for ref in result.promoted_refs
                    }
                )
            ]
            existing_claim_keys = {
                (
                    finding.get("record", {}).get("section_type"),
                    finding.get("record", {}).get("citation_key"),
                    finding.get("record", {}).get("claim"),
                )
                for finding in result.unresolved_findings
                if finding.get("source") == "claim_citation_audit"
            }
            for record in result.records:
                if record.get("severity") not in {"severe", "warning"}:
                    continue
                record_key = (
                    record.get("section_type"),
                    record.get("citation_key"),
                    record.get("claim"),
                )
                if record_key in existing_claim_keys:
                    continue
                result.unresolved_findings.append(
                    {
                        "source": "claim_citation_audit",
                        "severity": record.get("severity", "warning"),
                        "reason": record.get("reason", ""),
                        "record": record,
                    }
                )

        if memory is not None:
            for section_type, content in generated_sections.items():
                memory.update_section(section_type, content)
        _sync_sections_results(sections_results, generated_sections)

        result.status = "warnings" if result.unresolved_findings else "ok"
        return result


def sync_sections_results_and_memory(
    *,
    generated_sections: Dict[str, str],
    sections_results: List[Any],
    memory: Optional[Any],
) -> None:
    _sync_sections_results(sections_results, generated_sections)
    if memory is not None:
        for section_type, content in generated_sections.items():
            memory.update_section(section_type, content)
