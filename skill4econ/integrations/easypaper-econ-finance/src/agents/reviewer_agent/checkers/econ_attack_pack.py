"""
Economics/finance deterministic reviewer attack pack.

The checker catches lightweight but high-impact failure modes that are common
in generated empirical econ/finance drafts: invented coefficients, weak
identification language, and finance look-ahead leakage.
"""
from __future__ import annotations

import re
from typing import Dict, List, TYPE_CHECKING

from ....generation.claim_verifier import (
    find_econ_finance_claim_gate_issues,
    has_claim_anchor,
)
from .base import FeedbackChecker

if TYPE_CHECKING:
    from ..models import FeedbackResult, ReviewContext


_ECON_SECTION_HINTS = {
    "data",
    "empirical_strategy",
    "identification",
    "results",
    "robustness",
    "heterogeneity",
    "mechanisms",
    "institutional_background",
    "theory_or_model",
}
_ECON_CONTEXT_TERMS = (
    "economics",
    "economic",
    "finance",
    "financial",
    "aer",
    "qje",
    "jfe",
    "journal of financial economics",
    "american economic review",
)
_FINANCE_CONTEXT_TERMS = (
    "finance",
    "financial",
    "jfe",
    "journal of financial economics",
    "asset pricing",
    "corporate finance",
    "stock return",
    "bank lending",
)
_NUMBER_RE = re.compile(
    r"(?<![\w])[-+]?\d+(?:\.\d+)?(?:\s*(?:%|\\%|percent|percentage points?|pp|bps?|basis points?))?"
    r"|p\s*[<=>]\s*0?\.\d+|t\s*=\s*[-+]?\d+(?:\.\d+)?",
    re.IGNORECASE,
)
_COEFFICIENT_TERMS = (
    "coefficient",
    "point estimate",
    "estimated effect",
    "effect size",
    "standard error",
    "t-stat",
    "t statistic",
    "p-value",
    "regression estimate",
    "elasticity",
)
_LEAKAGE_TIME_TERMS = (
    "future",
    "subsequent",
    "next-period",
    "next period",
    "forward return",
    "realized return",
    "ex post",
    "post-formation",
)
_LEAKAGE_MODEL_TERMS = (
    "predict",
    "forecast",
    "signal",
    "sort",
    "portfolio",
    "feature",
    "training",
    "model",
    "formation",
    "return",
    "returns",
)
_LEAKAGE_SAFE_TERMS = (
    "lagged",
    "out-of-sample",
    "pre-formation",
    "available at",
    "known at",
    "prior to",
    "excluding future",
    "without future",
    "no look-ahead",
    "avoid look-ahead",
    "avoids look-ahead",
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\])")


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    normalized = _norm(text)
    return any(term in normalized for term in terms)


def _paragraphs(content: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", content or "") if p.strip()]


def _sentences(content: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", content or "").strip()
    if not cleaned:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(cleaned) if s.strip()]


def _is_econ_finance_context(context: "ReviewContext") -> bool:
    meta = context.metadata or {}
    context_blob = " ".join(
        str(value or "")
        for value in (
            context.style_guide,
            meta.get("style_guide"),
            meta.get("venue"),
            meta.get("field"),
            meta.get("paper_type"),
            meta.get("artifact_manifest", {}).get("version", "")
            if isinstance(meta.get("artifact_manifest"), dict)
            else "",
        )
    )
    if _contains_any(context_blob, _ECON_CONTEXT_TERMS):
        return True
    section_names = {str(name).lower() for name in (context.sections or {}).keys()}
    return bool(section_names.intersection(_ECON_SECTION_HINTS))


def _is_finance_context(context: "ReviewContext") -> bool:
    meta = context.metadata or {}
    context_blob = " ".join(
        str(value or "")
        for value in (
            context.style_guide,
            meta.get("style_guide"),
            meta.get("venue"),
            meta.get("field"),
            meta.get("topic"),
            meta.get("artifact_manifest", {}).get("source_agent", "")
            if isinstance(meta.get("artifact_manifest"), dict)
            else "",
            " ".join(context.sections.keys()),
        )
    )
    return _contains_any(context_blob, _FINANCE_CONTEXT_TERMS)


def _coefficient_looks_invented(sentence: str) -> bool:
    return (
        bool(_NUMBER_RE.search(sentence))
        and _contains_any(sentence, _COEFFICIENT_TERMS)
        and not has_claim_anchor(sentence)
    )


def _finance_leakage_risk(sentence: str) -> bool:
    return (
        _contains_any(sentence, _LEAKAGE_TIME_TERMS)
        and _contains_any(sentence, _LEAKAGE_MODEL_TERMS)
        and not _contains_any(sentence, _LEAKAGE_SAFE_TERMS)
    )


class EconAttackPackChecker(FeedbackChecker):
    """Rule-based reviewer attack pack for econ/finance drafts."""

    @property
    def name(self) -> str:
        return "econ_attack_pack"

    @property
    def priority(self) -> int:
        return 11

    async def check(self, context: "ReviewContext") -> "FeedbackResult":
        from ..models import FeedbackResult, Severity

        if not _is_econ_finance_context(context):
            return FeedbackResult(
                checker_name=self.name,
                passed=True,
                severity=Severity.INFO,
                message="Econ/finance attack pack skipped: no econ/finance context detected.",
                details={"active": False},
            )

        finance_context = _is_finance_context(context)
        flags: List[Dict[str, object]] = []

        for section_type, content in (context.sections or {}).items():
            for paragraph_index, paragraph in enumerate(_paragraphs(content)):
                for sentence_index, sentence in enumerate(_sentences(paragraph)):
                    if _coefficient_looks_invented(sentence):
                        flags.append({
                            "kind": "invented_coefficient",
                            "section_type": section_type,
                            "paragraph_index": paragraph_index,
                            "sentence_index": sentence_index,
                            "sentence": sentence[:240],
                            "severity": "error",
                            "message": (
                                "Coefficient-like numeric claim has no local citation, "
                                "table, figure, appendix, or artifact reference."
                            ),
                            "suggested_action": (
                                "Reference the exact result artifact or remove the coefficient."
                            ),
                        })

                    for issue in find_econ_finance_claim_gate_issues(
                        sentence,
                        paragraph_plan=None,
                        section_type=section_type,
                    ):
                        if issue.get("gate") != "identification_claim_without_anchor":
                            continue
                        flags.append({
                            "kind": "weak_identification",
                            "section_type": section_type,
                            "paragraph_index": paragraph_index,
                            "sentence_index": sentence_index,
                            "sentence": sentence[:240],
                            "severity": "warning",
                            "message": issue.get("message", ""),
                            "suggested_action": (
                                "Name the identifying variation, assumptions, controls, "
                                "or supporting empirical-strategy artifact."
                            ),
                        })

                    if finance_context and _finance_leakage_risk(sentence):
                        flags.append({
                            "kind": "finance_leakage",
                            "section_type": section_type,
                            "paragraph_index": paragraph_index,
                            "sentence_index": sentence_index,
                            "sentence": sentence[:240],
                            "severity": "error",
                            "message": (
                                "Finance design may use future or realized returns in "
                                "signal/model formation without lag or availability language."
                            ),
                            "suggested_action": (
                                "Clarify information timing, use lagged/pre-formation inputs, "
                                "or state the out-of-sample construction."
                            ),
                        })

        if not flags:
            return FeedbackResult(
                checker_name=self.name,
                passed=True,
                severity=Severity.INFO,
                message="Econ/finance attack pack passed.",
                details={"active": True, "attack_pack_flags": []},
            )

        paragraph_feedbacks: Dict[str, List[Dict[str, object]]] = {}
        sections_to_revise: Dict[str, str] = {}
        for flag in flags:
            section_type = str(flag["section_type"])
            pidx = int(flag["paragraph_index"])
            sections_to_revise.setdefault(section_type, str(flag["message"]))
            paragraph_feedbacks.setdefault(section_type, []).append({
                "paragraph_index": pidx,
                "paragraph_preview": str(flag["sentence"])[:80],
                "issues": [f"[{flag['kind']}] {flag['message']}"],
                "severity": str(flag["severity"]),
                "suggestion": str(flag["suggested_action"]),
            })

        section_feedbacks: List[Dict[str, object]] = []
        for section_type, feedbacks in paragraph_feedbacks.items():
            para_indices = sorted({int(item["paragraph_index"]) for item in feedbacks})
            section_feedbacks.append({
                "section_type": section_type,
                "current_word_count": context.word_counts.get(section_type, 0),
                "target_word_count": (
                    context.get_section_target(section_type)
                    or context.word_counts.get(section_type, 0)
                ),
                "action": "refine_paragraphs",
                "delta_words": 0,
                "target_paragraphs": para_indices,
                "paragraph_instructions": {
                    idx: (
                        "Resolve econ/finance attack-pack flags without adding new "
                        "unsupported coefficients or causal claims."
                    )
                    for idx in para_indices
                },
                "issue_type": "claim_evidence_gap",
            })

        severity = Severity.ERROR if any(f.get("severity") == "error" for f in flags) else Severity.WARNING
        message = f"Econ/finance attack pack found {len(flags)} issue(s)."
        document_feedbacks = [{
            "level": "document",
            "agent": "reviewer",
            "checker": self.name,
            "target_id": "document",
            "severity": severity.value,
            "issue_type": "econ_reviewer_attack_pack",
            "message": message,
            "suggested_action": "econ_attack_pack_fix",
        }]

        return FeedbackResult(
            checker_name=self.name,
            passed=False,
            severity=severity,
            message=message,
            details={
                "active": True,
                "attack_pack_flags": flags,
                "sections_to_revise": sections_to_revise,
                "paragraph_feedbacks": paragraph_feedbacks,
                "section_feedbacks": section_feedbacks,
                "document_feedbacks": document_feedbacks,
            },
            suggested_action="econ_attack_pack_fix",
        )

    def generate_revision_prompt(
        self,
        section_type: str,
        current_content: str,
        feedback: "FeedbackResult",
    ) -> str:
        flags = [
            flag for flag in feedback.details.get("attack_pack_flags", [])
            if str(flag.get("section_type", "")).lower() == section_type.lower()
        ]
        if not flags:
            return ""

        parts = [
            f"Fix the econ/finance reviewer attack-pack issues in {section_type}.\n",
        ]
        for flag in flags:
            parts.append(
                f"- [{flag.get('kind')}] {flag.get('sentence')} "
                f"-> {flag.get('suggested_action')}"
            )
        parts.append(
            "\nDo not invent coefficients, causal identification, timing assumptions, "
            "or finance signals. Keep only claims supported by cited sources or "
            "explicit table/figure/appendix artifacts."
        )
        parts.append(f"\nCurrent content:\n{current_content}")
        parts.append("\nReturn the revised LaTeX content only.")
        return "\n".join(parts)
