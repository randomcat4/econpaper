"""
Paragraph-local mini review helpers for MetaDataAgent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..shared.table_converter import inject_float_refs
from ..shared.tools import KeyPointCoverageTool


async def run_local_mini_review(
    *,
    section_type: str,
    paragraph_index: int,
    paragraph_plan,
    raw_latex: str,
    final_latex: str,
    figs_to_ref: List[str],
    tables_to_ref: List[str],
    attempt: int,
    max_attempts: int,
    memory=None,
    validate_required_figure_usages_fn,
    rewrite_content_fn,
) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []

    figures_ok, figure_feedback, missing_figures = validate_required_figure_usages_fn(
        raw_latex=raw_latex,
        final_latex=final_latex,
        paragraph_plan=paragraph_plan,
    )
    if not figures_ok:
        issues.append(
            {
                "issue_type": "missing_required_figure_ref",
                "message": figure_feedback,
                "missing_figures": missing_figures,
                "repairable": True,
            }
        )

    key_point = getattr(paragraph_plan, "key_point", "") or ""
    if key_point:
        kp_tool = KeyPointCoverageTool([key_point])
        kp_result = await kp_tool.execute(content=final_latex)
        coverage = (kp_result.data or {}).get("coverage", 1.0) if kp_result else 1.0
        if coverage < 1.0:
            issues.append(
                {
                    "issue_type": "missing_key_point",
                    "message": (
                        "The paragraph does not clearly realize its key point. "
                        f"Key point: {key_point}"
                    ),
                    "repairable": True,
                }
            )

    if not issues:
        return {
            "status": "passed",
            "latex": final_latex,
            "feedback": "",
            "issues": [],
        }

    repairable = all(bool(issue.get("repairable", False)) for issue in issues)
    target_id = f"{section_type}.p{paragraph_index}"
    combined_feedback = "\n".join(
        issue["message"] for issue in issues if issue.get("message")
    )

    if repairable:
        system_prompt = (
            "You are performing a local mini-review fix for one paragraph.\n"
            "Only repair paragraph-local issues.\n"
            "Preserve LaTeX correctness, citations, and the scientific claim.\n"
            "Return ONLY the revised paragraph text."
        )
        user_prompt = (
            f"Section: {section_type}\n"
            f"Paragraph index: {paragraph_index}\n"
            f"Current paragraph:\n{final_latex}\n\n"
            "Local issues to fix:\n"
            f"{combined_feedback}\n\n"
            "Rules:\n"
            "- Keep the revision local to this paragraph.\n"
            "- Do not change section-level structure or unrelated claims.\n"
            "- If a figure must be referenced, author a real reference in the paragraph itself.\n"
            "- You may use either `[FLOAT:fig:id]` or `Figure~\\ref{fig:id}`.\n"
        )
        revised = await rewrite_content_fn(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            section_type=section_type,
        )
        if revised and revised.strip():
            revised_latex = inject_float_refs(revised.strip(), figs_to_ref, tables_to_ref)
            revised_figures_ok, _, revised_missing_figures = validate_required_figure_usages_fn(
                raw_latex=revised.strip(),
                final_latex=revised_latex,
                paragraph_plan=paragraph_plan,
            )
            kp_ok = True
            if key_point:
                kp_tool = KeyPointCoverageTool([key_point])
                kp_result = await kp_tool.execute(content=revised_latex)
                kp_ok = ((kp_result.data or {}).get("coverage", 1.0) if kp_result else 1.0) >= 1.0

            if revised_figures_ok and kp_ok:
                if memory is not None:
                    memory.add_local_review_event(
                        section_type=section_type,
                        target_id=target_id,
                        level="paragraph",
                        disposition="fixed_locally",
                        issue_type="+".join(issue["issue_type"] for issue in issues),
                        message=combined_feedback,
                        paragraph_index=paragraph_index,
                        evidence={
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                        },
                    )
                return {
                    "status": "fixed_locally",
                    "latex": revised_latex,
                    "feedback": "",
                    "issues": issues,
                }

            if attempt + 1 < max_attempts:
                if memory is not None:
                    memory.add_local_review_event(
                        section_type=section_type,
                        target_id=target_id,
                        level="paragraph",
                        disposition="retry_required",
                        issue_type="+".join(issue["issue_type"] for issue in issues),
                        message=combined_feedback,
                        paragraph_index=paragraph_index,
                        evidence={
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                            "missing_figures": revised_missing_figures,
                        },
                    )
                return {
                    "status": "retry_required",
                    "latex": revised_latex,
                    "feedback": combined_feedback,
                    "issues": issues,
                }

    if memory is not None:
        memory.add_local_review_event(
            section_type=section_type,
            target_id=target_id,
            level="paragraph",
            disposition="escalate",
            issue_type="+".join(issue["issue_type"] for issue in issues),
            message=combined_feedback,
            paragraph_index=paragraph_index,
            evidence={
                "attempt": attempt + 1,
                "max_attempts": max_attempts,
                "repairable": repairable,
                "missing_figures": missing_figures,
            },
        )
    return {
        "status": "escalate",
        "latex": final_latex,
        "feedback": combined_feedback,
        "issues": issues,
    }
