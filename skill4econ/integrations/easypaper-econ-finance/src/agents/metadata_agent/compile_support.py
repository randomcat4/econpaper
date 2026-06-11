"""
Figure/table injection and compile-result helpers for MetaDataAgent.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import httpx

from .latex_helpers import extract_valid_citation_keys, validate_main_tex_structure

if TYPE_CHECKING:
    from ..planner_agent.models import PaperPlan
    from .models import FigureSpec, TableSpec


_SIMPLE_CAPTION_RE = re.compile(r"(\\caption(?:\[[^\]]*\])?\{)([^{}]*)(\})")


def normalize_latex_caption_prefixes(content: str) -> str:
    """
    Strip redundant Figure/Table numbering prefixes inside LaTeX captions.

    LaTeX generates "Figure N" / "Table N" automatically from ``\\caption``.
    Metadata and writer output may already include prefixes such as
    "Figure 1.", which would otherwise render as "Figure 1: Figure 1. ...".
    """
    if not content:
        return content

    from ..shared.table_converter import normalize_caption

    def _replace(match: re.Match[str]) -> str:
        normalized = normalize_caption(match.group(2))
        return f"{match.group(1)}{normalized}{match.group(3)}"

    return _SIMPLE_CAPTION_RE.sub(_replace, content)


def ensure_figures_defined(
    generated_sections: Dict[str, str],
    paper_plan: Optional["PaperPlan"],
    figures: Optional[List["FigureSpec"]],
    template_guide: Optional[Any] = None,
    column_format: Optional[str] = None,
) -> Dict[str, str]:
    if not paper_plan or not figures:
        return generated_sections

    figure_map = {fig.id: fig for fig in figures}
    assigned_figure_ids = {
        fig_id
        for section in paper_plan.sections
        for fig_id in (section.get_figure_ids_to_define() or [])
        if fig_id
    }

    if assigned_figure_ids:
        block_re = re.compile(
            r"\\begin\{figure\*?\}(?:\[[^\]]*\])?.*?\\end\{figure\*?\}",
            re.DOTALL,
        )
        label_re = re.compile(r"\\label\{([^}]+)\}")

        def _strip_assigned_blocks(content: str) -> str:
            def _replace(match: re.Match[str]) -> str:
                block = match.group(0)
                labels = set(label_re.findall(block))
                if labels & assigned_figure_ids:
                    return ""
                return block

            stripped = block_re.sub(_replace, content or "")
            return re.sub(r"\n{3,}", "\n\n", stripped).strip()

        for sec_type, content in list(generated_sections.items()):
            stripped = _strip_assigned_blocks(content)
            if stripped != content:
                generated_sections[sec_type] = stripped
                print(
                    f"[EnsureFigures] Stripped writer-defined assigned figure block(s) from '{sec_type}'"
                )

    def _split_rendered_blocks(content: str) -> List[str]:
        return [b for b in re.split(r"\n\s*\n", content) if b.strip()]

    def _paragraph_block_positions(blocks: List[str]) -> List[int]:
        positions: List[int] = []
        for idx, block in enumerate(blocks):
            stripped = block.strip()
            if stripped.startswith("\\subsection{"):
                continue
            if stripped.startswith("\\begin{figure"):
                continue
            positions.append(idx)
        return positions

    def _figure_ref_sentence(fig_id: str, fig: "FigureSpec") -> str:
        caption = re.sub(r"\s+", " ", getattr(fig, "caption", "") or "").strip()
        caption = normalize_latex_caption_prefixes(f"\\caption{{{caption}}}")
        caption = caption.removeprefix("\\caption{").removesuffix("}").strip()
        if caption:
            return f"Figure~\\ref{{{fig_id}}} summarizes {caption[0].lower() + caption[1:] if len(caption) > 1 else caption.lower()}."
        return f"Figure~\\ref{{{fig_id}}} summarizes the assigned visual evidence for this section."

    def _body_has_ref(content: str, fig_id: str) -> bool:
        stripped = re.sub(
            r'\\begin\{figure\*?\}(?:\[[^\]]*\])?.*?\\end\{figure\*?\}',
            '',
            content or "",
            flags=re.DOTALL,
        )
        return bool(re.search(rf'\\(?:ref|autoref|cref|Cref){{{re.escape(fig_id)}}}', stripped))

    def _payload(content: str, fig_id: str, fig: "FigureSpec", figure_latex: str) -> str:
        if _body_has_ref(content, fig_id):
            return figure_latex.strip()
        return f"{_figure_ref_sentence(fig_id, fig)}\n\n{figure_latex.strip()}"

    def _insert_after_block(blocks: List[str], block_idx: int, payload: str) -> str:
        updated = list(blocks)
        updated.insert(block_idx + 1, payload.strip())
        return "\n\n".join(updated)

    for section in paper_plan.sections:
        section_type = section.section_type
        figures_to_define = section.get_figure_ids_to_define()
        if not figures_to_define or section_type not in generated_sections:
            continue

        content = generated_sections[section_type]
        for fig_id in figures_to_define:
            fig = figure_map.get(fig_id)
            if not fig:
                continue

            print(f"[EnsureFigures] Injecting missing figure '{fig_id}' in '{section_type}'")
            fmt = str(column_format or getattr(template_guide, "column_format", None) or "single").lower()
            wide_allowed = fmt == "double"
            planned_wide_figures = {
                str(fid) for fid in (getattr(paper_plan, "wide_figures", []) or [])
            }
            is_planned_wide = fig_id in planned_wide_figures or bool(getattr(fig, "wide", False))
            env_name = "figure*" if is_planned_wide and wide_allowed else "figure"
            width = "0.92\\textwidth" if env_name == "figure*" else "0.82\\linewidth"
            caption = normalize_latex_caption_prefixes(f"\\caption{{{fig.caption}}}")
            caption = caption.removeprefix("\\caption{").removesuffix("}")
            figure_latex = f"""
\\begin{{{env_name}}}[tbp]
\\centering
\\includegraphics[width={width}]{{{fig_id}}}
\\caption{{{caption}}}\\label{{{fig_id}}}
\\end{{{env_name}}}
"""

            blocks = _split_rendered_blocks(content)
            para_positions = _paragraph_block_positions(blocks)
            anchor_para_idx: Optional[int] = None
            anchor_claim: str = ""
            all_paragraphs = section._all_paragraphs() if hasattr(section, "_all_paragraphs") else []
            for pidx, para in enumerate(all_paragraphs):
                usages = getattr(para, "figure_usages", []) or []
                for usage in usages:
                    if getattr(usage, "figure_id", "") != fig_id:
                        continue
                    if getattr(usage, "mode", "") == "define" or getattr(usage, "rhetorical_role", "") in {"introduce", "analyze"}:
                        anchor_para_idx = pidx
                        anchor_claim = getattr(usage, "supported_claim", "") or getattr(para, "key_point", "") or ""
                        break
                if anchor_para_idx is not None:
                    break

            inserted = False
            figure_payload = _payload(content, fig_id, fig, figure_latex)
            if anchor_para_idx is not None and anchor_para_idx < len(para_positions):
                block_idx = para_positions[anchor_para_idx]
                content = _insert_after_block(blocks, block_idx, figure_payload)
                inserted = True
            else:
                ref_pattern = re.compile(rf'\\(?:ref|autoref|cref|Cref){{{re.escape(fig_id)}}}')
                for para_pos in para_positions:
                    if ref_pattern.search(blocks[para_pos]):
                        content = _insert_after_block(blocks, para_pos, figure_payload)
                        inserted = True
                        break

            if not inserted and anchor_claim:
                claim_tokens = [w for w in re.findall(r"[A-Za-z0-9]+", anchor_claim.lower()) if len(w) > 4][:4]
                if claim_tokens:
                    for para_pos in para_positions:
                        block_lower = blocks[para_pos].lower()
                        if any(tok in block_lower for tok in claim_tokens):
                            content = _insert_after_block(blocks, para_pos, figure_payload)
                            inserted = True
                            break

            if not inserted:
                blocks.append(figure_payload)
                content = "\n\n".join(blocks)

            generated_sections[section_type] = content

    return generated_sections


def ensure_tables_defined(
    generated_sections: Dict[str, str],
    paper_plan: Optional["PaperPlan"],
    tables: Optional[List["TableSpec"]],
    converted_tables: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    from ..shared.table_converter import inject_tables, strip_writer_tables

    if not paper_plan or not tables:
        return generated_sections

    _converted = converted_tables or {}
    assigned_ids = {
        table_id
        for section in paper_plan.sections
        for table_id in (section.get_table_ids_to_define() or [])
    }
    print(f"[DirectInject] Starting: {len(_converted)} converted tables, sections={list(generated_sections.keys())}")

    if assigned_ids:
        for section_type, content in list(generated_sections.items()):
            stripped = strip_writer_tables(content, assigned_ids)
            if stripped != content:
                generated_sections[section_type] = stripped
                print(
                    f"[DirectInject] Stripped assigned Writer table(s) from '{section_type}'"
                )

    for section in paper_plan.sections:
        section_type = section.section_type
        if section_type not in generated_sections:
            continue
        tables_to_define = section.get_table_ids_to_define()
        if not tables_to_define:
            continue

        print(f"[DirectInject] Section '{section_type}' has tables_to_define={tables_to_define}")
        content = generated_sections[section_type]
        result = inject_tables(content, section, tables, _converted)
        if result != content:
            print(f"[DirectInject] Injected tables in '{section_type}' (content grew {len(content)}->{len(result)} chars)")
        generated_sections[section_type] = result

    return generated_sections


def save_compile_error_log(
    output_dir: Path,
    errors: List[str],
) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        error_path = output_dir / "compile_errors.json"
        error_path.write_text(
            json.dumps({"errors": errors}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def parse_typesetter_result(
    ts_state: Dict[str, Any],
    output_dir: Path,
) -> Tuple[Optional[str], Optional[str], List[str], Dict[str, List[str]]]:
    cr = ts_state.get("compilation_result")
    if cr is None:
        print("[MetaDataAgent] Typesetter returned no compilation_result")
        return None, None, ["Typesetter returned no compilation_result"], {}

    pdf_path = cr.pdf_path if hasattr(cr, "pdf_path") else cr.get("pdf_path")
    latex_path = cr.source_path if hasattr(cr, "source_path") else cr.get("source_path")
    errors = (cr.errors if hasattr(cr, "errors") else cr.get("errors", [])) or []
    section_errors = (cr.section_errors if hasattr(cr, "section_errors") else cr.get("section_errors", {})) or {}
    warnings = (cr.warnings if hasattr(cr, "warnings") else cr.get("warnings", [])) or []
    success = cr.success if hasattr(cr, "success") else cr.get("success", False)

    if success and pdf_path:
        print(f"[MetaDataAgent] PDF compiled successfully: {pdf_path}")
        if warnings:
            print(f"[MetaDataAgent] Compile warnings: {warnings[:5]}")
        if section_errors:
            print(f"[MetaDataAgent] Section errors (on success): {section_errors}")
        if latex_path:
            main_tex_path = Path(latex_path) / "main.tex"
            structure_errors = validate_main_tex_structure(main_tex_path)
            if structure_errors:
                print(f"[MetaDataAgent] main.tex structure validation failed: {structure_errors}")
                return None, None, structure_errors, section_errors
        return pdf_path, latex_path, [], section_errors

    print(f"[MetaDataAgent] PDF compilation failed: {errors}")
    if section_errors:
        print(f"[Typesetter] Section errors: {section_errors}")
    return None, None, errors or ["Typesetter compilation failed"], section_errors


def normalize_compile_sections(
    *,
    generated_sections: Dict[str, str],
    references: List[Dict[str, Any]],
    section_order: List[str],
    strip_code_path_references_fn,
    fix_latex_references_fn,
    normalize_float_placement_fn,
    validate_and_fix_citations_fn,
    deduplicate_figure_environments_fn,
) -> Dict[str, str]:
    from ..shared.label_registry import collect_all_labels, validate_and_fix_refs
    from .latex_helpers import normalize_narrative_section_shapes

    normalized_sections = dict(generated_sections)
    normalized_sections = normalize_narrative_section_shapes(normalized_sections)
    valid_citation_keys = extract_valid_citation_keys(references)
    total_invalid_removed = 0

    for section_type in list(normalized_sections.keys()):
        content = normalized_sections[section_type]
        content = fix_latex_references_fn(content)
        content = normalize_float_placement_fn(content)
        content = normalize_latex_caption_prefixes(content)
        fixed_content, invalid, _valid = validate_and_fix_citations_fn(
            content,
            valid_citation_keys,
            remove_invalid=True,
        )
        if invalid:
            print(
                f"[CompilePDF] Removed {len(invalid)} invalid citations from {section_type}: "
                f"{invalid[:3]}{'...' if len(invalid) > 3 else ''}"
            )
            total_invalid_removed += len(invalid)
        normalized_sections[section_type] = fixed_content

    valid_labels = collect_all_labels(normalized_sections)
    for section_type in list(normalized_sections.keys()):
        normalized_sections[section_type] = validate_and_fix_refs(
            normalized_sections[section_type],
            valid_labels,
        )

    if total_invalid_removed > 0:
        print(f"[CompilePDF] Total invalid citations removed: {total_invalid_removed}")

    normalized_sections = strip_code_path_references_fn(normalized_sections)
    normalized_sections = deduplicate_figure_environments_fn(
        normalized_sections,
        section_order=section_order,
    )
    return normalized_sections


def build_typesetter_payload(
    *,
    generated_sections: Dict[str, str],
    references: List[Dict[str, Any]],
    paper_title: str,
    output_dir: Path,
    template_path: Optional[str],
    figures_source_dir: Optional[str],
    figure_paths: Optional[Dict[str, str]],
    converted_tables: Optional[Dict[str, str]],
    figure_ids: List[str],
    section_order: List[str],
    section_titles: Dict[str, str],
    detected_column_format: str,
    canonical_bibtex: Optional[str] = None,
) -> Dict[str, Any]:
    typesetter_refs = [
        {
            "ref_id": ref.get("ref_id", ""),
            "bibtex": ref.get("bibtex"),
        }
        for ref in references
        if ref.get("bibtex")
    ]

    return {
        "sections": generated_sections,
        "section_order": section_order,
        "section_titles": section_titles,
        "template_path": template_path,
        "template_config": {
            "paper_title": paper_title,
            "paper_authors": "EasyPaper",
            "column_format": detected_column_format,
        },
        "references": typesetter_refs,
        "canonical_bibtex": canonical_bibtex,
        "figure_ids": figure_ids,
        "output_dir": str(output_dir),
        "figures_source_dir": figures_source_dir,
        "figure_paths": figure_paths or {},
        "converted_tables": converted_tables or {},
    }


async def post_typesetter_compile(
    *,
    payload: Dict[str, Any],
    request_id: str,
    self_url: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str], List[str], Dict[str, List[str]]]:
    target_url = f"{self_url or os.getenv('AGENTSYS_SELF_URL', 'http://127.0.0.1:8000')}/agent/typesetter/compile"
    async with httpx.AsyncClient(timeout=600.0) as client:
        response = await client.post(
            target_url,
            json={
                "request_id": request_id,
                "payload": payload,
            },
        )

    if response.status_code != 200:
        print(f"[MetaDataAgent] Typesetter error: {response.status_code} - {response.text}")
        return None, None, [f"Typesetter HTTP {response.status_code}"], {}

    result = response.json()
    if result.get("status") == "ok" and result.get("result"):
        compilation_result = result["result"]
        pdf_path = compilation_result.get("pdf_path")
        latex_path = compilation_result.get("source_path")
        compile_warnings = compilation_result.get("warnings", [])
        section_errors = compilation_result.get("section_errors", {})
        compile_errors = compilation_result.get("errors", []) or []

        if pdf_path:
            print(f"[MetaDataAgent] PDF compiled successfully: {pdf_path}")
            if compile_warnings:
                print(f"[MetaDataAgent] Compile warnings: {compile_warnings[:5]}")
            if section_errors:
                print(f"[MetaDataAgent] Section errors (on success): {section_errors}")
        else:
            print("[MetaDataAgent] PDF compilation failed: compilation result has no pdf_path")
            if not compile_errors:
                compile_errors = ["Typesetter compilation failed"]
            if section_errors:
                print(f"[Typesetter] Section errors: {section_errors}")
            return None, None, compile_errors, section_errors

        if latex_path:
            main_tex_path = Path(latex_path) / "main.tex"
            structure_errors = validate_main_tex_structure(main_tex_path)
            if structure_errors:
                print(f"[MetaDataAgent] main.tex structure validation failed: {structure_errors}")
                return None, None, structure_errors, section_errors

        return pdf_path, latex_path, [], section_errors

    compile_errors: List[str] = []
    section_errors: Dict[str, List[str]] = {}
    error_msg = result.get("error", "Unknown error")
    if result.get("result"):
        compile_errors = result["result"].get("errors", [])
        section_errors = result["result"].get("section_errors", {})
    if not compile_errors:
        compile_errors = [e.strip() for e in error_msg.split(";") if e.strip()]
    print(f"[MetaDataAgent] PDF compilation failed: {error_msg}")
    print(f"[Typesetter] Compile errors: {compile_errors}")
    if section_errors:
        print(f"[Typesetter] Section errors: {section_errors}")
    return None, None, compile_errors, section_errors
