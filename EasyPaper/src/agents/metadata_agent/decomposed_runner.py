"""
Core decomposed section-generation runner for MetaDataAgent.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .progress import Phase


async def run_decomposed_section_generation(
    *,
    section_type: str,
    section_plan,
    writer_valid_keys: List[str],
    section_title_str: str,
    figures,
    evidence_dag,
    memory,
    emitter,
    writer,
    ensure_paragraph_figure_usages_fn,
    build_subsection_maps_fn,
    prepare_paragraph_generation_inputs_fn,
    build_assigned_refs_for_prompt_fn,
    compile_core_prompt_fn,
    compile_citation_prompt_fn,
    apply_citation_edits_fn,
    inject_float_refs_fn,
    run_local_mini_review_fn,
    handle_local_review_result_fn,
    verify_claim_and_emit_fn,
    record_claim_verification_failure_fn,
    run_template_fallback_fn,
    claim_verifier_cls,
    max_claim_retries: int,
    template_fallback_enabled: bool,
    paragraph_template_cls,
    build_template_fill_prompt_fn,
) -> str:
    verifier = claim_verifier_cls()
    paragraph_outputs: List[str] = []
    section_context = ""
    figure_map = {
        fig.id: fig for fig in (figures or [])
        if getattr(fig, "id", "")
    }
    placement_map = {
        placement.figure_id: placement
        for placement in (section_plan.figures or [])
        if getattr(placement, "figure_id", "")
    }
    ensure_paragraph_figure_usages_fn(
        section_type=section_type,
        section_plan=section_plan,
        figure_map=figure_map,
        placement_map=placement_map,
    )
    all_paras = section_plan._all_paragraphs()
    total_paras = len(all_paras)
    verify_stats = {"passed": 0, "retried": 0, "degraded": 0, "skipped": 0}

    para_subsection_title, subsection_first_para = build_subsection_maps_fn(section_plan)

    for pidx, para in enumerate(all_paras):
        if pidx in subsection_first_para:
            subsection_title = subsection_first_para[pidx]
            paragraph_outputs.append(f"\\subsection{{{subsection_title}}}")

        paragraph_inputs = prepare_paragraph_generation_inputs_fn(
            para=para,
            evidence_dag=evidence_dag,
            writer_valid_keys=writer_valid_keys,
            section_type=section_type,
        )
        has_claim = bool(paragraph_inputs["has_claim"])
        current_subsection_title = para_subsection_title.get(pidx, "")

        if emitter is not None:
            await emitter.paragraph_start(
                section_type=section_type,
                paragraph_index=pidx,
                claim_id=para.claim_id or "",
                total_paragraphs=total_paras,
                phase=Phase.BODY_SECTIONS,
            )

        evidence_snippets = paragraph_inputs["evidence_snippets"]
        evidence_snippet_map = paragraph_inputs["evidence_snippet_map"]
        para_valid_refs = paragraph_inputs["para_valid_refs"]
        valid_keys_set = paragraph_inputs["valid_keys_set"]
        latex = ""
        verification_feedback = ""

        figs_to_ref = paragraph_inputs["figs_to_ref"]
        tables_to_ref = paragraph_inputs["tables_to_ref"]
        requires_figure_ref = bool(paragraph_inputs["requires_figure_ref"])
        max_attempts = max_claim_retries if (has_claim or requires_figure_ref) else 1

        for attempt in range(max_attempts):
            core_prompt = compile_core_prompt_fn(
                paragraph_plan=para,
                section_type=section_type,
                section_context=section_context,
                evidence_snippets=evidence_snippets if has_claim else None,
                section_title=section_title_str,
                paragraph_index=pidx,
                total_paragraphs=total_paras,
                subsection_title=current_subsection_title,
            )
            if attempt > 0 and verification_feedback:
                core_prompt += f"\n\n### Revision Guidance\n{verification_feedback}"

            core_result = await writer.generate_core_content(
                core_prompt=core_prompt,
                section_type=section_type,
                paragraph_index=pidx,
            )
            raw_latex = core_result.raw_latex

            assigned_refs_for_prompt = build_assigned_refs_for_prompt_fn(para_valid_refs)
            cite_prompt = compile_citation_prompt_fn(
                raw_latex=raw_latex,
                assigned_refs=assigned_refs_for_prompt,
                section_type=section_type,
            )
            cite_result = await writer.inject_citations(
                citation_prompt=cite_prompt,
                valid_refs=para_valid_refs,
            )
            latex = apply_citation_edits_fn(
                raw_latex,
                cite_result.actions,
                valid_keys=valid_keys_set,
            )

            latex = inject_float_refs_fn(latex, figs_to_ref, tables_to_ref)
            local_review = await run_local_mini_review_fn(
                section_type=section_type,
                paragraph_index=pidx,
                paragraph_plan=para,
                raw_latex=raw_latex,
                final_latex=latex,
                figs_to_ref=figs_to_ref,
                tables_to_ref=tables_to_ref,
                attempt=attempt,
                max_attempts=max_attempts,
                memory=memory,
            )
            latex = local_review.get("latex", latex)
            local_status, next_feedback = handle_local_review_result_fn(
                local_review=local_review,
                verify_stats=verify_stats,
                paragraph_index=pidx,
                attempt=attempt,
            )
            if local_status == "retry_required":
                verification_feedback = next_feedback
                continue
            if local_status == "escalate":
                break

            if not has_claim:
                verify_stats["passed"] += 1
                break

            vr = await verify_claim_and_emit_fn(
                verifier=verifier,
                latex=latex,
                para=para,
                evidence_dag=evidence_dag,
                valid_keys_set=valid_keys_set,
                emitter=emitter,
                section_type=section_type,
                paragraph_index=pidx,
                max_attempts=max_attempts,
                attempt=attempt,
            )

            if vr.passed:
                verify_stats["passed"] += 1
                break

            verification_feedback = record_claim_verification_failure_fn(
                verify_stats=verify_stats,
                paragraph_index=pidx,
                attempt=attempt,
                verification_result=vr,
            )
        else:
            if has_claim and template_fallback_enabled and para.paragraph_template:
                try:
                    latex = await run_template_fallback_fn(
                        para=para,
                        evidence_snippet_map=evidence_snippet_map,
                        para_valid_refs=para_valid_refs,
                        section_type=section_type,
                        paragraph_index=pidx,
                        writer=writer,
                        paragraph_template_cls=paragraph_template_cls,
                        build_template_fill_prompt_fn=build_template_fill_prompt_fn,
                    ) or latex
                    verify_stats["degraded"] += 1
                    print(
                        f"[MetaDataAgent] Paragraph {pidx} degraded to template-slot filling"
                    )
                except Exception as tmpl_err:
                    print(
                        f"[MetaDataAgent] Template fallback failed for paragraph {pidx}: {tmpl_err}"
                    )

        wc = len(latex.split()) if latex else 0
        if emitter is not None:
            await emitter.paragraph_content(
                section_type=section_type,
                paragraph_index=pidx,
                claim_id=para.claim_id or "",
                content=latex,
                word_count=wc,
                phase=Phase.BODY_SECTIONS,
            )

        paragraph_outputs.append(latex)
        if latex:
            section_context += "\n\n" + latex

    content = "\n\n".join(p for p in paragraph_outputs if p)
    print(
        f"[MetaDataAgent] Decomposed generation for '{section_type}': "
        f"{verify_stats['passed']} passed, {verify_stats['retried']} retried, "
        f"{verify_stats['degraded']} degraded, {verify_stats['skipped']} skipped "
        f"(total {total_paras} paragraphs)"
    )
    return content
