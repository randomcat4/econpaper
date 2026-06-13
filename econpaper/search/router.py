"""Tier routing (design §5): which search tier fits which scenario.

Default tier is always L1. Upgrading costs money and time, so it is an
explicit user choice — the router only recommends, it never auto-upgrades.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import SEARCH_TIERS_VERSION

_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "verify_existing_refs",
        "match": ["verify", "核验", "补元数据", "refs.bib", "已有文献库", "metadata"],
        "tier": "l2_verify",
        "rationale": "作者已有 refs.bib，只需核验+补元数据：L2 核验子集是最便宜路径。",
        "command": "econpaper search verify --refs refs.bib --out <dir>",
    },
    {
        "id": "chinese_policy_budget_sensitive",
        "match": ["中文", "政策评估", "政策背景", "知网", "cnki", "预算敏感", "国内"],
        "tier": "l1",
        "rationale": "国内政策评估需要中文文献+政策背景，开放 API 覆盖弱：走 L1 处方（中文 query 卡加重）。",
        "command": "econpaper search prescribe --topic-spec <spec> --out <dir>",
    },
    {
        "id": "english_wp_citation_graph",
        "match": ["working paper", "引文图谱", "citation graph", "英文定位", "nber", "ssrn"],
        "tier": "l2",
        "rationale": "英文 working paper 定位与引文图谱：L2 开放 API 聚合即可。",
        "command": "econpaper search open --prescription <search_prescription.json> --out <dir>",
    },
    {
        "id": "systematic_pre_submission",
        "match": ["投稿前", "系统性", "审稿人", "漏了", "systematic", "reviewer", "全量"],
        "tier": "l3",
        "rationale": "投稿前系统性定位 / 审稿人质疑漏文献：需要 L3 双语全量与覆盖审计。",
        "command": "econpaper search deep --prescription <search_prescription.json> --out <dir> --confirm-plan",
    },
    {
        "id": "exploratory_scoping",
        "match": ["开题", "不确定方向", "摸底", "exploratory", "scoping"],
        "tier": "l3_plan_only",
        "rationale": "开题摸底：跑 L3 的『计划+第一轮』截断模式（澄清+处方+一轮扇出，不进深读循环）。",
        "command": "econpaper search deep --prescription <search_prescription.json> --out <dir> --max-rounds 1 --confirm-plan",
    },
]

_DEFAULT = {
    "id": "default",
    "tier": "l1",
    "rationale": "默认档位 = L1 处方驱动检索；升档涉及钱和时间，永远是显式选择。",
    "command": "econpaper search prescribe --topic-spec <spec> --out <dir>",
}


@dataclass
class RouteResult:
    scenario_text: str
    matched_scenario: str
    tier: str
    rationale: str
    command: str

    @property
    def has_hard_blocks(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "scenario_text": self.scenario_text,
            "matched_scenario": self.matched_scenario,
            "tier": self.tier,
            "rationale": self.rationale,
            "command": self.command,
            "note": "升档永远是显式选择，本路由只推荐不自动升档。",
        }


def recommend_tier(scenario_text: str) -> RouteResult:
    lowered = (scenario_text or "").lower()
    best = _DEFAULT
    best_score = 0
    for scenario in _SCENARIOS:
        score = sum(1 for keyword in scenario["match"] if keyword.lower() in lowered)
        if score > best_score:
            best, best_score = scenario, score
    return RouteResult(
        scenario_text=scenario_text,
        matched_scenario=best["id"],
        tier=best["tier"],
        rationale=best["rationale"],
        command=best["command"],
    )
