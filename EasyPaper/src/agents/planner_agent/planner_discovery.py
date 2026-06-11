"""
Discovery and research-context helpers for PlannerAgent.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .planner_query_policy import (
    passes_query_quality_gate,
)
from .planner_utils import safe_load_json


def _passes_query_quality_gate(query: str, paper_title: str, key_points: List[str]) -> bool:
    return passes_query_quality_gate(
        query,
        title=paper_title,
        concept_anchors=key_points[:6],
    )


def build_context_fallback_payload(
    *,
    plan: "PaperPlan",
    discovered: Dict[str, List[Dict[str, Any]]],
    all_papers: List[Dict[str, Any]],
    assign_papers_to_sections_fn,
) -> Dict[str, Any]:
    paper_assignments = assign_papers_to_sections_fn(plan, discovered)
    claim_evidence_matrix: List[Dict[str, Any]] = []
    for section_type, refs in paper_assignments.items():
        if section_type in {"abstract", "conclusion"}:
            continue
        if not refs:
            continue
        claim_evidence_matrix.append(
            {
                "section_type": section_type,
                "claim": f"Key findings and arguments in {section_type} should be supported by assigned evidence.",
                "support_refs": refs[:4],
                "reason": "Fallback mapping from section assignment after context parsing failure.",
                "priority": "P1",
            }
        )

    contribs = list(plan.contributions or [])
    p0 = contribs[:2]
    p1 = contribs[2:4]
    p2 = contribs[4:6]
    contribution_ranking = {
        "P0": [
            {
                "contribution": c,
                "why_it_matters": "Core contribution from planner output.",
                "suggested_sections": ["introduction", "methods", "results"],
                "suggested_result_focus": "Highlight primary quantitative gains.",
            }
            for c in p0
        ],
        "P1": [
            {
                "contribution": c,
                "why_it_matters": "Important but secondary contribution.",
                "suggested_sections": ["discussion", "results"],
                "suggested_result_focus": "Position as supporting evidence.",
            }
            for c in p1
        ],
        "P2": [
            {
                "contribution": c,
                "why_it_matters": "Optional or auxiliary contribution.",
                "suggested_sections": ["discussion"],
                "suggested_result_focus": "Mention briefly if space allows.",
            }
            for c in p2
        ],
    }

    return {
        "research_area": "Research area analysis",
        "summary": f"Found {len(all_papers)} relevant papers across {len(discovered)} sections.",
        "key_papers": [],
        "research_trends": [],
        "gaps": [],
        "claim_evidence_matrix": claim_evidence_matrix,
        "contribution_ranking": contribution_ranking,
        "planning_decision_trace": [
            "Used heuristic fallback context because structured JSON parsing failed."
        ],
        "paper_assignments": paper_assignments,
    }


async def generate_search_queries(
    *,
    client,
    model_name: str,
    section_type: str,
    key_points: List[str],
    existing_refs: List[str],
    paper_title: str,
    logger,
) -> List[str]:
    kp_text = "; ".join(key_points[:4])
    refs_text = ", ".join(existing_refs[:10]) if existing_refs else "none"
    prompt = (
        f"Paper: {paper_title}\n"
        f"Section: {section_type}\n"
        f"Key points: {kp_text}\n"
        f"Existing references: {refs_text}\n\n"
        "Generate 1-2 academic search queries to find relevant papers "
        "for this section. Output JSON: {\"queries\": [\"...\"]}"
    )
    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an academic research assistant. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        data = safe_load_json(raw, expected=dict)
        if data is None:
            raise ValueError("Could not parse JSON object from query generation output")
        queries = data.get("queries", [])
        gated = [
            " ".join(q.split()).strip()
            for q in queries
            if isinstance(q, str) and _passes_query_quality_gate(q, paper_title, key_points)
        ]
        if len(gated) < len([q for q in queries if isinstance(q, str)]):
            logger.info(
                "planner.query_generation_gate section=%s kept=%d raw=%d",
                section_type,
                len(gated),
                len([q for q in queries if isinstance(q, str)]),
            )
        return list(dict.fromkeys(gated))
    except Exception as e:
        logger.warning("planner.query_generation_error section=%s: %s", section_type, e)
        return []


async def filter_papers_by_relevance(
    *,
    client,
    model_name: str,
    papers: List[Dict[str, Any]],
    section_type: str,
    key_points: List[str],
    paper_title: str,
    logger,
) -> List[Dict[str, Any]]:
    if not papers:
        return []

    paper_list = []
    for i, p in enumerate(papers):
        paper_list.append(
            {
                "index": i,
                "title": p.get("title", ""),
                "year": p.get("year", ""),
                "venue": p.get("venue", ""),
                "abstract": p.get("abstract", "")[:300] if p.get("abstract") else "",
            }
        )

    kp_text = "; ".join(key_points[:4])
    papers_json = json.dumps(paper_list, ensure_ascii=False)
    prompt = (
        f"Paper: {paper_title}\n"
        f"Section: {section_type}\n"
        f"Key points: {kp_text}\n\n"
        f"Discovered papers:\n{papers_json}\n\n"
        "Evaluate each paper's relevance to this section on a scale of 0-10. "
        "Consider: (1) relevance to key points, (2) paper quality (venue, citations), "
        "(3) recency (prefer papers from the last 5 years). "
        "Output JSON array with format: "
        "[{\"index\": 0, \"relevance_score\": 8, \"reason\": \"brief justification\"}]"
    )

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an academic research assistant. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        evaluations = safe_load_json(raw, expected=list)
        if evaluations is None:
            raise ValueError("Could not parse JSON array from relevance output")

        score_map: Dict[int, Dict[str, Any]] = {}
        for ev in evaluations:
            idx = ev.get("index")
            if idx is not None and 0 <= idx < len(papers):
                score_map[idx] = {
                    "relevance_score": ev.get("relevance_score", 0),
                    "reason": ev.get("reason", ""),
                }

        filtered = []
        for i, paper in enumerate(papers):
            score_info = score_map.get(i, {})
            score = score_info.get("relevance_score", 0)
            if score >= 5:
                paper["relevance_score"] = score
                paper["relevance_reason"] = score_info.get("reason", "")
                filtered.append(paper)

        logger.info(
            "planner.filter_papers section=%s input=%d output=%d",
            section_type, len(papers), len(filtered),
        )
        return filtered
    except Exception as e:
        logger.warning("planner.filter_error section=%s: %s", section_type, e)
        return []


async def score_papers_by_relevance(
    *,
    client,
    model_name: str,
    research_topic: str,
    papers: List[Dict[str, Any]],
    logger,
) -> List[tuple]:
    if not papers:
        return []

    paper_summaries = []
    for i, p in enumerate(papers):
        paper_summaries.append(
            {
                "index": i,
                "title": p.get("title", ""),
                "abstract": p.get("abstract", "")[:300] if p.get("abstract") else "",
            }
        )

    papers_json = json.dumps(paper_summaries, ensure_ascii=False)
    system_msg = (
        "You are an academic research analyst. Score each paper's relevance to the research topic. "
        "Respond with JSON only."
    )
    user_prompt = (
        f"Research topic: {research_topic}\n\n"
        f"Papers to score:\n{papers_json}\n\n"
        "Score each paper's relevance to the research topic on a scale of 0-10. "
        "Consider: topical relevance, methodological relevance, and how directly the paper "
        "informs or supports the research topic.\n\n"
        "Output ONLY a JSON array of objects with 'index' and 'relevance_score' fields:\n"
        "[{\"index\": 0, \"relevance_score\": 8.5}, {\"index\": 1, \"relevance_score\": 6.0}, ...]"
    )

    try:
        response = await client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content or ""
        scores_data = safe_load_json(raw, expected=list)
        if scores_data is None:
            logger.warning("planner.score_papers_by_relevance: failed to parse LLM output")
            return [(p, 0.0) for p in papers]

        score_map: Dict[int, float] = {}
        for item in scores_data:
            if isinstance(item, dict) and "index" in item and "relevance_score" in item:
                score_map[item["index"]] = float(item["relevance_score"])

        scored_papers = [(papers[i], score_map.get(i, 0.0)) for i in range(len(papers))]
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        return scored_papers
    except Exception as e:
        logger.warning("planner.score_papers_by_relevance error: %s", e)
        return [(p, 0.0) for p in papers]


async def generate_research_context(
    *,
    client,
    model_name: str,
    plan: "PaperPlan",
    discovered: Dict[str, List[Dict[str, Any]]],
    logger,
    score_papers_by_relevance_fn,
    assign_papers_to_sections_fn,
) -> Dict[str, Any]:
    all_papers: List[Dict[str, Any]] = []
    for section_papers in discovered.values():
        all_papers.extend(section_papers)

    if not all_papers:
        return {
            "research_area": "",
            "summary": "No papers discovered.",
            "key_papers": [],
            "research_trends": [],
            "gaps": [],
            "paper_assignments": {},
        }

    scored_papers = await score_papers_by_relevance_fn(
        research_topic=plan.title,
        papers=all_papers,
    )
    analysis_papers = [p for p, _ in scored_papers[:24]]
    paper_summaries = []
    for p in analysis_papers:
        paper_summaries.append(
            {
                "citation_key": p.get("ref_id", p.get("citation_key", "")),
                "title": p.get("title", ""),
                "year": p.get("year"),
                "venue": p.get("venue", ""),
                "citation_count": p.get("citation_count"),
                "abstract": p.get("abstract", "")[:200] if p.get("abstract") else "",
            }
        )

    papers_json = json.dumps(paper_summaries, ensure_ascii=False)
    prompt = (
        f"Paper title: {plan.title}\n\n"
        f"Discovered papers:\n{papers_json}\n\n"
        "Analyze these papers and provide a JSON response with:\n"
        "1. research_area: Main research area/topic (brief)\n"
        "2. summary: Overview of the research landscape (2-3 sentences)\n"
        "3. key_papers: Top 5 most important papers with their contributions\n"
        "4. research_trends: 2-3 key research trends identified\n"
        "5. gaps: 2-3 research gaps or opportunities\n"
        "6. claim_evidence_matrix: 6-10 records with {section_type, claim, support_refs, reason, priority}\n"
        "7. contribution_ranking: object with keys P0/P1/P2, each item has "
        "{contribution, why_it_matters, suggested_sections, suggested_result_focus}\n"
        "8. planning_decision_trace: short list of explicit trade-off decisions\n"
        "Output ONLY JSON with this structure:\n"
        "{\"research_area\": \"...\", \"summary\": \"...\", "
        "\"key_papers\": [{\"title\": \"...\", \"contribution\": \"...\"}], "
        "\"research_trends\": [\"...\"], \"gaps\": [\"...\"], "
        "\"claim_evidence_matrix\": [{\"section_type\": \"method\", \"claim\": \"...\", "
        "\"support_refs\": [\"ref1\"], \"reason\": \"...\", \"priority\": \"P0\"}], "
        "\"contribution_ranking\": {\"P0\": [], \"P1\": [], \"P2\": []}, "
        "\"planning_decision_trace\": [\"...\"]}"
    )

    max_attempts = 3
    llm_raw_outputs: List[str] = []
    context: Optional[Dict[str, Any]] = None

    system_msg = "You are an academic research analyst. Respond with JSON only."
    repair_system_msg = "You are a strict JSON fixer. Return JSON object only."
    repair_prompt_template = (
        "Convert the following model output into a STRICT valid JSON object. "
        "Keep only these keys: research_area, summary, key_papers, research_trends, gaps, "
        "claim_evidence_matrix, contribution_ranking, planning_decision_trace.\n"
        "Rules:\n"
        "- Output ONLY JSON object, no markdown/code fences.\n"
        "- If a field is missing, fill with empty default.\n"
        "- contribution_ranking must be an object with keys P0/P1/P2 (arrays).\n"
        "- claim_evidence_matrix and planning_decision_trace must be arrays.\n\n"
        "Raw output:\n{raw_output}"
    )

    for attempt in range(1, max_attempts + 1):
        try:
            temperature = max(0.1, 0.4 - 0.1 * attempt)
            response = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            )
            raw = response.choices[0].message.content or ""
            llm_raw_outputs.append(raw)
            logger.info("planner.research_context attempt=%d/%d raw_len=%d", attempt, max_attempts, len(raw))

            context = safe_load_json(raw, expected=dict)
            if context is not None:
                break

            repair_resp = await client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": repair_system_msg},
                    {"role": "user", "content": repair_prompt_template.format(raw_output=raw[:12000])},
                ],
                temperature=0.0,
            )
            repaired_raw = repair_resp.choices[0].message.content or ""
            llm_raw_outputs.append(f"[repair_attempt_{attempt}] {repaired_raw}")
            context = safe_load_json(repaired_raw, expected=dict)
            if context is not None:
                logger.info("planner.research_context attempt=%d/%d parsed via repair", attempt, max_attempts)
                break

            logger.warning("planner.research_context attempt=%d/%d parse_failed", attempt, max_attempts)
        except Exception as e:
            logger.warning("planner.research_context attempt=%d/%d error: %s", attempt, max_attempts, e)

    paper_assignments = assign_papers_to_sections_fn(plan, discovered)

    if context is not None:
        fallback_context = build_context_fallback_payload(
            plan=plan,
            discovered=discovered,
            all_papers=all_papers,
            assign_papers_to_sections_fn=assign_papers_to_sections_fn,
        )
        parsed_claim_matrix = context.get("claim_evidence_matrix", [])
        parsed_ranking = context.get("contribution_ranking", {"P0": [], "P1": [], "P2": []})
        ranking_empty = (
            not isinstance(parsed_ranking, dict)
            or (not parsed_ranking.get("P0") and not parsed_ranking.get("P1") and not parsed_ranking.get("P2"))
        )

        return {
            "research_area": context.get("research_area", ""),
            "summary": context.get("summary", ""),
            "key_papers": context.get("key_papers", [])[:10],
            "research_trends": context.get("research_trends", []),
            "gaps": context.get("gaps", []),
            "claim_evidence_matrix": parsed_claim_matrix if parsed_claim_matrix else fallback_context.get("claim_evidence_matrix", []),
            "contribution_ranking": parsed_ranking if not ranking_empty else fallback_context.get("contribution_ranking", {"P0": [], "P1": [], "P2": []}),
            "planning_decision_trace": context.get("planning_decision_trace", []),
            "paper_assignments": paper_assignments,
        }

    logger.warning("planner.research_context all %d attempts failed, using fallback", max_attempts)
    fallback = build_context_fallback_payload(
        plan=plan,
        discovered=discovered,
        all_papers=all_papers,
        assign_papers_to_sections_fn=assign_papers_to_sections_fn,
    )
    fallback["_llm_raw_outputs"] = llm_raw_outputs
    return fallback


def assign_papers_to_sections(
    plan: "PaperPlan",
    discovered: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[str]]:
    assignments: Dict[str, List[str]] = {}
    for section_type, papers in discovered.items():
        citation_keys = [p.get("ref_id", "") for p in papers if p.get("ref_id")]
        assignments[section_type] = citation_keys
    return assignments
