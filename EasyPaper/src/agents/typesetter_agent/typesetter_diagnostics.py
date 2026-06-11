"""
Diagnostics and output-copy helpers for TypesetterAgent.
"""
from __future__ import annotations

import os
import re
import shutil
from typing import Dict, List, Optional, Set


def save_diagnostics_on_failure(work_dir: str, output_dir: str, logger) -> None:
    os.makedirs(output_dir, exist_ok=True)
    diag_exts = ('.tex', '.log', '.bib', '.bbl', '.aux')
    for item in os.listdir(work_dir):
        src = os.path.join(work_dir, item)
        if os.path.isfile(src) and item.endswith(diag_exts):
            try:
                shutil.copy2(src, os.path.join(output_dir, item))
            except Exception as e:
                logger.warning("typesetter.diag_copy_failed file=%s error=%s", item, e)
        elif os.path.isdir(src) and item == 'sections':
            dst_sec = os.path.join(output_dir, 'sections')
            os.makedirs(dst_sec, exist_ok=True)
            for sf in os.listdir(src):
                sf_src = os.path.join(src, sf)
                if os.path.isfile(sf_src):
                    try:
                        shutil.copy2(sf_src, os.path.join(dst_sec, sf))
                    except Exception as e:
                        logger.warning("typesetter.diag_copy_failed file=sections/%s error=%s", sf, e)


def copy_to_output_dir(work_dir: str, output_dir: str, logger) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    output_figures = os.path.join(output_dir, "figures")
    os.makedirs(output_figures, exist_ok=True)
    result_paths = {"pdf_path": None, "source_path": output_dir}
    files_to_copy = []

    for item in os.listdir(work_dir):
        src_path = os.path.join(work_dir, item)
        if os.path.isfile(src_path):
            if item.endswith('.pdf') and item == 'main.pdf':
                dst_path = os.path.join(output_dir, 'main.pdf')
                result_paths["pdf_path"] = dst_path
                files_to_copy.append((src_path, dst_path))
            elif item.endswith(('.tex', '.bib', '.bst', '.sty', '.cls', '.bbl', '.blg', '.aux', '.log')):
                dst_path = os.path.join(output_dir, item)
                files_to_copy.append((src_path, dst_path))
            elif item.endswith(('.png', '.jpg', '.jpeg', '.pdf', '.eps')) and item != 'main.pdf':
                dst_path = os.path.join(output_figures, item)
                files_to_copy.append((src_path, dst_path))
        elif os.path.isdir(src_path) and item == 'figures':
            for fig_file in os.listdir(src_path):
                fig_src = os.path.join(src_path, fig_file)
                if os.path.isfile(fig_src):
                    fig_dst = os.path.join(output_figures, fig_file)
                    files_to_copy.append((fig_src, fig_dst))
        elif os.path.isdir(src_path) and item == 'sections':
            output_sections = os.path.join(output_dir, "sections")
            os.makedirs(output_sections, exist_ok=True)
            for sec_file in os.listdir(src_path):
                sec_src = os.path.join(src_path, sec_file)
                if os.path.isfile(sec_src):
                    sec_dst = os.path.join(output_sections, sec_file)
                    files_to_copy.append((sec_src, sec_dst))

    for src, dst in files_to_copy:
        try:
            shutil.copy2(src, dst)
        except Exception as e:
            logger.warning("typesetter.copy_failed src=%s dst=%s error=%s", src, dst, str(e))

    return result_paths


def extract_errors(log_content: str) -> List[str]:
    errors = []
    error_patterns = [
        r'! (.*?)(?:\n|$)',
        r'Error: (.*?)(?:\n|$)',
        r'Fatal error occurred, (.*?)(?:\n|$)',
    ]
    for pattern in error_patterns:
        matches = re.findall(pattern, log_content)
        errors.extend(matches[:5])
    return list(set(errors))[:10]


def extract_warnings(log_content: str) -> List[str]:
    warnings = []
    warning_patterns = [
        r'Warning: (.*?)(?:\n|$)',
        r'LaTeX Warning: (.*?)(?:\n|$)',
    ]
    for pattern in warning_patterns:
        matches = re.findall(pattern, log_content)
        warnings.extend(matches[:5])
    return list(set(warnings))[:10]


def extract_section_errors(
    log_content: str,
    section_file_map: Dict[str, str],
) -> Dict[str, List[str]]:
    file_to_section: Dict[str, str] = {}
    for section_type, rel_path in section_file_map.items():
        fname = rel_path + ".tex"
        file_to_section[fname] = section_type
        file_to_section["./" + fname] = section_type

    section_errors: Dict[str, List[str]] = {}
    file_stack: List[str] = []
    current_section = None

    lines = log_content.split('\n')
    for line in lines:
        file_open_matches = re.findall(r'\((\.?/[^()\s]+\.tex)', line)
        for file_path in file_open_matches:
            file_stack.append(file_path)
            current_section = file_to_section.get(file_path, current_section)

        close_count = line.count(')')
        for _ in range(close_count):
            if file_stack:
                file_stack.pop()
        if file_stack:
            current_section = file_to_section.get(file_stack[-1], current_section)

        if line.startswith('! '):
            error_msg = line[2:].strip()
            if current_section:
                section_errors.setdefault(current_section, []).append(error_msg)

    return {k: v[:10] for k, v in section_errors.items()}


def strip_tex_comments(content: str) -> str:
    cleaned_lines: List[str] = []
    for line in (content or "").splitlines():
        buf: List[str] = []
        idx = 0
        while idx < len(line):
            ch = line[idx]
            if ch == "%" and (idx == 0 or line[idx - 1] != "\\"):
                break
            buf.append(ch)
            idx += 1
        cleaned_lines.append("".join(buf))
    return "\n".join(cleaned_lines)


def extract_document_body(tex_src: str) -> str:
    body_start = (tex_src or "").find(r"\begin{document}")
    if body_start < 0:
        return tex_src or ""
    return tex_src[body_start + len(r"\begin{document}") :]


def resolve_include_path(
    include_target: str,
    base_dir: str,
    work_dir: str,
) -> Optional[str]:
    target = (include_target or "").strip()
    if not target:
        return None

    normalized = target.replace("/", os.sep).replace("\\", os.sep)
    if os.path.isabs(normalized):
        candidates = [normalized]
    else:
        candidates = [
            os.path.join(base_dir, normalized),
            os.path.join(work_dir, normalized),
        ]

    expanded: List[str] = []
    for cand in candidates:
        expanded.append(cand)
        if not cand.lower().endswith(".tex"):
            expanded.append(cand + ".tex")

    for cand in expanded:
        if os.path.isfile(cand):
            return os.path.abspath(cand)
    return None


def has_tex_command(content: str, command: str) -> bool:
    if not content or not command:
        return False
    pattern = rf"\\{re.escape(command)}(?![A-Za-z@])"
    return re.search(pattern, content) is not None


def expand_tex_includes_for_detection(
    *,
    content: str,
    current_file: str,
    work_dir: str,
    visited: Set[str],
    logger,
) -> str:
    stripped = strip_tex_comments(content)
    include_re = re.compile(r"\\(?:input|include)\{([^}]+)\}")
    base_dir = os.path.dirname(current_file)

    out_parts: List[str] = []
    last_idx = 0
    for match in include_re.finditer(stripped):
        out_parts.append(stripped[last_idx: match.start()])
        target = match.group(1).strip()
        include_path = resolve_include_path(target, base_dir, work_dir)
        if not include_path:
            logger.warning(
                "typesetter.include_not_found target=%s base=%s",
                target,
                current_file,
            )
            last_idx = match.end()
            continue

        include_key = os.path.normcase(os.path.abspath(include_path))
        if include_key in visited:
            logger.warning("typesetter.include_cycle_skipped path=%s", include_path)
            last_idx = match.end()
            continue

        visited.add(include_key)
        try:
            with open(include_path, "r", encoding="utf-8", errors="ignore") as f:
                include_src = f.read()
            expanded = expand_tex_includes_for_detection(
                content=include_src,
                current_file=include_path,
                work_dir=work_dir,
                visited=visited,
                logger=logger,
            )
            out_parts.append("\n")
            out_parts.append(expanded)
            out_parts.append("\n")
        except Exception as e:
            logger.warning(
                "typesetter.include_read_failed path=%s error=%s",
                include_path,
                e,
            )

        last_idx = match.end()

    out_parts.append(stripped[last_idx:])
    return "".join(out_parts)


def build_detection_body(
    *,
    tex_src: str,
    main_tex: str,
    work_dir: str,
    logger,
) -> str:
    body = extract_document_body(tex_src)
    try:
        visited: Set[str] = {os.path.normcase(os.path.abspath(main_tex))}
        expanded = expand_tex_includes_for_detection(
            content=body,
            current_file=main_tex,
            work_dir=work_dir,
            visited=visited,
            logger=logger,
        )
        if expanded.strip():
            return expanded
    except Exception as e:
        logger.warning("typesetter.include_expansion_failed error=%s", e)
    return strip_tex_comments(body)
