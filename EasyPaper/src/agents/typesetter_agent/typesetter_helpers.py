"""
Stateless resource and citation helpers for TypesetterAgent.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .models import BibEntry, TemplateConfig


def resolve_figure_ids(state: dict, extract_includegraphics_targets_fn) -> List[str]:
    ids: set[str] = set()
    for item in (state.get("figure_ids") or []):
        if item:
            ids.add(str(item))
    for key in (state.get("figure_paths") or {}).keys():
        if key:
            ids.add(str(key))

    if not ids:
        sections = state.get("sections") or {}
        combined = "\n".join(content for content in sections.values() if isinstance(content, str))
        if not combined.strip():
            combined = str(state.get("latex_content") or "")
        for token in extract_includegraphics_targets_fn(combined):
            ids.add(token)
    return sorted(ids)


def extract_includegraphics_targets(content: str) -> List[str]:
    pattern = r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}'
    targets: List[str] = []
    seen = set()
    for raw in re.findall(pattern, content or ""):
        token = str(raw).strip()
        if not token:
            continue
        if "/" in token or token.startswith(".") or token.endswith((".png", ".jpg", ".jpeg", ".pdf", ".svg")):
            continue
        if token not in seen:
            seen.add(token)
            targets.append(token)
    return targets


def strip_graphics_extension(path: str) -> str:
    root, ext = os.path.splitext(path)
    if ext.lower() in {".png", ".jpg", ".jpeg", ".pdf", ".svg", ".eps"}:
        return root
    return path


def build_figure_id_map(
    figure_paths: Dict[str, str],
    work_dir: str,
) -> Dict[str, str]:
    id_map: Dict[str, str] = {}
    for fig_id, file_path in figure_paths.items():
        if not fig_id or not file_path:
            continue
        filename = os.path.basename(file_path)
        if not filename:
            continue
        candidate = os.path.join("figures", filename).replace("\\", "/")
        abs_candidate = os.path.join(work_dir, candidate)
        if not os.path.exists(abs_candidate):
            continue
        rel_path = strip_graphics_extension(candidate)

        variants = {fig_id}
        variants.add(fig_id.replace(":", "_"))
        if ":" in fig_id:
            variants.add(fig_id.split(":", 1)[1])
        stem = os.path.splitext(filename)[0]
        variants.add(stem)
        variants.add(f"figures/{stem}")
        variants.add(f"figures/{filename}")

        for variant in variants:
            if variant and variant not in id_map:
                id_map[variant] = rel_path
    return id_map


def rewrite_includegraphics_targets(
    content: str,
    work_dir: str,
    id_to_rel_path: Dict[str, str],
) -> str:
    if not content:
        return content

    def _resolve_target(raw_target: str) -> str:
        target = raw_target.strip().replace("\\", "/")
        if not target:
            return target
        if target in id_to_rel_path:
            return id_to_rel_path[target]

        abs_existing = os.path.join(work_dir, target)
        if os.path.exists(abs_existing):
            return strip_graphics_extension(target)

        basename = os.path.basename(target)
        candidate = f"figures/{basename}"
        if os.path.exists(os.path.join(work_dir, candidate)):
            return strip_graphics_extension(candidate)
        for ext in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"):
            ext_candidate = f"figures/{basename}{ext}"
            if os.path.exists(os.path.join(work_dir, ext_candidate)):
                return strip_graphics_extension(ext_candidate)
        return target

    pattern = r'(\\includegraphics)(?:\[([^\]]*)\])?\{([^}]+)\}'

    def _rewrite(match: re.Match) -> str:
        cmd = match.group(1)
        opts = match.group(2)
        target = match.group(3)
        resolved_target = _resolve_target(target)
        if opts is None or not opts.strip():
            return f"{cmd}[width=0.9\\linewidth]{{{resolved_target}}}"
        return f"{cmd}[{opts}]{{{resolved_target}}}"

    return re.sub(pattern, _rewrite, content)


def validate_resolved_figure_includes(
    compiled_tex_or_main_tex: str,
    figure_paths: Dict[str, str],
) -> List[str]:
    """
    Validate post-typesetter includegraphics targets against resolved assets.

    This must run after the typesetter has copied figures and rewritten figure
    IDs to paths. It intentionally does not inspect raw writer sections.
    """
    if not compiled_tex_or_main_tex:
        return []
    tex_path = compiled_tex_or_main_tex
    if os.path.isdir(tex_path):
        tex_path = os.path.join(tex_path, "main.tex")
    if not os.path.exists(tex_path):
        return [f"Compiled TeX file not found for figure include validation: {tex_path}"]
    work_dir = os.path.dirname(tex_path)
    with open(tex_path, "r", encoding="utf-8") as handle:
        content = handle.read()
    targets = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", content or "")
    errors: List[str] = []
    for raw in targets:
        target = str(raw).strip().replace("\\", "/")
        if not target:
            continue
        candidates = [target]
        root, ext = os.path.splitext(target)
        if not ext:
            candidates.extend(f"{target}{suffix}" for suffix in (".pdf", ".png", ".jpg", ".jpeg", ".svg", ".eps"))
        if target in figure_paths:
            candidates.append(os.path.join("figures", os.path.basename(figure_paths[target])))
        if not any(os.path.exists(os.path.join(work_dir, candidate)) for candidate in candidates):
            errors.append(f"Resolved figure include target is missing: {target}")
    return errors


def extract_citations_from_content(latex_content: str) -> List[str]:
    pattern = r'\\cite[tp]?\{([^}]+)\}'
    matches = re.findall(pattern, latex_content)
    all_keys = []
    for match in matches:
        keys = [k.strip() for k in match.split(',')]
        all_keys.extend(keys)

    invalid_keys = {'ref_id', 'id', 'key', 'citation', 'reference'}
    seen = set()
    unique_keys = []
    for key in all_keys:
        if not key or key in seen or key.lower() in invalid_keys:
            continue
        if re.match(r'^[a-zA-Z][a-zA-Z0-9_\-:]+$', key):
            seen.add(key)
            unique_keys.append(key)
    return unique_keys


def generate_bibtex_entry(entry: BibEntry) -> str:
    lines = [f"@{entry.entry_type}{{{entry.key},"]
    if entry.title:
        lines.append(f"  title = {{{entry.title}}},")
    if entry.authors:
        lines.append(f"  author = {{{entry.authors}}},")
    if entry.year:
        lines.append(f"  year = {{{entry.year}}},")
    if entry.booktitle:
        lines.append(f"  booktitle = {{{entry.booktitle}}},")
    elif entry.journal:
        lines.append(f"  journal = {{{entry.journal}}},")
    elif entry.venue:
        if entry.entry_type in ["inproceedings", "conference"]:
            lines.append(f"  booktitle = {{{entry.venue}}},")
        else:
            lines.append(f"  journal = {{{entry.venue}}},")
    if entry.doi:
        lines.append(f"  doi = {{{entry.doi}}},")
    if entry.url:
        lines.append(f"  url = {{{entry.url}}},")
    lines.append("}")
    return "\n".join(lines)


def build_preamble_from_config(config: TemplateConfig) -> str:
    if config.raw_preamble:
        return config.raw_preamble

    doc_options = list(config.document_class_options)
    if config.column_format == "double" and "twocolumn" not in doc_options:
        doc_options.append("twocolumn")

    options_str = ",".join(doc_options) if doc_options else ""
    if options_str:
        doc_class_line = f"\\documentclass[{options_str}]{{{config.document_class}}}"
    else:
        doc_class_line = f"\\documentclass{{{config.document_class}}}"

    packages = [
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage[T1]{fontenc}",
        "\\usepackage{graphicx}",
        "\\usepackage{amsmath}",
        "\\usepackage{amssymb}",
        "\\usepackage{hyperref}",
        "\\usepackage[margin=1in]{geometry}",
    ]
    if config.citation_style in ("citep", "citet"):
        packages.append("\\usepackage{natbib}")
    else:
        packages.append("\\usepackage{cite}")
    for pkg in config.required_packages:
        pkg_line = f"\\usepackage{{{pkg}}}"
        if pkg_line not in packages:
            packages.append(pkg_line)

    title_section = []
    title_section.append(f"\\title{{{config.paper_title}}}" if config.paper_title else "\\title{Generated Paper}")
    title_section.append(f"\\author{{{config.paper_authors}}}" if config.paper_authors else "\\author{}")
    title_section.append("\\date{\\today}")

    preamble_parts = [
        doc_class_line,
        "",
        "% Packages",
        "\n".join(packages),
        "",
        "% Title",
        "\n".join(title_section),
    ]
    return "\n".join(preamble_parts)
