"""
Helpers for decomposed paragraph generation in MetaDataAgent.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def _is_visible_evidence_for_section(enode, section_type: str) -> bool:
    """Hide figure evidence outside its assigned owner section."""
    node_type = str(getattr(enode, "node_type", "") or "").lower()
    if node_type.endswith("figure") or node_type == "figure":
        metadata = getattr(enode, "metadata", {}) or {}
        owner_section = str(metadata.get("section", "") or "")
        return bool(owner_section and owner_section == section_type)
    return True


def build_subsection_maps(section_plan) -> Tuple[Dict[int, Optional[str]], Dict[int, str]]:
    para_subsection_title: Dict[int, Optional[str]] = {}
    subsection_first_para: Dict[int, str] = {}
    subsections = getattr(section_plan, "subsections", None) or []
    if not subsections:
        return para_subsection_title, subsection_first_para
    if len(subsections) == 1:
        return para_subsection_title, subsection_first_para

    pidx_offset = len(section_plan.paragraphs)
    for sub in subsections:
        sub_title = getattr(sub, "title", "")
        sub_paras = getattr(sub, "paragraphs", [])
        if sub_paras and sub_title:
            subsection_first_para[pidx_offset] = sub_title
        for _sp in sub_paras:
            para_subsection_title[pidx_offset] = sub_title
            pidx_offset += 1
    return para_subsection_title, subsection_first_para


def prepare_paragraph_generation_inputs(
    *,
    para,
    evidence_dag,
    writer_valid_keys: List[str],
    section_type: str = "",
) -> Dict[str, object]:
    has_claim = bool(para.claim_id and evidence_dag is not None)
    evidence_snippets: List[str] = []
    evidence_snippet_map: Dict[str, str] = {}
    para_valid_refs: List[str] = list(writer_valid_keys)
    writer_valid_set = set(writer_valid_keys)

    if has_claim:
        evidence_nodes = evidence_dag.get_evidence_for_claim(para.claim_id)
        for enode in evidence_nodes:
            if not _is_visible_evidence_for_section(enode, section_type):
                continue
            snippet = enode.content or enode.source_path or enode.node_id
            evidence_snippets.append(snippet)
            evidence_snippet_map[enode.node_id] = snippet
            if (
                enode.source_path
                and enode.source_path in writer_valid_set
                and enode.source_path not in para_valid_refs
            ):
                para_valid_refs.append(enode.source_path)

    for ref_key in para.references_to_cite:
        if ref_key in writer_valid_set and ref_key not in para_valid_refs:
            para_valid_refs.append(ref_key)

    figs_to_ref = getattr(para, "figures_to_reference", []) or []
    tables_to_ref = getattr(para, "tables_to_reference", []) or []
    requires_figure_ref = any(
        getattr(usage, "must_appear", False)
        for usage in (getattr(para, "figure_usages", []) or [])
    )

    return {
        "has_claim": has_claim,
        "evidence_snippets": evidence_snippets,
        "evidence_snippet_map": evidence_snippet_map,
        "para_valid_refs": para_valid_refs,
        "valid_keys_set": set(para_valid_refs),
        "figs_to_ref": figs_to_ref,
        "tables_to_ref": tables_to_ref,
        "requires_figure_ref": requires_figure_ref,
    }


def build_assigned_refs_for_prompt(para_valid_refs: List[str]) -> List[Dict[str, str]]:
    return [{"id": ref_key, "title": "", "abstract": ""} for ref_key in para_valid_refs]


async def run_template_fallback(
    *,
    para,
    evidence_snippet_map: Dict[str, str],
    para_valid_refs: List[str],
    section_type: str,
    paragraph_index: int,
    writer,
    paragraph_template_cls,
    build_template_fill_prompt_fn,
) -> str:
    tmpl_data = para.paragraph_template
    if isinstance(tmpl_data, dict):
        tmpl = paragraph_template_cls(**tmpl_data)
    else:
        tmpl = tmpl_data

    tmpl_prompt = build_template_fill_prompt_fn(
        template=tmpl,
        evidence_snippets=evidence_snippet_map,
        valid_refs=para_valid_refs,
    )
    tmpl_result = await writer.generate_from_template(
        template_prompt=tmpl_prompt,
        section_type=section_type,
        valid_refs=para_valid_refs,
        paragraph_index=paragraph_index,
    )
    if hasattr(tmpl_result, "latex_content"):
        return tmpl_result.latex_content
    return tmpl_result.get("latex_content", "")
