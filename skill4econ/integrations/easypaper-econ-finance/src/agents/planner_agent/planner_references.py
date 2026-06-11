"""
Reference discovery and assignment helpers for PlannerAgent.
"""
from __future__ import annotations

import asyncio
import random
import math
from typing import Any, Dict, List, Optional

from ..shared.reference_assignment import claim_matrix_refs_for_section
from ..shared.tools.paper_search import PaperSearchTool
from .planner_query_policy import (
    extract_concept_anchors,
    passes_query_quality_gate,
    query_tokens as _query_tokens,
)


UTILITY_LITERATURE_TRIGGERS: List[tuple[str, str]] = [
    ("imagenet", "ImageNet large scale visual recognition Deng 2009"),
    ("cifar-10", "CIFAR-10 dataset learning multiple layers"),
    ("cifar-100", "CIFAR-100 dataset"),
    ("pytorch", "PyTorch Paszke automatic differentiation"),
    ("tensorflow", "TensorFlow Abadi machine learning"),
    ("mnist", "MNIST handwritten digit database"),
    ("bleu", "BLEU Papineni machine translation evaluation"),
    ("rouge", "ROUGE Lin summarization evaluation"),
    ("coco dataset", "COCO dataset Lin Microsoft common objects"),
]


def _has_auditable_abstract(paper: Dict[str, Any]) -> bool:
    return bool(str(paper.get("title") or "").strip()) and bool(
        str(paper.get("abstract") or "").strip()
    )


def _passes_query_quality_gate(query: str, title: str, concept_anchors: List[str]) -> bool:
    return passes_query_quality_gate(
        query,
        title=title,
        concept_anchors=concept_anchors,
    )


def _extract_concept_anchors(core_analysis: Any, title: str, idea_hypothesis: str) -> List[str]:
    blobs = [title or "", idea_hypothesis or ""]
    for attr in ("shared_gaps", "research_lineage", "positioning_statement"):
        value = getattr(core_analysis, attr, "")
        if isinstance(value, list):
            blobs.extend(str(item) for item in value[:6])
        else:
            blobs.append(str(value or ""))
    for item in getattr(core_analysis, "items", None) or []:
        if isinstance(item, dict):
            blobs.extend([str(item.get("title", "")), str(item.get("gap", ""))])
        else:
            blobs.extend([str(getattr(item, "title", "")), str(getattr(item, "gap", ""))])
    anchors = extract_concept_anchors(*blobs)
    if len(anchors) < 4:
        title_terms = [token for token in _query_tokens(title) if token not in {"llm", "based"}]
        anchors.extend(title_terms[:4])
    return list(dict.fromkeys(anchors))


def _build_landscape_queries(core_analysis: Any, title: str, idea_hypothesis: str) -> List[str]:
    anchors = _extract_concept_anchors(core_analysis, title, idea_hypothesis)
    templates = [
        "{a} literature review",
        "{a} measurement experiments",
        "{a} cognitive bias agents",
        "{a} large language models evaluation",
    ]
    queries: List[str] = []
    for anchor in anchors:
        for template in templates:
            query = template.format(a=anchor)
            if _passes_query_quality_gate(query, title, anchors):
                queries.append(query)
    return list(dict.fromkeys(queries))


def _build_section_fallback_queries(
    *,
    section_type: str,
    key_points: List[str],
    title: str,
    max_queries: int,
) -> List[str]:
    anchors = extract_concept_anchors(" ".join(key_points), title)
    if not anchors:
        anchors = [
            token
            for point in key_points[:4]
            for token in _query_tokens(point)
            if len(token) >= 4
        ][:6]

    templates_by_section: Dict[str, List[str]] = {
        "introduction": [
            "{a} large language models social simulation",
            "{a} psychological experiments large language models",
            "{a} cognitive bias evaluation llm agents",
        ],
        "related_work": [
            "{a} literature review large language models",
            "{a} prior work psychological experiments",
            "{a} social simulation generative agents",
            "{a} cognitive bias machine psychology",
        ],
        "method": [
            "{a} measurement methodology large language models",
            "{a} experimental paradigm cognitive psychology",
            "{a} log probabilities surprisal response latency",
        ],
        "result": [
            "{a} empirical evaluation large language models",
            "{a} benchmark results cognitive bias",
        ],
        "discussion": [
            "{a} limitations social simulation large language models",
            "{a} implications cognitive bias llm agents",
            "{a} reliability validity psychological simulation",
        ],
    }
    templates = templates_by_section.get(
        section_type,
        [
            "{a} large language models evaluation",
            "{a} empirical study cognitive bias",
        ],
    )

    queries: List[str] = []
    for anchor in anchors[:8]:
        for template in templates:
            query = template.format(a=anchor)
            if _passes_query_quality_gate(query, title, anchors):
                normalized = " ".join(query.split()).strip()
                if normalized not in queries:
                    queries.append(normalized)
            if len(queries) >= max_queries:
                return queries
    return queries


def _build_search_tool(cfg: Dict[str, Any]) -> PaperSearchTool:
    return PaperSearchTool(
        serpapi_api_key=cfg.get("serpapi_api_key"),
        semantic_scholar_api_key=cfg.get("semantic_scholar_api_key"),
        timeout=cfg.get("timeout", 10),
        semantic_scholar_min_results_before_fallback=cfg.get(
            "semantic_scholar_min_results_before_fallback", 3
        ),
        enable_query_cache=cfg.get("enable_query_cache", True),
        cache_ttl_hours=cfg.get("cache_ttl_hours", 24),
    )


async def discover_landscape_references(
    *,
    core_analysis: Any,
    title: str,
    idea_hypothesis: str,
    paper_search_config: Optional[Dict[str, Any]],
    logger,
) -> List[Dict[str, Any]]:
    cfg = paper_search_config or {}
    tool = _build_search_tool(cfg)

    max_queries = max(4, min(10, int(cfg.get("planner_landscape_max_queries", 8))))
    per_round = max(3, int(cfg.get("search_results_per_round", 5)))
    delay_sec = max(0.5, float(cfg.get("planner_inter_round_delay_sec", 1.5)))

    queries = _build_landscape_queries(core_analysis, title, idea_hypothesis)
    if not queries:
        logger.info("planner.landscape_reference_discovery skipped=no_quality_queries")
        return []

    discovered: List[Dict[str, Any]] = []
    seen_keys: set[str] = set()
    for idx, query in enumerate(queries[:max_queries]):
        if idx > 0:
            await asyncio.sleep(delay_sec)
        try:
            result = await tool.execute(query=query, max_results=per_round)
            if not result.success:
                continue
            papers = result.data.get("papers", []) if result.data else []
            for paper in papers:
                bkey = paper.get("bibtex_key", "")
                bibtex = paper.get("bibtex", "")
                if bkey and bibtex and bkey not in seen_keys:
                    seen_keys.add(bkey)
                    discovered.append(
                        {
                            "ref_id": bkey,
                            "bibtex": bibtex,
                            "title": paper.get("title", ""),
                            "year": paper.get("year"),
                            "abstract": paper.get("abstract", ""),
                            "venue": paper.get("venue", ""),
                            "citation_count": paper.get("citation_count"),
                            "source": "landscape_discovery",
                            "validation": {
                                "status": "unvetted",
                                "exportable": False,
                                "reason": "Landscape search result; available for planning context only.",
                                "provenance": "landscape_discovery",
                                "support_tags": [],
                            },
                        }
                    )
        except Exception as exc:
            logger.warning("planner.landscape_search_error query='%s': %s", query[:80], exc)

    logger.info("planner.landscape_reference_discovery count=%d", len(discovered))
    return discovered


async def discover_utility_references(
    *,
    plan,
    existing_ref_keys: List[str],
    paper_search_config: Optional[Dict[str, Any]],
    logger,
    triggers: Optional[List[tuple[str, str]]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    cfg = paper_search_config or {}
    tool = _build_search_tool(cfg)
    per_round = max(2, int(cfg.get("search_results_per_round", 5)))
    delay_sec = max(0.5, float(cfg.get("planner_inter_round_delay_sec", 1.5)))

    out: Dict[str, List[Dict[str, Any]]] = {}
    seen_keys = set(existing_ref_keys)
    search_count = 0
    max_utility_searches = int(cfg.get("planner_max_utility_searches", 12))

    for section in plan.sections:
        if section.section_type in ("abstract", "conclusion"):
            continue
        blobs: List[str] = []
        try:
            blobs.extend(section.get_key_points())
        except Exception:
            pass
        for para in getattr(section, "paragraphs", []) or []:
            blobs.append(getattr(para, "key_point", "") or "")
            blobs.extend(getattr(para, "supporting_points", []) or [])
        blob = " ".join(blobs).lower()

        for needle, query in (triggers or UTILITY_LITERATURE_TRIGGERS):
            if search_count >= max_utility_searches:
                break
            if needle not in blob:
                continue
            if search_count > 0:
                await asyncio.sleep(delay_sec)
            search_count += 1
            try:
                result = await tool.execute(query=query, max_results=per_round)
                if not result.success:
                    continue
                papers = result.data.get("papers", []) if result.data else []
                for paper in papers:
                    bkey = paper.get("bibtex_key", "")
                    bibtex = paper.get("bibtex", "")
                    if not bkey or not bibtex or bkey in seen_keys:
                        continue
                    seen_keys.add(bkey)
                    out.setdefault(section.section_type, []).append(
                        {
                            "ref_id": bkey,
                            "bibtex": bibtex,
                            "title": paper.get("title", ""),
                            "year": paper.get("year"),
                            "abstract": paper.get("abstract", ""),
                            "venue": paper.get("venue", ""),
                            "citation_count": paper.get("citation_count"),
                            "source": "utility_discovery",
                            "validation": {
                                "status": "unvetted",
                                "exportable": False,
                                "reason": "Utility discovery result; requires planner relevance validation before citation.",
                                "provenance": "utility_discovery",
                                "support_tags": [section.section_type],
                            },
                        }
                    )
                    break
            except Exception as exc:
                logger.warning("planner.utility_search_error query='%s': %s", query[:60], exc)

    total_found = sum(len(values) for values in out.values())
    if total_found:
        logger.info("planner.utility_reference_discovery total=%d", total_found)
    return out


async def discover_references(
    *,
    plan,
    existing_ref_keys: List[str],
    paper_search_config: Optional[Dict[str, Any]],
    logger,
    generate_search_queries_fn,
    estimate_total_citations_fn,
    distribute_citations_topdown_fn,
    filter_papers_by_relevance_fn,
) -> Dict[str, List[Dict[str, Any]]]:
    cfg = paper_search_config or {}
    tool = _build_search_tool(cfg)

    results_per_round = max(1, int(cfg.get("search_results_per_round", 5)))
    max_queries_per_section = max(1, int(cfg.get("planner_max_queries_per_section", 5)))
    inter_round_delay = cfg.get("planner_inter_round_delay_sec", 1.5)
    min_target_papers = cfg.get("planner_min_target_papers_per_section", 3)
    require_abstract_for_citation = bool(
        cfg.get("planner_require_abstract_for_citation", True)
    )

    section_queries: Dict[str, List[str]] = {}
    section_targets: Dict[str, int] = {}

    body_sections = [
        sp for sp in plan.sections
        if sp.section_type not in ("abstract", "conclusion")
    ]

    strategy = plan.citation_strategy if isinstance(plan.citation_strategy, dict) else {}
    global_total = int(strategy.get("total_target", 0) or 0)
    section_allocation = strategy.get("section_allocation")

    if global_total <= 0:
        total_paras = sum(len(sp.paragraphs) for sp in body_sections)
        global_total = estimate_total_citations_fn(
            style_guide=cfg.get("style_guide"),
            n_body_sections=len(body_sections),
            total_paragraphs=total_paras,
        )
        section_allocation = None
        logger.info(
            "planner.citation_strategy fallback: estimated total_target=%d (venue=%s, body_sections=%d, paragraphs=%d)",
            global_total,
            cfg.get("style_guide", "unknown"),
            len(body_sections),
            total_paras,
        )
    else:
        logger.info("planner.citation_strategy from_planner: total_target=%d", global_total)

    topdown_targets = distribute_citations_topdown_fn(
        total_target=global_total,
        body_sections=body_sections,
        section_allocation=section_allocation,
    )

    for section in plan.sections:
        if section.section_type in ("abstract", "conclusion"):
            continue
        key_points = section.get_key_points()
        if not key_points:
            continue

        queries = await generate_search_queries_fn(
            section.section_type,
            key_points,
            existing_ref_keys,
            plan.title,
        )
        concept_anchors = section.get_key_points()[:6]
        gated_queries = [
            query
            for query in (queries or [])
            if _passes_query_quality_gate(query, plan.title, concept_anchors)
        ]
        planner_budget = section.citation_budget if isinstance(section.citation_budget, dict) else {}
        planner_target = planner_budget.get("target_refs")
        if planner_target is not None:
            try:
                section_targets[section.section_type] = max(1, int(planner_target))
            except Exception:
                section_targets[section.section_type] = topdown_targets.get(
                    section.section_type,
                    min_target_papers,
                )
        else:
            section_targets[section.section_type] = topdown_targets.get(
                section.section_type,
                min_target_papers,
            )
        target_for_query_count = section_targets.get(section.section_type, min_target_papers)
        dynamic_max_queries = max(
            max_queries_per_section,
            min(10, math.ceil(max(1, target_for_query_count) / max(1, results_per_round))),
        )
        fallback_queries = _build_section_fallback_queries(
            section_type=section.section_type,
            key_points=key_points,
            title=plan.title,
            max_queries=dynamic_max_queries,
        )
        combined_queries = list(dict.fromkeys(gated_queries + fallback_queries))
        if not combined_queries:
            logger.info("planner.search_queries_rejected section=%s", section.section_type)
            continue
        section_queries[section.section_type] = combined_queries[:dynamic_max_queries]

    discovered: Dict[str, List[Dict[str, Any]]] = {}

    for section_type, queries in section_queries.items():
        section_papers: List[Dict[str, Any]] = []
        section_seen_keys: set[str] = set()
        target_count = section_targets.get(section_type, 3)
        per_query_results = max(
            results_per_round,
            min(10, math.ceil(max(1, target_count * 2) / max(1, len(queries)))),
        )
        round_num = 0

        while round_num < len(queries):
            query = queries[round_num]
            if round_num > 0:
                jitter = random.uniform(0, 0.4)
                await asyncio.sleep(max(0.0, inter_round_delay + jitter))
            try:
                result = await tool.execute(query=query, max_results=per_query_results)
                if not result.success:
                    round_num += 1
                    continue
                papers = result.data.get("papers", []) if result.data else []
                for paper in papers:
                    bkey = paper.get("bibtex_key", "")
                    bibtex = paper.get("bibtex", "")
                    if bkey and bibtex and bkey not in section_seen_keys:
                        section_seen_keys.add(bkey)
                        section_papers.append(
                            {
                                "ref_id": bkey,
                                "bibtex": bibtex,
                                "title": paper.get("title", ""),
                                "year": paper.get("year"),
                                "abstract": paper.get("abstract", ""),
                                "venue": paper.get("venue", ""),
                                "citation_count": paper.get("citation_count"),
                            }
                        )
                logger.info(
                    "planner.search_round section=%s round=%d query='%s' found=%d total=%d",
                    section_type,
                    round_num,
                    query[:50],
                    len(papers),
                    len(section_papers),
                )
            except Exception as exc:
                logger.warning("planner.search_error query='%s': %s", query, exc)

            round_num += 1

        if section_papers:
            raw_count = len(section_papers)
            section_key_points = []
            for section in plan.sections:
                if section.section_type == section_type:
                    section_key_points = section.get_key_points()
                    break

            filtered_papers = await filter_papers_by_relevance_fn(
                papers=section_papers,
                section_type=section_type,
                key_points=section_key_points,
                paper_title=plan.title,
            )
            filtered_count = len(filtered_papers)
            auditable_papers = [
                paper
                for paper in filtered_papers
                if not require_abstract_for_citation or _has_auditable_abstract(paper)
            ]
            if filtered_papers and not auditable_papers:
                logger.info(
                    "planner.discovered_refs_rejected_no_abstract section=%s count=%d",
                    section_type,
                    len(filtered_papers),
                )
            filtered_sorted = sorted(
                auditable_papers,
                key=lambda p: (
                    float(p.get("relevance_score") or 0.0),
                    int(p.get("citation_count") or 0),
                    int(p.get("year") or 0),
                ),
                reverse=True,
            )
            selected_papers = filtered_sorted[:target_count] if target_count > 0 else filtered_sorted

            if selected_papers:
                for paper in selected_papers:
                    paper["source"] = "planner_discovery"
                    paper["validation"] = {
                        "status": "vetted",
                        "exportable": True,
                        "reason": (
                            f"Selected by planner relevance filter for {section_type}; "
                            f"score={paper.get('relevance_score', 'unknown')}."
                        ),
                        "provenance": "planner_discovery.relevance_filter",
                        "support_tags": [section_type],
                    }
                discovered[section_type] = selected_papers
                logger.info(
                    "planner.discovered_refs section=%s target=%d raw=%d filtered=%d selected=%d",
                    section_type,
                    target_count,
                    raw_count,
                    filtered_count,
                    len(selected_papers),
                )

    total = sum(len(values) for values in discovered.values())
    logger.info("planner.reference_discovery_complete total=%d", total)
    return discovered


def assign_references(
    *,
    plan,
    discovered: Dict[str, List[Dict[str, Any]]],
    core_ref_keys: List[str],
    paper_search_config: Optional[Dict[str, Any]],
    research_context: Optional[Dict[str, Any]],
    logger,
    estimate_total_citations_fn,
    distribute_citations_topdown_fn,
    rank_references_for_section_fn,
    infer_section_citation_budget_fn,
) -> None:
    cfg = paper_search_config or {}
    budget_enabled = cfg.get("citation_budget_enabled", True)
    soft_cap = cfg.get("citation_budget_soft_cap", True)
    reserve_size = max(1, int(cfg.get("citation_budget_reserve_size", 4)))

    no_cite_sections = {"abstract", "conclusion"}
    body_sections = [
        sp for sp in plan.sections
        if sp.section_type not in no_cite_sections
    ]
    strategy = plan.citation_strategy if isinstance(plan.citation_strategy, dict) else {}
    global_total = int(strategy.get("total_target", 0) or 0)
    section_allocation = strategy.get("section_allocation")

    if global_total <= 0:
        total_paras = sum(len(sp.paragraphs) for sp in body_sections)
        global_total = estimate_total_citations_fn(
            style_guide=cfg.get("style_guide"),
            n_body_sections=len(body_sections),
            total_paragraphs=total_paras,
        )
        section_allocation = None

    topdown_targets = distribute_citations_topdown_fn(
        total_target=global_total,
        body_sections=body_sections,
        section_allocation=section_allocation,
    )

    for section in plan.sections:
        if section.section_type in no_cite_sections:
            section.assigned_refs = []
            section.budget_selected_refs = []
            section.budget_reserve_refs = []
            section.budget_must_use_refs = []
            section.citation_budget = {
                "enabled": budget_enabled,
                "min_refs": 0,
                "target_refs": 0,
                "max_refs": 0,
                "candidate_count": 0,
                "selected_count": 0,
                "soft_cap": soft_cap,
            }
            continue

        discovered_for_section = [
            paper
            for paper in discovered.get(section.section_type, [])
            if (paper.get("validation") or {}).get("status") == "vetted"
            and (paper.get("validation") or {}).get("exportable") is True
        ]
        discovered_ranked = rank_references_for_section_fn(discovered_for_section)
        planner_hint_refs = [ref for ref in section.get_all_references() if ref]
        claim_refs = claim_matrix_refs_for_section(research_context, section.section_type)
        budget = infer_section_citation_budget_fn(
            section_type=section.section_type,
            paragraph_count=len(section.paragraphs),
            candidate_refs=discovered_ranked,
            planner_hint_refs=planner_hint_refs,
            core_ref_keys=core_ref_keys,
            planner_budget=section.citation_budget if isinstance(section.citation_budget, dict) else {},
            topdown_target=topdown_targets.get(section.section_type),
            claim_matrix_refs=claim_refs,
        )

        if not budget_enabled:
            refs: List[str] = []
            for ref_id in claim_refs:
                if ref_id not in refs:
                    refs.append(ref_id)
            for ref_id in core_ref_keys:
                if ref_id not in refs:
                    refs.append(ref_id)
            for paper in discovered_ranked:
                ref_id = paper.get("ref_id", "")
                if ref_id and ref_id not in refs:
                    refs.append(ref_id)
            section.assigned_refs = refs
            section.budget_selected_refs = refs
            section.budget_reserve_refs = []
            section.budget_must_use_refs = planner_hint_refs[:3]
            budget["enabled"] = False
            budget["selected_count"] = len(refs)
            section.citation_budget = budget
            continue

        selected_refs = list(budget.get("selected_refs", []))
        reserve_refs = list(budget.get("reserve_refs", []))
        must_use_refs = list(budget.get("must_use_refs", []))

        if not selected_refs:
            fallback = [key for key in planner_hint_refs if key in core_ref_keys]
            selected_refs = fallback[: max(1, budget.get("target_refs", 1))]
        section.assigned_refs = selected_refs
        section.budget_selected_refs = selected_refs
        section.budget_reserve_refs = reserve_refs[:reserve_size]
        section.budget_must_use_refs = must_use_refs
        budget["enabled"] = True
        budget["selected_count"] = len(selected_refs)
        budget["soft_cap"] = soft_cap
        section.citation_budget = budget

    assigned_counts = {
        section.section_type: len(section.assigned_refs)
        for section in plan.sections
        if section.assigned_refs
    }
    logger.info("planner.assign_references result=%s", assigned_counts)
