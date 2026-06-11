"""
Deterministic plan-review rules for paper plans.

These checks cover structural conventions that are easier and more reliable to
validate locally than to rediscover through an LLM critic on every run.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set

from .models import (
    PaperPlan,
    ParagraphPlan,
    PlanReviewIssue,
    PlanReviewSeverity,
    SectionPlan,
)


_CONTRIBUTION_TERMS = (
    "contribution",
    "contributions",
    "we introduce",
    "we propose",
    "we present",
    "we make",
    "our work",
    "our paper",
    "in summary",
    "summarized as follows",
)

_RESULT_TABLE_TERMS = (
    "ablation",
    "accuracy",
    "auc",
    "benchmark",
    "bleu",
    "captioning",
    "comparison",
    "experiment",
    "experimental",
    "f1",
    "fine-tuned",
    "finetuned",
    "iou",
    "metric",
    "performance",
    "precision",
    "recall",
    "result",
    "retrieval",
    "rouge",
    "score",
    "sota",
    "state-of-the-art",
    "vqa",
    "zero-shot",
)

_INTRO_SUITABLE_TABLE_TERMS = (
    "background",
    "concept",
    "conceptual",
    "data overview",
    "dataset overview",
    "definitions",
    "notation",
    "problem setup",
    "setting",
    "symbol",
    "taxonomy",
    "terminology",
    "variables",
)

_RESULT_FIGURE_TERMS = (
    "ablation",
    "accuracy",
    "auc",
    "benchmark",
    "chart",
    "comparison",
    "curve",
    "data visualization",
    "experiment",
    "experimental",
    "f1",
    "metric",
    "performance",
    "plot",
    "precision",
    "recall",
    "result",
    "score",
    "zero shot",
)

_NON_RESULT_FIGURE_TERMS = (
    "architecture",
    "conceptual",
    "conceptual framework",
    "framework",
    "info figure",
    "infograph",
    "pipeline",
    "protocol",
    "system",
    "taxonomy",
    "workflow",
)

_NON_RESULT_FIGURE_ROLES = (
    "architecture",
    "conceptual_framework",
    "info_figure",
    "pipeline",
    "protocol",
    "taxonomy",
)

_ROBUSTNESS_MAIN_RESULT_TERMS = (
    "new main result",
    "new primary result",
    "additional main result",
    "main result is",
    "primary finding is",
    "central finding is",
    "headline result",
    "robustness checks reveal",
    "robustness reveals",
    "robustness shows a new",
)

_ROBUSTNESS_BRIDGE_TERMS = (
    "confirm",
    "confirms",
    "support",
    "supports",
    "consistent",
    "stable",
    "remain",
    "remains",
    "unchanged",
    "robust to",
    "does not overturn",
)


def _norm(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _text_blob(*values: Any) -> str:
    return " ".join(_norm(v) for v in values if v is not None)


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    normalized_terms = (_norm(term) for term in terms)
    return any(term and term in text for term in normalized_terms)


def is_intro_like_section(section_type: str) -> bool:
    """Return whether a section should be treated as introduction-like."""
    normalized = _norm(section_type).replace(" ", "_")
    return normalized == "introduction" or normalized.startswith("introduction_")


def is_related_work_like_section(section_type: str) -> bool:
    normalized = _norm(section_type).replace(" ", "_")
    return normalized == "related_work" or normalized.startswith("related_work_")


def is_method_like_section(section_type: str) -> bool:
    normalized = _norm(section_type).replace(" ", "_")
    return normalized in {"method", "methodology"} or normalized.startswith(("method_", "methodology_"))


def is_robustness_like_section(section_type: str) -> bool:
    normalized = _norm(section_type).replace(" ", "_")
    return normalized == "robustness" or normalized.startswith(("robustness_", "sensitivity_"))


def is_contribution_summary_paragraph_for_section(
    section_type: str,
    paragraph: ParagraphPlan,
) -> bool:
    """
    Identify contribution-summary paragraphs without tying behavior to a venue.

    A paragraph can use ``prose_with_list`` for many reasons. We only classify it
    as a contribution summary when the section is introduction-like and the
    paragraph text/role carries contribution-summary intent.
    """
    presentation = getattr(paragraph, "presentation", None)
    if getattr(presentation, "mode", "prose") != "prose_with_list":
        return False
    if not is_intro_like_section(section_type):
        return False

    text = _text_blob(
        getattr(paragraph, "key_point", ""),
        " ".join(getattr(paragraph, "supporting_points", []) or []),
        getattr(presentation, "list_label", ""),
        " ".join(getattr(presentation, "list_items", []) or []),
    )
    return _contains_any(text, _CONTRIBUTION_TERMS)


def is_contribution_summary_paragraph(
    section: SectionPlan,
    paragraph: ParagraphPlan,
) -> bool:
    """Return whether a paragraph is a contribution summary in its section."""
    return is_contribution_summary_paragraph_for_section(
        getattr(section, "section_type", ""),
        paragraph,
    )


def is_advisory_plan_issue(issue: PlanReviewIssue) -> bool:
    """
    Return whether a major issue should remain advisory for optimization flow.

    Introduction result-table placement is a major planning concern, but the
    planner should treat it as a strong recommendation rather than an absolute
    rejection criterion because some introduction tables are legitimate.
    """
    return getattr(issue, "category", "") == "table_placement"


def _flatten_section_paragraphs(section: SectionPlan) -> List[ParagraphPlan]:
    all_paragraphs = getattr(section, "_all_paragraphs", None)
    if callable(all_paragraphs):
        return list(all_paragraphs())
    return list(getattr(section, "paragraphs", []) or [])


def _table_snapshot(table_id: str, provenance: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not provenance:
        return {}
    item = provenance.get(table_id, {})
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return item if isinstance(item, Mapping) else {}


def _figure_snapshot(figure_id: str, provenance: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    if not provenance:
        return {}
    item = provenance.get(figure_id, {})
    if hasattr(item, "model_dump"):
        return item.model_dump()
    return item if isinstance(item, Mapping) else {}


def _object_snapshot(item: Any) -> Mapping[str, Any]:
    if not item:
        return {}
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if isinstance(item, Mapping):
        return item
    snapshot: Dict[str, Any] = {}
    for key in (
        "id",
        "figure_id",
        "table_id",
        "caption",
        "description",
        "content",
        "section",
        "source",
        "data_source",
        "semantic_role",
        "message",
        "position_hint",
        "suggested_section",
        "caption_guidance",
        "supplementation_rationale",
        "target_type",
        "generated_by",
    ):
        if hasattr(item, key):
            snapshot[key] = getattr(item, key)
    return snapshot


def _semantic_values(data: Mapping[str, Any], keys: Iterable[str]) -> List[Any]:
    return [data.get(key, "") for key in keys]


def classify_intro_table_semantics(
    table_id: str,
    placement: Optional[Any] = None,
    table_provenance: Optional[Mapping[str, Any]] = None,
    table_info: Optional[Any] = None,
    table_analysis: Optional[Any] = None,
) -> str:
    """
    Classify table semantics for introduction placement review.

    Returns ``"result_like"``, ``"intro_suitable"``, or ``"unknown"``.
    Unknown tables are not rejected; the rule is a recommendation with high
    confidence only when semantic signals are visible.
    """
    placement_data = _object_snapshot(placement)
    source_data = _table_snapshot(table_id, table_provenance)
    info_data = _object_snapshot(table_info)
    analysis_data = _object_snapshot(table_analysis)
    blob = _text_blob(
        table_id,
        *_semantic_values(
            placement_data,
            ("table_id", "semantic_role", "message", "position_hint"),
        ),
        *_semantic_values(
            source_data,
            ("id", "caption", "description", "content", "section", "source", "data_source"),
        ),
        *_semantic_values(
            info_data,
            ("id", "caption", "description", "content", "section", "source", "data_source"),
        ),
        *_semantic_values(
            analysis_data,
            (
                "semantic_role",
                "message",
                "suggested_section",
                "caption_guidance",
                "caption",
                "description",
            ),
        ),
    )
    if _contains_any(blob, _RESULT_TABLE_TERMS):
        return "result_like"
    if _contains_any(blob, _INTRO_SUITABLE_TABLE_TERMS):
        return "intro_suitable"
    return "unknown"


def classify_figure_semantics(
    figure_id: str,
    placement: Optional[Any] = None,
    figure_provenance: Optional[Mapping[str, Any]] = None,
    figure_info: Optional[Any] = None,
    figure_analysis: Optional[Any] = None,
) -> str:
    """Classify figure semantics for deterministic placement review."""
    placement_data = _object_snapshot(placement)
    source_data = _figure_snapshot(figure_id, figure_provenance)
    info_data = _object_snapshot(figure_info)
    analysis_data = _object_snapshot(figure_analysis)
    blob = _text_blob(
        figure_id,
        *_semantic_values(
            placement_data,
            ("figure_id", "semantic_role", "message", "position_hint", "caption_guidance"),
        ),
        *_semantic_values(
            source_data,
            (
                "id",
                "caption",
                "description",
                "section",
                "semantic_role",
                "supplementation_rationale",
                "target_type",
                "generated_by",
            ),
        ),
        *_semantic_values(
            info_data,
            (
                "id",
                "caption",
                "description",
                "section",
                "semantic_role",
                "supplementation_rationale",
                "target_type",
            ),
        ),
        *_semantic_values(
            analysis_data,
            ("semantic_role", "message", "suggested_section", "caption_guidance"),
        ),
    )
    role = _norm(source_data.get("semantic_role", "") or info_data.get("semantic_role", ""))
    if role in {_norm(item) for item in _NON_RESULT_FIGURE_ROLES}:
        return "non_result_visual"
    if _contains_any(blob, _RESULT_FIGURE_TERMS):
        return "result_like"
    if _contains_any(blob, _NON_RESULT_FIGURE_TERMS):
        return "non_result_visual"
    return "unknown"


def _table_issue(
    *,
    section_type: str,
    table_id: str,
    source: str,
    placement: Optional[Any],
    table_provenance: Optional[Mapping[str, Any]],
) -> Optional[PlanReviewIssue]:
    classification = classify_intro_table_semantics(
        table_id,
        placement=placement,
        table_provenance=table_provenance,
    )
    if classification != "result_like":
        return None
    return PlanReviewIssue(
        issue_id=f"det-intro-result-table-{section_type}-{source}-{table_id}",
        section_type=section_type,
        category="table_placement",
        severity=PlanReviewSeverity.MAJOR,
        title="Result-like table planned in Introduction",
        description=(
            f"Introduction plans to {source.replace('_', ' ')} table '{table_id}', "
            "whose available metadata looks like results, performance, benchmark, "
            "or experiment evidence."
        ),
        recommendation=(
            "Move result/performance table definition and table-specific references "
            "to the relevant method, experiment, result, or analysis section. In the "
            "Introduction, quote essential numbers directly unless the table is "
            "explicitly conceptual, background, notation, or dataset overview material."
        ),
        expected_plan_change=(
            f"Remove table '{table_id}' from introduction table definitions/references "
            "or add explicit non-results justification in table metadata/placement."
        ),
    )


def find_intro_table_placement_issues(
    plan: PaperPlan,
    table_provenance: Optional[Mapping[str, Any]] = None,
) -> List[PlanReviewIssue]:
    """Find result-like table definitions/references in introduction sections."""
    issues: List[PlanReviewIssue] = []
    seen: Set[str] = set()

    for section in getattr(plan, "sections", []) or []:
        section_type = getattr(section, "section_type", "")
        if not is_intro_like_section(section_type):
            continue

        for placement in getattr(section, "tables", []) or []:
            table_id = getattr(placement, "table_id", "") or ""
            if not table_id:
                continue
            issue = _table_issue(
                section_type=section_type,
                table_id=table_id,
                source="define",
                placement=placement,
                table_provenance=table_provenance,
            )
            if issue and issue.issue_id not in seen:
                seen.add(issue.issue_id)
                issues.append(issue)

    return issues


def find_figure_placement_issues(
    plan: PaperPlan,
    figure_provenance: Optional[Mapping[str, Any]] = None,
) -> List[PlanReviewIssue]:
    """Find misplaced result-like figures and unused figure assignments."""
    issues: List[PlanReviewIssue] = []
    seen: Set[str] = set()

    for section in getattr(plan, "sections", []) or []:
        section_type = getattr(section, "section_type", "")
        planned_refs: Set[str] = set(getattr(section, "figures_to_reference", []) or [])
        for paragraph in _flatten_section_paragraphs(section):
            planned_refs.update(getattr(paragraph, "figures_to_reference", []) or [])
            for usage in getattr(paragraph, "figure_usages", []) or []:
                figure_id = str(getattr(usage, "figure_id", "") or "")
                if figure_id:
                    planned_refs.add(figure_id)

        for placement in getattr(section, "figures", []) or []:
            figure_id = getattr(placement, "figure_id", "") or ""
            if not figure_id:
                continue
            classification = classify_figure_semantics(
                figure_id,
                placement=placement,
                figure_provenance=figure_provenance,
            )
            if (
                classification == "result_like"
                and (
                    is_intro_like_section(section_type)
                    or is_related_work_like_section(section_type)
                    or is_method_like_section(section_type)
                )
            ):
                issue = PlanReviewIssue(
                    issue_id=f"det-misplaced-result-figure-{section_type}-{figure_id}",
                    section_type=section_type,
                    category="figure_placement",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Result-like figure planned in a non-result section",
                    description=(
                        f"Section '{section_type}' defines figure '{figure_id}', "
                        "whose metadata looks like empirical results, performance, "
                        "benchmark, or ablation evidence."
                    ),
                    recommendation=(
                        "Move result-like figure definitions to result, evaluation, "
                        "experiment, analysis, or discussion sections. Early sections "
                        "may reference later-defined results only when the narrative "
                        "explicitly justifies that preview."
                    ),
                    expected_plan_change=(
                        f"Remove figure '{figure_id}' from section '{section_type}' "
                        "or replace it with a non-result conceptual/pipeline visual."
                    ),
                )
                if issue.issue_id not in seen:
                    seen.add(issue.issue_id)
                    issues.append(issue)

            if figure_id not in planned_refs:
                issue = PlanReviewIssue(
                    issue_id=f"det-unused-assigned-figure-{section_type}-{figure_id}",
                    section_type=section_type,
                    category="figure_usage",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Assigned figure lacks paragraph-level usage",
                    description=(
                        f"Figure '{figure_id}' is defined in section '{section_type}' "
                        "but no paragraph declares figures_to_reference or figure_usages for it."
                    ),
                    recommendation=(
                        "Attach the figure to a paragraph-level usage contract so the "
                        "writer has a concrete place and purpose for referencing it."
                    ),
                    expected_plan_change=(
                        f"Add '{figure_id}' to an appropriate paragraph's "
                        "figures_to_reference/figure_usages or remove the assignment."
                    ),
                )
                if issue.issue_id not in seen:
                    seen.add(issue.issue_id)
                    issues.append(issue)

    return issues


def find_contribution_terminal_list_issues(plan: PaperPlan) -> List[PlanReviewIssue]:
    """
    Ensure contribution-summary list guidance treats the list as terminal.

    This does not say every ``prose_with_list`` paragraph must end with a list.
    It applies only to introduction-like contribution-summary paragraphs.
    """
    issues: List[PlanReviewIssue] = []
    for section in getattr(plan, "sections", []) or []:
        if not is_intro_like_section(getattr(section, "section_type", "")):
            continue
        for idx, paragraph in enumerate(_flatten_section_paragraphs(section)):
            if not is_contribution_summary_paragraph(section, paragraph):
                continue
            presentation = getattr(paragraph, "presentation", None)
            closing = str(getattr(presentation, "closing_guidance", "") or "").strip()
            if not closing:
                continue
            issues.append(
                PlanReviewIssue(
                    issue_id=(
                        f"det-intro-contribution-terminal-list-"
                        f"{section.section_type}-p{idx}"
                    ),
                    section_type=section.section_type,
                    paragraph_locator=f"p{idx}",
                    category="presentation",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Contribution list is not terminal",
                    description=(
                        "The introduction contribution-summary paragraph is planned "
                        "as prose_with_list but still carries closing/roadmap guidance "
                        "after the itemized contribution points."
                    ),
                    recommendation=(
                        "Keep the prose lead-in before the itemized contribution list, "
                        "make the itemize block the terminal rhetorical unit, and move "
                        "roadmap or closing prose before the list or into a separate "
                        "paragraph."
                    ),
                    expected_plan_change=(
                        "Clear presentation.closing_guidance for this contribution "
                        "summary paragraph or relocate it outside the terminal list."
                    ),
                )
            )
    return issues


def find_conclusion_structure_issues(plan: PaperPlan) -> List[PlanReviewIssue]:
    """Require a standalone conclusion in current full-paper plans."""
    sections = list(getattr(plan, "sections", []) or [])
    if len(sections) < 3:
        return []

    issues: List[PlanReviewIssue] = []
    has_conclusion = any(
        _norm(getattr(section, "section_type", "")) == "conclusion"
        for section in sections
    )
    if not has_conclusion:
        issues.append(
            PlanReviewIssue(
                issue_id="det-missing-standalone-conclusion",
                section_type="conclusion",
                category="structure",
                severity=PlanReviewSeverity.BLOCKER,
                title="Standalone conclusion section missing",
                description=(
                    "The full-paper plan does not include a dedicated conclusion "
                    "section, so synthesis can skip the conclusion entirely."
                ),
                recommendation=(
                    "Add a standalone conclusion section after the body sections."
                ),
                expected_plan_change=(
                    "Append a section with section_type='conclusion' and title "
                    "'Conclusion'."
                ),
            )
        )

    for section in sections:
        section_type = _norm(getattr(section, "section_type", ""))
        title = _norm(getattr(section, "section_title", ""))
        if section_type == "discussion" and "conclusion" in title:
            issues.append(
                PlanReviewIssue(
                    issue_id="det-merged-discussion-conclusion-title",
                    section_type="discussion",
                    category="structure",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Discussion title merges conclusion",
                    description=(
                        "The discussion section title still merges conclusion into "
                        "discussion even though full-paper outputs require a "
                        "standalone conclusion."
                    ),
                    recommendation=(
                        "Rename the discussion section to 'Discussion' and keep "
                        "conclusion content in the dedicated conclusion section."
                    ),
                    expected_plan_change=(
                        "Set the discussion section_title to 'Discussion'."
                    ),
                )
            )
    return issues


def find_robustness_narrative_bridge_issues(plan: PaperPlan) -> List[PlanReviewIssue]:
    """Find robustness plans that introduce a new headline result."""
    issues: List[PlanReviewIssue] = []
    for section in getattr(plan, "sections", []) or []:
        section_type = getattr(section, "section_type", "")
        section_title = getattr(section, "section_title", "")
        if not (
            is_robustness_like_section(section_type)
            or "robustness" in _norm(section_title)
            or "sensitivity" in _norm(section_title)
        ):
            continue
        for idx, paragraph in enumerate(_flatten_section_paragraphs(section)):
            blob = _text_blob(
                section_type,
                section_title,
                getattr(paragraph, "key_point", ""),
                " ".join(getattr(paragraph, "supporting_points", []) or []),
                getattr(paragraph, "role", ""),
            )
            if not _contains_any(blob, _ROBUSTNESS_MAIN_RESULT_TERMS):
                continue
            if _contains_any(blob, _ROBUSTNESS_BRIDGE_TERMS):
                continue
            issues.append(
                PlanReviewIssue(
                    issue_id=f"det-robustness-new-main-result-{section_type}-p{idx}",
                    section_type=section_type,
                    paragraph_locator=f"p{idx}",
                    category="econ_narrative_bridge",
                    severity=PlanReviewSeverity.MAJOR,
                    title="Robustness planned as a new main result",
                    description=(
                        "The robustness section is planned to introduce a new "
                        "main/headline result instead of checking whether the "
                        "primary result survives alternative specifications."
                    ),
                    recommendation=(
                        "Reframe robustness as confirmation, sensitivity, placebo, "
                        "or falsification evidence that bridges back to the main "
                        "results section. Move any genuinely new headline finding "
                        "to Results or Heterogeneity."
                    ),
                    expected_plan_change=(
                        "Rewrite this robustness paragraph so it explicitly "
                        "connects to the main result rather than presenting a new "
                        "central finding."
                    ),
                )
            )
    return issues


def deterministic_plan_review_issues(
    plan: PaperPlan,
    table_provenance: Optional[Mapping[str, Any]] = None,
    figure_provenance: Optional[Mapping[str, Any]] = None,
) -> List[PlanReviewIssue]:
    """Return deterministic plan-review issues for structural plan contracts."""
    return [
        *find_conclusion_structure_issues(plan),
        *find_robustness_narrative_bridge_issues(plan),
        *find_contribution_terminal_list_issues(plan),
        *find_intro_table_placement_issues(plan, table_provenance=table_provenance),
        *find_figure_placement_issues(plan, figure_provenance=figure_provenance),
    ]
