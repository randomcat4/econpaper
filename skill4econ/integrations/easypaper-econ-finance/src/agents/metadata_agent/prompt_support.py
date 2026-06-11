"""
Prompt-support helpers for MetaDataAgent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..shared.code_context import CodeContextBuilder
from ...models.evidence_graph import EvidenceDAG


def get_active_skills(
    skill_registry,
    section_type: str,
    style_guide: str = None,
    active_skill_names=None,
):
    """
    Retrieve active writing skills from the skill registry.
    """
    if skill_registry is None or len(skill_registry) == 0:
        return None
    return skill_registry.get_writing_skills(
        section_type=section_type,
        venue=style_guide,
        active_names=active_skill_names,
    )


async def build_code_repository_context(
    metadata,
) -> Optional[Dict[str, Any]]:
    """
    Build code repository context for section-aware writing.
    """
    if not metadata.code_repository:
        return None

    builder = CodeContextBuilder(workspace_root=str(Path.cwd()))
    return await builder.build(
        code_repo=metadata.code_repository,
        paper_title=metadata.title,
    )


def retrieve_runtime_code_evidence(
    code_context: Optional[Dict[str, Any]],
    section_type: str,
    metadata,
    contributions: Optional[List[str]] = None,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Retrieve section-specific runtime evidence as fallback.
    """
    if not code_context:
        return []

    query_bundle: List[str] = []
    if section_type == "method":
        query_bundle = ["algorithm", "model", "module", "implementation", "forward", "pipeline"]
        query_bundle.extend(metadata.method.split()[:12])
    elif section_type == "experiment":
        query_bundle = ["train", "eval", "dataset", "metric", "configuration", "ablation"]
        query_bundle.extend(metadata.data.split()[:12])
        query_bundle.extend(metadata.experiments.split()[:12])
    elif section_type == "result":
        query_bundle = ["result", "analysis", "benchmark", "compare", "metric", "report"]
        query_bundle.extend(metadata.experiments.split()[:12])
    else:
        query_bundle = ["project", "workflow", "pipeline"]
        query_bundle.extend(metadata.idea_hypothesis.split()[:10])

    if contributions:
        query_bundle.extend(" ".join(contributions[:2]).split()[:8])

    builder = CodeContextBuilder(workspace_root=str(Path.cwd()))
    return builder.retrieve_for_section(
        context=code_context,
        section_type=section_type,
        query_bundle=query_bundle,
        top_k=top_k,
    )


def format_research_context_for_prompt(
    research_context: Optional[Dict[str, Any]],
    section_type: str,
    evidence_dag: Optional[EvidenceDAG] = None,
) -> str:
    """
    Format research context into a compact writer-consumable brief.
    """
    if not research_context and not evidence_dag:
        return ""

    lines: List[str] = ["## Research Context Brief"]

    if research_context:
        area = str(research_context.get("research_area", "")).strip()
        summary = str(research_context.get("summary", "")).strip()
        if area:
            lines.append(f"- Area: {area}")
        if summary:
            lines.append(f"- Landscape: {summary}")

        trends = research_context.get("research_trends", []) or []
        if trends:
            lines.append("- Trends:")
            for trend in trends[:3]:
                lines.append(f"  - {trend}")

        gaps = research_context.get("gaps", []) or []
        if gaps:
            lines.append("- Gaps to address:")
            for gap in gaps[:3]:
                lines.append(f"  - {gap}")

        key_papers = research_context.get("key_papers", []) or []
        if key_papers:
            lines.append("- Key papers and why they matter:")
            for kp in key_papers[:5]:
                title = kp.get("title", "")
                contribution = kp.get("contribution", "")
                if title:
                    lines.append(f"  - {title}: {contribution}")

        cra = research_context.get("core_ref_analysis")
        if isinstance(cra, dict):
            cra_items = cra.get("items") or []
            if cra_items:
                lines.append("- Core references (user anchors):")
                for it in cra_items[:6]:
                    if not isinstance(it, dict):
                        continue
                    rid = it.get("ref_id", "")
                    tit = it.get("title", "")
                    rel = str(it.get("relationship_to_ours", ""))[:220]
                    if tit or rid:
                        lines.append(f"  - [{rid}] {tit}: {rel}")
                pos = str(cra.get("positioning_statement", "")).strip()
                if pos:
                    lines.append(f"- Positioning vs core refs: {pos[:400]}")

        claim_matrix = research_context.get("claim_evidence_matrix", []) or []
        section_claims = [
            c for c in claim_matrix
            if c.get("section_type") in {section_type, "global", "", None}
        ]
        if section_claims and evidence_dag is None:
            lines.append("- Claim-evidence priorities:")
            for c in section_claims[:6]:
                claim = c.get("claim", "")
                refs = c.get("support_refs", []) or []
                priority = c.get("priority", "")
                reason = c.get("reason", "")
                ref_text = ", ".join(refs[:4]) if refs else "none"
                lines.append(
                    f"  - [{priority}] Claim: {claim} | Evidence refs: {ref_text} | Why: {reason}"
                )

        ranking = research_context.get("contribution_ranking", {}) or {}
        if ranking:
            lines.append("- Contribution ranking:")
            for band in ("P0", "P1", "P2"):
                items = ranking.get(band, []) or []
                if not items:
                    continue
                for item in items[:3]:
                    contribution = item.get("contribution", "")
                    why = item.get("why_it_matters", "")
                    sections = item.get("suggested_sections", []) or []
                    section_hint = ", ".join(sections[:3]) if sections else "n/a"
                    lines.append(
                        f"  - {band}: {contribution} | Why: {why} | Suggested sections: {section_hint}"
                    )

    if evidence_dag is not None:
        section_claims = evidence_dag.get_claims_for_section(section_type)
        if section_claims:
            lines.append("")
            lines.append("## Claim-Evidence Bindings (from Evidence DAG)")
            lines.append(
                "(Each claim MUST be supported ONLY by its bound evidence. "
                "Do NOT introduce unsupported claims.)"
            )
            for claim in section_claims[:10]:
                ev_nodes = evidence_dag.get_evidence_for_claim(claim.node_id)
                ev_desc_parts: List[str] = []
                for ev in ev_nodes[:5]:
                    node_type = str(getattr(ev, "node_type", "") or "").lower()
                    if node_type.endswith("figure") or node_type == "figure":
                        metadata = getattr(ev, "metadata", {}) or {}
                        owner_section = str(metadata.get("section", "") or "")
                        if owner_section and owner_section != section_type:
                            continue
                    label = f"{ev.node_id}({ev.node_type.value})"
                    if ev.source_path:
                        label += f"[{ev.source_path}]"
                    ev_desc_parts.append(label)
                ev_text = ", ".join(ev_desc_parts) if ev_desc_parts else "UNSUPPORTED"
                lines.append(
                    f"  - [{claim.priority}] {claim.node_id}: "
                    f"{claim.statement[:200]} "
                    f"| Bound evidence: {ev_text}"
                )

    if len(lines) <= 1:
        return ""
    return "\n".join(lines)
