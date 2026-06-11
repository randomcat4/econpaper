"""
Context-formatting helpers for PlannerAgent.
"""
from __future__ import annotations

from typing import Any, Optional

from .models import PaperPlan


def gather_plan_candidates(plan: PaperPlan, question: str) -> str:
    """
    Gather compact plan snippets via keyword matching.
    """
    keywords = [w.lower() for w in question.split() if len(w) > 2]
    hits: list[str] = []

    for sp in plan.sections:
        stype = sp.section_type
        guidance = sp.writing_guidance or ""
        para_texts = " ".join(getattr(p, "key_point", "") for p in (sp.paragraphs or []))
        fig_texts = " ".join(
            getattr(fp, "figure_id", "") + " " + getattr(fp, "purpose", "")
            for fp in (sp.figure_placements or [])
        )
        tbl_texts = " ".join(
            getattr(tp, "table_id", "") + " " + getattr(tp, "purpose", "")
            for tp in (sp.table_placements or [])
        )
        full = f"{stype} {guidance} {para_texts} {fig_texts} {tbl_texts}".lower()

        if not keywords or any(kw in full for kw in keywords):
            guidance_snippet = guidance.split(".")[0] if guidance else ""
            n_paras = len(sp.paragraphs or [])
            kp_list = ", ".join(
                getattr(p, "key_point", "")[:60]
                for p in (sp.paragraphs or [])[:4]
            )
            line = f"- {stype}: {n_paras} paragraphs"
            est = sp.get_estimated_words() if hasattr(sp, "get_estimated_words") else 0
            if est:
                line += f", ~{est} words"
            if guidance_snippet:
                line += f', guidance: "{guidance_snippet}"'
            if kp_list:
                line += f", key points: [{kp_list}]"
            for fp in (sp.figure_placements or []):
                fid = getattr(fp, "figure_id", "")
                purpose = getattr(fp, "purpose", "")[:60]
                line += f", fig {fid}: {purpose}"
            for tp in (sp.table_placements or []):
                tid = getattr(tp, "table_id", "")
                purpose = getattr(tp, "purpose", "")[:60]
                line += f", tbl {tid}: {purpose}"
            hits.append(line)

    return "\n".join(hits) if hits else ""


def format_research_context_for_planning(
    research_context: Optional[dict[str, Any]],
) -> str:
    """
    Format compact research context for planning input.
    """
    if not research_context:
        return "Not available."

    lines: list[str] = []
    area = str(research_context.get("research_area", "")).strip()
    summary = str(research_context.get("summary", "")).strip()
    if area:
        lines.append(f"- Research area: {area}")
    if summary:
        lines.append(f"- Landscape summary: {summary}")

    raw_trends = research_context.get("research_trends", []) or []
    trends = list(raw_trends) if isinstance(raw_trends, (list, tuple)) else []
    if trends:
        lines.append("- Key trends:")
        for trend in trends[:3]:
            lines.append(f"  - {trend}")

    raw_gaps = research_context.get("gaps", []) or []
    gaps = list(raw_gaps) if isinstance(raw_gaps, (list, tuple)) else []
    if gaps:
        lines.append("- Key gaps/opportunities:")
        for gap in gaps[:3]:
            lines.append(f"  - {gap}")

    ranking = research_context.get("contribution_ranking", {}) or {}
    if isinstance(ranking, dict):
        lines.append("- Contribution ranking hints:")
        for band in ("P0", "P1", "P2"):
            raw_items = ranking.get(band, []) or []
            items = list(raw_items) if isinstance(raw_items, (list, tuple)) else []
            if not items:
                continue
            top_text = ", ".join(
                [str(x.get("contribution", "")).strip() for x in items[:3] if isinstance(x, dict)]
            )
            if top_text:
                lines.append(f"  - {band}: {top_text}")

    return "\n".join(lines) if lines else "Not available."


def format_code_assets_for_planning(
    code_context: Optional[dict[str, Any]],
    code_writing_assets: Optional[dict[str, Any]],
) -> str:
    """
    Format compact code-driven writing assets for planner decisions.
    """
    assets = code_writing_assets or {}
    if not assets and code_context:
        assets = code_context.get("writing_assets", {}) or {}

    section_packs = {}
    if code_context:
        section_packs = code_context.get("section_asset_packs", {}) or {}
    evidence_graph = (code_context or {}).get("code_evidence_graph", []) or []

    if not assets and not section_packs and not evidence_graph:
        return "Not available."

    lines: list[str] = [f"- Evidence nodes extracted: {len(evidence_graph)}"]
    planner_brief = str(assets.get("planner_brief", "")).strip() if isinstance(assets, dict) else ""
    if planner_brief:
        lines.append("- Planner brief:")
        for chunk in planner_brief.splitlines()[:10]:
            lines.append(f"  {chunk}")
    for key, label in (
        ("method_pipeline", "Method assets"),
        ("experiment_protocol", "Experiment assets"),
        ("result_readouts", "Result assets"),
        ("risk_limitations", "Risk assets"),
    ):
        rows = assets.get(key, []) or []
        if not rows:
            continue
        lines.append(f"- {label}:")
        for row in rows[:4]:
            title = str(row.get("title", "")).strip()
            if title:
                lines.append(f"  - {title}")
    for sec in ("introduction", "method", "experiment", "result", "discussion"):
        pack = section_packs.get(sec, {}) or {}
        evidence_ids = [str(x).strip() for x in (pack.get("evidence_ids", []) or []) if str(x).strip()]
        if evidence_ids:
            lines.append(f"- Suggested evidence IDs for {sec}: {', '.join(evidence_ids[:6])}")
        guardrails = [str(x).strip() for x in (pack.get("claim_guardrails", []) or []) if str(x).strip()]
        if guardrails:
            lines.append(f"- Claim guardrails for {sec}:")
            for guardrail in guardrails[:2]:
                lines.append(f"  - {guardrail}")
    return "\n".join(lines) if lines else "Not available."
