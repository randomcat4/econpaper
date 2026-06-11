"""
Canonical query policy for planner literature discovery.

The goal is not perfect retrieval.  The policy rejects obvious broad/title-like
queries and keeps all discovery entry points on the same precision-oriented
contract.
"""
from __future__ import annotations

import re
from typing import Iterable, List


QUERY_STOPWORDS = {
    "a", "an", "and", "are", "as", "based", "by", "for", "from", "in", "of",
    "on", "or", "the", "to", "with", "using", "multi", "paper", "study",
    "analysis", "toward", "towards", "this", "that", "into",
}

GENERIC_QUERY_TOKENS = {
    "ai", "agent", "agents", "artificial", "benchmark", "benchmarks",
    "evaluation", "language", "large", "learning", "literature", "llm",
    "llms", "machine", "model", "models", "review", "simulation",
    "simulations", "survey", "surveys",
}

KNOWN_DOMAIN_PHRASES = [
    "large language models",
    "llm agents",
    "simulated agents",
    "generative agents",
    "agent-based simulation",
    "self-bias",
    "self reference effect",
    "self-reference effect",
    "self enhancement",
    "self-enhancement",
    "implicit association test",
    "endowment effect",
    "machine psychology",
    "ai psychology",
    "cognitive bias",
    "psychometrics",
    "behavioral experiments",
    "human survey responses",
    "social simulation",
]


def normalize_query(query: str) -> str:
    return " ".join(str(query or "").split()).strip()


def query_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", (text or "").lower())
        if token not in QUERY_STOPWORDS
    }


def is_title_like_query(query: str, title: str) -> bool:
    normalized_query = normalize_query(query).lower()
    normalized_title = normalize_query(title).lower()
    if normalized_query and normalized_title and normalized_query == normalized_title:
        return True
    q_tokens = query_tokens(query)
    title_tokens = query_tokens(title)
    if not q_tokens or not title_tokens:
        return False
    if q_tokens == title_tokens:
        return True
    overlap = len(q_tokens & title_tokens) / max(1, len(q_tokens))
    return overlap >= 0.75 and len(q_tokens) >= 4


def extract_concept_anchors(*texts: str) -> List[str]:
    text = " ".join(t or "" for t in texts).lower()
    anchors = [phrase for phrase in KNOWN_DOMAIN_PHRASES if phrase in text]
    token_candidates = [
        token
        for token in query_tokens(text)
        if token not in GENERIC_QUERY_TOKENS and len(token) >= 4
    ]
    anchors.extend(token_candidates[:8])
    return list(dict.fromkeys(anchors))


def passes_query_quality_gate(
    query: str,
    *,
    title: str = "",
    concept_anchors: Iterable[str] = (),
) -> bool:
    query = normalize_query(query)
    if len(query) < 8 or len(query) > 180:
        return False
    tokens = query_tokens(query)
    if len(tokens) < 3 or len(tokens) > 14:
        return False
    if is_title_like_query(query, title):
        return False

    lowered = query.lower()
    anchors = [a for a in concept_anchors if str(a or "").strip()]
    anchor_hits = [anchor for anchor in anchors if str(anchor).lower() in lowered]
    anchor_token_hits = set()
    for anchor in anchors:
        anchor_token_hits.update(tokens & query_tokens(str(anchor)))

    if lowered in {"large language models", "llm agents", "social simulation"}:
        return False
    if tokens <= GENERIC_QUERY_TOKENS:
        return False
    if "literature review" in lowered and len(anchor_hits) + len(anchor_token_hits) < 2:
        return False

    non_generic = tokens - GENERIC_QUERY_TOKENS
    if not non_generic and not anchor_hits:
        return False
    return bool(anchor_hits or anchor_token_hits or len(non_generic) >= 2)


def build_seed_queries(
    *,
    title: str,
    idea_hypothesis: str,
    method: str,
    data: str,
    experiments: str,
    max_queries: int,
) -> List[str]:
    """
    Build seed queries without issuing raw-title searches.
    """
    anchors = extract_concept_anchors(title, idea_hypothesis, method, data, experiments)
    core = anchors[:6]
    templates: list[str] = []
    if core:
        for anchor in core[:4]:
            templates.extend(
                [
                    f"{anchor} psychological experiment simulation",
                    f"{anchor} human behavior benchmark",
                    f"{anchor} cognitive bias evaluation",
                ]
            )
    templates.extend(
        [
            "large language models simulate human survey responses social science",
            "LLM agents cognitive bias psychological experiments",
            "generative agents social simulation human behavior",
        ]
    )

    queries: List[str] = []
    for query in templates:
        if passes_query_quality_gate(query, title=title, concept_anchors=anchors):
            normalized = normalize_query(query)
            if normalized not in queries:
                queries.append(normalized)
        if len(queries) >= max_queries:
            break
    return queries
