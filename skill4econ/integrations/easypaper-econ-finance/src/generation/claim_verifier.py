"""
Claim-Level Verification for Decomposed Generation
- **Description**:
    - Provides immediate (not post-hoc) verification of paragraph-level
      generated content against the EvidenceDAG and citation database.
    - Three checks run in sequence:
      1. Citation validity — reuses CitationValidatorTool logic.
      2. Evidence anchor — ensures bound evidence IDs are referenced.
      3. Key-point coverage — checks that the paragraph's stated goals
         are reflected in the output.
    - Produces a ``VerificationResult`` with structured feedback that can
      be fed back to the Writer for retry, or trigger degradation to
      template-slot filling.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_CLAIM_RETRIES: int = 3
TEMPLATE_FALLBACK_ENABLED: bool = True


_CITE_PATTERN = re.compile(
    r"\\(?:cite|citep|citet|citealp|parencite|textcite)\{([^}]+)\}"
)
_REF_PATTERN = re.compile(r"\\(?:ref|cref|Cref|autoref)\{([^}]+)\}")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+(?=[A-Z\\])")
_NUMERIC_PATTERN = re.compile(
    r"(?<![\w])[-+]?\d+(?:\.\d+)?(?:\s*(?:%|\\%|percent|percentage points?|"
    r"pp|bps?|basis points?|standard deviations?|s\.d\.|million|billion|trillion))?"
    r"|p\s*[<=>]\s*0?\.\d+|t\s*=\s*[-+]?\d+(?:\.\d+)?|beta\s*=\s*[-+]?\d+(?:\.\d+)?",
    re.IGNORECASE,
)
_EMPIRICAL_NUMERIC_TERMS = (
    "estimate",
    "estimates",
    "estimated",
    "coefficient",
    "effect",
    "increase",
    "decrease",
    "decline",
    "rise",
    "fall",
    "percentage point",
    "basis point",
    "elasticity",
    "standard error",
    "p-value",
    "statistically significant",
    "regression",
    "treatment",
    "treated",
    "control",
    "return",
    "spread",
    "employment",
    "investment",
    "lending",
    "loan",
    "market",
    "revenue",
    "income",
    "profit",
)
_IDENTIFICATION_CLAIM_TERMS = (
    "identify",
    "identifies",
    "identified",
    "identification",
    "causal",
    "causally",
    "exogenous",
    "instrument",
    "treatment effect",
    "difference-in-differences",
    "difference in differences",
    "parallel trends",
    "event study",
)
_IDENTIFICATION_ANCHOR_TERMS = (
    "using",
    "exploiting",
    "leveraging",
    "variation",
    "shock",
    "instrument",
    "fixed effect",
    "fixed effects",
    "parallel trend",
    "parallel trends",
    "event study",
    "difference-in-differences",
    "difference in differences",
    "controls",
    "placebo",
    "pre-trend",
    "pretrend",
    "pre-period",
    "as-if random",
    "quasi-experimental",
    "research design",
    "identifying assumption",
    "exclusion restriction",
    "within",
    "staggered",
    "regression discontinuity",
    "shift-share",
    "lagged",
)
_ROBUSTNESS_CONTEXT_TERMS = (
    "robustness",
    "sensitivity",
    "placebo",
    "falsification",
    "alternative specification",
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
_ARTIFACT_REFERENCE_PATTERN = re.compile(
    r"\b(?:Table|Figure|Fig\.|Panel|Column|Appendix Table|Equation|Eq\.)"
    r"\s*(?:~?\(?\\(?:ref|cref|Cref|autoref)\{|[A-Z]?\d+|\([A-Za-z0-9]+\))",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

class VerificationResult(BaseModel):
    """
    Outcome of claim-level verification on a generated paragraph.
    - **Fields**:
        - ``passed``: Whether all checks passed.
        - ``citation_issues``: Invalid citation keys found.
        - ``unanchored_claims``: Claims not backed by cited evidence.
        - ``missing_evidence_refs``: Bound evidence IDs that should have
          been cited but were not.
        - ``coverage_gaps``: Key points or supporting points not covered.
        - ``feedback_for_retry``: Human-readable feedback to prepend to the
          retry prompt.
    """
    passed: bool = True
    citation_issues: List[str] = Field(default_factory=list)
    unanchored_claims: List[str] = Field(default_factory=list)
    missing_evidence_refs: List[str] = Field(default_factory=list)
    coverage_gaps: List[str] = Field(default_factory=list)
    econ_gate_issues: List[Dict[str, str]] = Field(default_factory=list)
    feedback_for_retry: str = ""


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    normalized = _norm(text)
    return any(term in normalized for term in terms)


def _split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return []
    return [part.strip() for part in _SENTENCE_SPLIT_PATTERN.split(cleaned) if part.strip()]


def _planned_artifact_targets(paragraph_plan: Any) -> Set[str]:
    targets: Set[str] = set()
    if paragraph_plan is None:
        return targets
    for attr in ("figures_to_reference", "tables_to_reference", "bound_evidence_ids"):
        for item in getattr(paragraph_plan, attr, []) or []:
            if item:
                targets.add(str(item))
    for usage in getattr(paragraph_plan, "figure_usages", []) or []:
        figure_id = getattr(usage, "figure_id", "")
        if figure_id:
            targets.add(str(figure_id))
    return targets


def has_claim_anchor(text: str, paragraph_plan: Any = None) -> bool:
    """Return whether text contains a citation, artifact reference, or planned ref target."""
    if _CITE_PATTERN.search(text) or _REF_PATTERN.search(text):
        return True
    if _ARTIFACT_REFERENCE_PATTERN.search(text):
        return True
    for target in _planned_artifact_targets(paragraph_plan):
        if target and target in text:
            return True
    return False


def find_econ_finance_claim_gate_issues(
    text: str,
    paragraph_plan: Any = None,
    section_type: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Find deterministic econ/finance claim-gate issues in generated prose.

    The gates are deliberately lightweight: they only fire on visible empirical
    claim language, require local citation/artifact anchors for numeric claims,
    require identification language to name a design anchor, and prevent a
    robustness section from becoming a new headline-result section.
    """
    issues: List[Dict[str, str]] = []
    plan_blob = " ".join(
        str(value or "")
        for value in (
            getattr(paragraph_plan, "key_point", ""),
            " ".join(getattr(paragraph_plan, "supporting_points", []) or []),
            getattr(paragraph_plan, "role", ""),
            section_type or "",
        )
    )
    robustness_context = _contains_any(plan_blob, _ROBUSTNESS_CONTEXT_TERMS)

    for sentence in _split_sentences(text):
        sentence_lower = _norm(sentence)

        if (
            _NUMERIC_PATTERN.search(sentence)
            and _contains_any(sentence_lower, _EMPIRICAL_NUMERIC_TERMS)
            and not has_claim_anchor(sentence, paragraph_plan)
        ):
            issues.append({
                "gate": "unsupported_numeric_empirical_claim",
                "sentence": sentence[:240],
                "message": (
                    "Numeric empirical claims must cite a source or reference a "
                    "table, figure, appendix artifact, or bound evidence target."
                ),
            })

        if (
            _contains_any(sentence_lower, _IDENTIFICATION_CLAIM_TERMS)
            and not _contains_any(sentence_lower, _IDENTIFICATION_ANCHOR_TERMS)
            and not has_claim_anchor(sentence, paragraph_plan)
        ):
            issues.append({
                "gate": "identification_claim_without_anchor",
                "sentence": sentence[:240],
                "message": (
                    "Identification or causal claims must name the research-design "
                    "anchor, identifying variation, assumption, or supporting artifact."
                ),
            })

        if (
            robustness_context
            and _contains_any(sentence_lower, _ROBUSTNESS_MAIN_RESULT_TERMS)
            and not _contains_any(sentence_lower, _ROBUSTNESS_BRIDGE_TERMS)
        ):
            issues.append({
                "gate": "robustness_as_new_main_result",
                "sentence": sentence[:240],
                "message": (
                    "Robustness sections should bridge back to the main result; "
                    "they should not introduce a new headline result."
                ),
            })

    return issues


# ---------------------------------------------------------------------------
# ClaimVerifier
# ---------------------------------------------------------------------------

class ClaimVerifier:
    """
    Immediate verifier for paragraph-level generated content.
    - **Description**:
        - Designed for use inside the decomposed generation loop
          (``_generate_section_decomposed`` in metadata_agent).
        - Stateless; all context is passed per call.
    """

    async def verify(
        self,
        generated_text: str,
        paragraph_plan: Any,
        evidence_dag: Optional[Any] = None,
        valid_citation_keys: Optional[Set[str]] = None,
        section_type: Optional[str] = None,
    ) -> VerificationResult:
        """
        Run all verification checks on a generated paragraph.
        - **Args**:
            - ``generated_text`` (str): The LaTeX paragraph output.
            - ``paragraph_plan``: ParagraphPlan with claim_id, bound_evidence_ids,
              key_point, supporting_points.
            - ``evidence_dag``: EvidenceDAG instance (optional).
            - ``valid_citation_keys`` (Set[str]): Allowed citation keys.

        - **Returns**:
            - ``VerificationResult``
        """
        result = VerificationResult()
        valid_keys = valid_citation_keys or set()

        self._check_citations(generated_text, valid_keys, result)
        self._check_evidence_anchoring(generated_text, paragraph_plan, evidence_dag, result)
        self._check_coverage(generated_text, paragraph_plan, result)
        self._check_econ_finance_claim_gates(
            generated_text,
            paragraph_plan,
            result,
            section_type=section_type,
        )

        result.passed = (
            not result.citation_issues
            and not result.unanchored_claims
            and not result.missing_evidence_refs
            and not result.coverage_gaps
            and not result.econ_gate_issues
        )

        if not result.passed:
            result.feedback_for_retry = self._build_feedback(result)

        return result

    # ------------------------------------------------------------------
    # Check 1: Citation validity
    # ------------------------------------------------------------------

    @staticmethod
    def _check_citations(
        text: str,
        valid_keys: Set[str],
        result: VerificationResult,
    ) -> None:
        """Verify that every \\cite{} key is in the allowed set."""
        for m in _CITE_PATTERN.finditer(text):
            for key in m.group(1).split(","):
                k = key.strip()
                if k and k not in valid_keys:
                    if k not in result.citation_issues:
                        result.citation_issues.append(k)

    # ------------------------------------------------------------------
    # Check 2: Evidence anchoring
    # ------------------------------------------------------------------

    @staticmethod
    def _check_evidence_anchoring(
        text: str,
        paragraph_plan: Any,
        evidence_dag: Optional[Any],
        result: VerificationResult,
    ) -> None:
        """Ensure bound evidence nodes are actually referenced."""
        bound_ids: List[str] = getattr(paragraph_plan, "bound_evidence_ids", [])
        if not bound_ids:
            return

        text_lower = text.lower()

        cited_keys: Set[str] = set()
        for m in _CITE_PATTERN.finditer(text):
            for key in m.group(1).split(","):
                cited_keys.add(key.strip())

        ref_labels: Set[str] = set()
        for m in _REF_PATTERN.finditer(text):
            ref_labels.add(m.group(1).strip())

        for eid in bound_ids:
            referenced = False
            if eid in cited_keys or eid in ref_labels:
                referenced = True
            elif evidence_dag:
                try:
                    enode = evidence_dag.evidence_nodes.get(eid)
                    if enode:
                        if enode.source_path and enode.source_path in cited_keys:
                            referenced = True
                        elif enode.content and len(enode.content) > 10:
                            snippet_words = enode.content[:60].lower().split()
                            if any(w in text_lower for w in snippet_words[:3]):
                                referenced = True
                except Exception:
                    pass

            if not referenced:
                result.missing_evidence_refs.append(eid)

    # ------------------------------------------------------------------
    # Check 3: Key-point coverage
    # ------------------------------------------------------------------

    @staticmethod
    def _check_coverage(
        text: str,
        paragraph_plan: Any,
        result: VerificationResult,
    ) -> None:
        """Check that the paragraph covers its planned key point."""
        key_point: str = getattr(paragraph_plan, "key_point", "")
        if not key_point:
            return

        text_lower = text.lower()
        kp_words = [w for w in key_point.lower().split() if len(w) > 3]

        if kp_words:
            overlap = sum(1 for w in kp_words if w in text_lower)
            coverage = overlap / len(kp_words)
            if coverage < 0.3:
                result.coverage_gaps.append(
                    f"Key point '{key_point[:80]}...' has low coverage ({coverage:.0%})"
                )

    # ------------------------------------------------------------------
    # Check 4: Econ/finance claim gates
    # ------------------------------------------------------------------

    @staticmethod
    def _check_econ_finance_claim_gates(
        text: str,
        paragraph_plan: Any,
        result: VerificationResult,
        section_type: Optional[str] = None,
    ) -> None:
        """Block unsupported econ/finance empirical and narrative claims."""
        issues = find_econ_finance_claim_gate_issues(
            text,
            paragraph_plan=paragraph_plan,
            section_type=section_type,
        )
        for issue in issues:
            result.econ_gate_issues.append(issue)
            sentence = issue.get("sentence", "")
            if sentence and sentence not in result.unanchored_claims:
                result.unanchored_claims.append(sentence)

    # ------------------------------------------------------------------
    # Feedback builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_feedback(result: VerificationResult) -> str:
        """Compose a retry-prompt from the verification failures."""
        parts: List[str] = ["## Verification Feedback — Please Fix These Issues:\n"]

        if result.citation_issues:
            parts.append(
                f"**Invalid citations**: {', '.join(result.citation_issues)}. "
                "Remove or replace these with valid citation keys."
            )
        if result.missing_evidence_refs:
            parts.append(
                f"**Missing evidence references**: Evidence IDs "
                f"{', '.join(result.missing_evidence_refs)} are bound to this "
                "paragraph but not referenced. Include \\cite{{}} or \\ref{{}} "
                "for each."
            )
        if result.econ_gate_issues:
            for issue in result.econ_gate_issues:
                parts.append(
                    f"**Econ/finance claim gate ({issue.get('gate', 'claim_gate')})**: "
                    f"{issue.get('message', '')} Sentence: {issue.get('sentence', '')}"
                )
        if result.coverage_gaps:
            for gap in result.coverage_gaps:
                parts.append(f"**Coverage gap**: {gap}")

        return "\n".join(parts)
