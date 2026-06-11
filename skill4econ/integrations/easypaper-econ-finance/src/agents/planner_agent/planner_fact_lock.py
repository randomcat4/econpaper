"""
Canonical fact lock for planner review iterations.

The optimizer may rewrite structure and narrative planning fields, but it must
not silently mutate stable metadata/reference facts.  This module restores
canonical facts after optimizer output and reports conflicts as plan-review
issues.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Dict, Iterable, List

from .models import PaperPlan, PlanReviewIssue, PlanReviewSeverity


@dataclass
class CanonicalReferenceFact:
    ref_id: str
    title: str = ""
    year: int | None = None
    venue: str = ""
    abstract: str = ""
    first_author: str = ""


@dataclass
class CanonicalFactLock:
    title: str = ""
    reference_facts: List[CanonicalReferenceFact] = field(default_factory=list)
    figure_ids: List[str] = field(default_factory=list)
    table_ids: List[str] = field(default_factory=list)


def _bibtex_field(entry: str, field_name: str) -> str:
    match = re.search(
        rf"{field_name}\s*=\s*[{{\"]([^}}\"]+)[}}\"]",
        entry or "",
        re.IGNORECASE | re.DOTALL,
    )
    return " ".join(match.group(1).split()) if match else ""


def _bibtex_key(entry: str) -> str:
    match = re.search(r"@\w+\{([^,]+),", entry or "")
    return match.group(1).strip() if match else ""


def _first_author(authors: str) -> str:
    first = re.split(r"\s+and\s+|,", authors or "", maxsplit=1)[0].strip()
    if not first:
        return ""
    parts = [p for p in re.split(r"\s+", first) if p]
    return re.sub(r"[^A-Za-z-]", "", parts[-1]) if parts else ""


def _parse_reference_facts(references: Iterable[str]) -> List[CanonicalReferenceFact]:
    facts: List[CanonicalReferenceFact] = []
    for entry in references or []:
        ref_id = _bibtex_key(entry)
        title = _bibtex_field(entry, "title")
        year_text = _bibtex_field(entry, "year")
        authors = _bibtex_field(entry, "author")
        abstract = _bibtex_field(entry, "abstract")
        venue = _bibtex_field(entry, "journal") or _bibtex_field(entry, "booktitle")
        year = int(year_text) if year_text.isdigit() else None
        if ref_id or title or year:
            facts.append(
                CanonicalReferenceFact(
                    ref_id=ref_id,
                    title=title,
                    year=year,
                    venue=venue,
                    abstract=abstract,
                    first_author=_first_author(authors),
                )
            )
    return facts


def build_canonical_fact_lock(plan: PaperPlan, request: Any) -> CanonicalFactLock:
    figure_ids = [getattr(fig, "id", "") for fig in getattr(request, "figures", []) or []]
    table_ids = [getattr(tbl, "id", "") for tbl in getattr(request, "tables", []) or []]
    return CanonicalFactLock(
        title=plan.title,
        reference_facts=_parse_reference_facts(getattr(request, "references", []) or []),
        figure_ids=[fid for fid in figure_ids if fid],
        table_ids=[tid for tid in table_ids if tid],
    )


def _walk_strings(value: Any):
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if isinstance(child, str):
                yield value, key, child
            else:
                yield from _walk_strings(child)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            if isinstance(child, str):
                yield value, idx, child
            else:
                yield from _walk_strings(child)


def _restore_reference_year_mentions(
    plan_data: Dict[str, Any],
    ref: CanonicalReferenceFact,
) -> List[Dict[str, Any]]:
    if not ref.first_author or not ref.year:
        return []
    conflicts: List[Dict[str, Any]] = []
    author = re.escape(ref.first_author)
    canonical_year = str(ref.year)
    patterns = [
        re.compile(rf"\b({author}\s+et\s+al\.\s*\()([12]\d{{3}})(\))", re.IGNORECASE),
        re.compile(rf"\b({author}\s+et\s+al\.,?\s+)([12]\d{{3}})\b", re.IGNORECASE),
    ]
    for parent, key, text in _walk_strings(plan_data):
        new_text = text
        for pattern in patterns:
            def repl(match):
                found_year = match.group(2)
                if found_year == canonical_year:
                    return match.group(0)
                conflicts.append(
                    {
                        "ref_id": ref.ref_id,
                        "title": ref.title,
                        "canonical_year": canonical_year,
                        "found_year": found_year,
                    }
                )
                return f"{match.group(1)}{canonical_year}{match.group(3) if len(match.groups()) >= 3 else ''}"

            new_text = pattern.sub(repl, new_text)
        if new_text != text:
            parent[key] = new_text
    return conflicts


def apply_canonical_fact_lock(
    plan: PaperPlan,
    fact_lock: CanonicalFactLock,
    *,
    iteration: int,
) -> tuple[PaperPlan, List[PlanReviewIssue]]:
    """
    Restore locked facts after optimizer output.
    """
    plan_data = plan.model_dump(mode="json")
    conflicts: List[Dict[str, Any]] = []

    if fact_lock.title and plan_data.get("title") != fact_lock.title:
        conflicts.append(
            {
                "field": "title",
                "canonical": fact_lock.title,
                "found": plan_data.get("title", ""),
            }
        )
        plan_data["title"] = fact_lock.title

    for ref in fact_lock.reference_facts:
        conflicts.extend(_restore_reference_year_mentions(plan_data, ref))

    restored = PaperPlan.model_validate(plan_data)
    issues: List[PlanReviewIssue] = []
    for idx, conflict in enumerate(conflicts, start=1):
        issues.append(
            PlanReviewIssue(
                issue_id=f"iter-{iteration}-fact-lock-{idx}",
                category="fact_lock_conflict",
                severity=PlanReviewSeverity.MINOR,
                title="Canonical fact restored after planner optimization",
                description=(
                    "Planner optimizer output conflicted with locked metadata/reference facts: "
                    f"{conflict}"
                ),
                recommendation="Keep canonical metadata/reference facts and revise only mutable plan structure.",
                expected_plan_change="Canonical fact was restored before accepting the revised plan.",
            )
        )
    return restored, issues
