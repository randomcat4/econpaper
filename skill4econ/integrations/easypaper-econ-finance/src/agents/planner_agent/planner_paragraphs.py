"""
Paragraph and sentence planning helpers for PlannerAgent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ParagraphPlan, SentencePlan, SentenceRole


def generate_sentence_plans(
    paragraph_plan: ParagraphPlan,
    evidence_dag: Optional[Any] = None,
) -> List[SentencePlan]:
    """
    Generate explicit sentence-level plans for a paragraph.
    """
    bound_ids = list(getattr(paragraph_plan, "bound_evidence_ids", []) or [])
    claim_id = getattr(paragraph_plan, "claim_id", "")
    n_sentences = getattr(paragraph_plan, "approx_sentences", 5)

    plans: List[SentencePlan] = []
    prefix = claim_id or "p"

    if bound_ids and evidence_dag is not None:
        plans.append(
            SentencePlan(
                sentence_id=f"{prefix}.s0",
                claim_id=claim_id,
                role=SentenceRole.TOPIC,
                approx_words=25,
            )
        )
        for i, eid in enumerate(bound_ids):
            ev_ids = [eid]
            approx_w = 20
            try:
                node = evidence_dag.get_node(eid)
                if node is not None:
                    approx_w = min(40, max(15, len(str(getattr(node, "content", ""))) // 5))
            except Exception:
                pass
            plans.append(
                SentencePlan(
                    sentence_id=f"{prefix}.s{i + 1}",
                    claim_id=claim_id,
                    evidence_ids=ev_ids,
                    role=SentenceRole.EVIDENCE,
                    approx_words=approx_w,
                )
            )
        plans.append(
            SentencePlan(
                sentence_id=f"{prefix}.s{len(bound_ids) + 1}",
                claim_id=claim_id,
                role=SentenceRole.CONCLUSION,
                approx_words=20,
            )
        )
    else:
        for i in range(n_sentences):
            if i == 0:
                role = SentenceRole.TOPIC
            elif i == n_sentences - 1:
                role = SentenceRole.CONCLUSION
            else:
                role = SentenceRole.EVIDENCE
            plans.append(
                SentencePlan(
                    sentence_id=f"{prefix}.s{i}",
                    claim_id=claim_id,
                    role=role,
                    approx_words=20,
                )
            )
    return plans


def normalize_string_list(raw: Any, max_items: int = 5) -> List[str]:
    """
    Normalize mixed list/string into a clean bounded string list.
    """
    if isinstance(raw, str):
        items = [x.strip() for x in raw.split(",") if x.strip()]
    elif isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        items = []
    deduped: List[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


def coerce_bool(raw: Any) -> bool:
    """
    Coerce bool from permissive raw JSON value.
    """
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    return text in {"1", "true", "yes", "y", "recommended"}


def generate_default_paragraphs(
    section_type: str,
    section_sentences: int,
    llm_section: Dict[str, Any],
) -> List[ParagraphPlan]:
    """
    Generate default paragraph structure when LLM doesn't provide one.
    """
    key_points = llm_section.get("key_points", [])
    refs = llm_section.get("references_to_cite", [])

    default_structures = {
        "abstract": [
            ("Research problem and motivation", "motivation", 2),
            ("Method and key results", "summary", 3),
        ],
        "introduction": [
            ("Research context and motivation", "motivation", 5),
            ("Problem statement and gap", "problem_statement", 4),
            ("Contributions", "summary", 4),
            ("Paper organization", "transition", 2),
        ],
        "related_work": [
            ("Prior work overview", "evidence", 5),
            ("Comparison and gaps", "comparison", 4),
        ],
        "method": [
            ("Overview of approach", "definition", 4),
            ("Technical details", "evidence", 6),
            ("Implementation specifics", "evidence", 4),
        ],
        "experiment": [
            ("Experimental setup", "definition", 4),
            ("Datasets and baselines", "evidence", 4),
        ],
        "result": [
            ("Main results", "evidence", 5),
            ("Analysis and discussion", "comparison", 4),
        ],
        "conclusion": [
            ("Summary of contributions", "summary", 4),
            ("Future work", "transition", 3),
        ],
    }

    if key_points:
        n_paragraphs = len(key_points)
        sentences_per = max(3, section_sentences // n_paragraphs)
        paragraphs = []
        for i, kp in enumerate(key_points):
            role = "evidence"
            kp_lower = str(kp).lower()
            if "motivation" in kp_lower or "context" in kp_lower:
                role = "motivation"
            elif "conclusion" in kp_lower or "summary" in kp_lower:
                role = "summary"
            elif "organization" in kp_lower or "roadmap" in kp_lower:
                role = "transition"
            paragraphs.append(
                ParagraphPlan(
                    key_point=str(kp),
                    supporting_points=[],
                    approx_sentences=sentences_per,
                    role=role,
                    references_to_cite=refs[:2] if i < len(refs) else [],
                )
            )
        return paragraphs

    structures = default_structures.get(
        section_type,
        [("Main content", "evidence", max(3, section_sentences))],
    )

    return [
        ParagraphPlan(
            key_point=key_point,
            supporting_points=[],
            approx_sentences=approx_sentences,
            role=role,
            references_to_cite=refs[:2] if refs else [],
        )
        for key_point, role, approx_sentences in structures
    ]


def expand_paragraph_plan(
    existing: List[ParagraphPlan],
    target_sentences: int,
    section_type: str,
) -> List[ParagraphPlan]:
    """
    Expand a paragraph plan when the LLM underestimates needed depth.
    """
    if not existing:
        return existing

    expanded = [p.model_copy(deep=True) for p in existing]

    while sum(p.approx_sentences for p in expanded) < target_sentences * 0.75:
        made_progress = False
        for para in expanded:
            if sum(p.approx_sentences for p in expanded) >= target_sentences * 0.75:
                break
            if para.approx_sentences >= 8:
                continue
            para.approx_sentences = min(8, para.approx_sentences + 3)
            made_progress = True
        if not made_progress:
            break

    round_idx = 0
    while sum(p.approx_sentences for p in expanded) < target_sentences * 0.75:
        source = existing[round_idx % len(existing)]
        elaboration = ParagraphPlan(
            key_point=f"Further analysis of: {source.key_point}",
            supporting_points=["Additional evidence", "Extended discussion"],
            approx_sentences=min(
                6,
                max(3, (target_sentences - sum(p.approx_sentences for p in expanded)) // 3),
            ),
            role=source.role if source.role != "motivation" else "evidence",
            references_to_cite=[],
        )
        expanded.append(elaboration)
        round_idx += 1
        if round_idx > len(existing) * 3:
            break

    return expanded
