"""
Citation budgeting helpers for PlannerAgent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def estimate_total_citations(
    style_guide: Optional[str],
    n_body_sections: int,
    total_paragraphs: int,
) -> int:
    """
    Estimate total citations for the paper when Planner omits citation_strategy.
    """
    sg = (style_guide or "").lower()

    if any(v in sg for v in ("nature", "science", "cell", "lancet", "nejm")):
        base = 35
    elif any(v in sg for v in ("neurips", "icml", "iclr", "aaai", "cvpr", "acl", "emnlp")):
        base = 30
    elif any(v in sg for v in ("journal", "tpami", "jmlr", "tkde", "tac")):
        base = 45
    elif "workshop" in sg:
        base = 18
    else:
        base = 30

    scale_factor = max(1.0, total_paragraphs / 15.0)
    return max(15, int(base * min(scale_factor, 2.0)))


def distribute_citations_topdown(
    total_target: int,
    body_sections: List["SectionPlan"],
    section_allocation: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """
    Distribute total citation target across body sections by weight.
    """
    targets: Dict[str, int] = {}

    if section_allocation:
        allocated = 0
        for sp in body_sections:
            alloc = section_allocation.get(sp.section_type, {})
            if not isinstance(alloc, dict):
                alloc = {}
            direct_target = alloc.get("target_refs")
            if direct_target is not None:
                t = max(2, int(direct_target))
            else:
                pct = float(alloc.get("share_pct", 0))
                t = max(2, int(total_target * pct / 100.0))
            targets[sp.section_type] = t
            allocated += t
        remainder = total_target - allocated
        for sp in body_sections:
            if sp.section_type not in targets or targets[sp.section_type] <= 2:
                bonus = max(0, remainder // max(1, len(body_sections)))
                targets[sp.section_type] = targets.get(sp.section_type, 2) + bonus
    else:
        total_paras = sum(len(sp.paragraphs) for sp in body_sections) or 1
        for sp in body_sections:
            n_paras = max(1, len(sp.paragraphs))
            share = n_paras / total_paras
            targets[sp.section_type] = max(2, int(total_target * share))

    return targets


def rank_references_for_section(
    papers: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Rank section candidate papers by relevance, quality and recency.
    """
    return sorted(
        papers,
        key=lambda p: (
            float(p.get("relevance_score") or 0.0),
            int(p.get("citation_count") or 0),
            int(p.get("year") or 0),
        ),
        reverse=True,
    )


def infer_section_citation_budget(
    section_type: str,
    paragraph_count: int,
    candidate_refs: List[Dict[str, Any]],
    planner_hint_refs: List[str],
    core_ref_keys: List[str],
    planner_budget: Optional[Dict[str, Any]] = None,
    topdown_target: Optional[int] = None,
    evidence_dag: Optional[Any] = None,
    section_plan: Optional[Any] = None,
    claim_matrix_refs: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Infer per-section citation budget, prioritizing planner-provided budget.
    """
    candidate_keys = [p.get("ref_id", "") for p in candidate_refs if p.get("ref_id")]
    allowed_key_set = set(candidate_keys) | set(core_ref_keys)

    dag_citation_refs: List[str] = []
    if evidence_dag is not None and section_plan is not None:
        try:
            for para in getattr(section_plan, "paragraphs", []):
                for eid in getattr(para, "bound_evidence_ids", []):
                    node = evidence_dag.get_node(eid)
                    if node is not None:
                        ref_id = getattr(node, "ref_id", "") or ""
                        if ref_id and ref_id in allowed_key_set and ref_id not in dag_citation_refs:
                            dag_citation_refs.append(ref_id)
        except Exception:
            pass
    planner_hint_refs = [r for r in planner_hint_refs if r in allowed_key_set]
    claim_refs = [r for r in (claim_matrix_refs or []) if r in allowed_key_set]
    high_quality = [
        p for p in candidate_refs
        if float(p.get("relevance_score") or 0.0) >= 8.0
        or int(p.get("citation_count") or 0) >= 80
    ]
    candidate_count = len(candidate_keys) + len(core_ref_keys)
    normalized_budget = planner_budget or {}
    budget_min = normalized_budget.get("min_refs")
    budget_target = normalized_budget.get("target_refs")
    budget_max = normalized_budget.get("max_refs")

    if budget_target is not None:
        target_refs = max(0, int(budget_target))
    elif topdown_target is not None and topdown_target > 0:
        target_refs = topdown_target
    else:
        complexity_signal = max(1, paragraph_count)
        evidence_signal = len(planner_hint_refs) + max(0, len(high_quality) // 2)
        target_refs = max(3, complexity_signal + evidence_signal)

    if budget_min is not None:
        min_refs = max(0, int(budget_min))
    else:
        min_refs = max(1, min(target_refs, max(paragraph_count, 3)))

    if budget_max is not None:
        max_refs = max(int(budget_max), target_refs, min_refs)
    else:
        max_refs = max(target_refs, min_refs, candidate_count)

    must_use_refs: List[str] = []
    for rid in dag_citation_refs:
        if rid and rid not in must_use_refs:
            must_use_refs.append(rid)
    for rid in claim_refs:
        if rid and rid not in must_use_refs:
            must_use_refs.append(rid)
    for rid in planner_hint_refs:
        if rid and rid not in must_use_refs:
            must_use_refs.append(rid)
        if len(must_use_refs) >= 3 + len(dag_citation_refs):
            break
    for p in high_quality:
        rid = p.get("ref_id", "")
        if rid and rid in allowed_key_set and rid not in must_use_refs:
            must_use_refs.append(rid)
        if len(must_use_refs) >= 4:
            break

    selected_refs: List[str] = []
    for rid in must_use_refs:
        if rid and rid not in selected_refs:
            selected_refs.append(rid)

    for rid in candidate_keys:
        if len(selected_refs) >= target_refs:
            break
        if rid and rid not in selected_refs:
            selected_refs.append(rid)

    for rid in core_ref_keys:
        if len(selected_refs) >= min_refs:
            break
        if rid and rid not in selected_refs:
            selected_refs.append(rid)

    reserve_refs: List[str] = []
    for rid in candidate_keys:
        if rid and rid not in selected_refs and rid not in reserve_refs:
            reserve_refs.append(rid)
        if len(reserve_refs) >= 8:
            break

    return {
        "section_type": section_type,
        "min_refs": min_refs,
        "target_refs": target_refs,
        "max_refs": max_refs,
        "candidate_count": candidate_count,
        "must_use_refs": must_use_refs,
        "selected_refs": selected_refs[:max_refs] if max_refs > 0 else selected_refs,
        "reserve_refs": reserve_refs,
        "planner_hint_refs": planner_hint_refs[:8],
        "planner_budget_used": bool(budget_target is not None),
    }
