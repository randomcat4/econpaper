"""
Section-file and abstract-prep helpers for TypesetterAgent.
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Optional


DEFAULT_SECTION_ORDER = [
    "introduction", "related_work", "method", "experiment", "result", "conclusion",
]

DEFAULT_SECTION_TITLES = {
    "introduction": "Introduction",
    "related_work": "Related Work",
    "method": "Methodology",
    "experiment": "Experiments",
    "result": "Results",
    "conclusion": "Conclusion",
    "appendix": "Appendix",
}


def strip_leading_section_command(content: str, strip_all_section_commands_fn) -> str:
    return strip_all_section_commands_fn(content)


def strip_all_section_commands(content: str, find_brace_end_fn) -> str:
    result = []
    i = 0
    while i < len(content):
        m = re.search(r'\\section\*?\s*\{', content[i:])
        if not m:
            result.append(content[i:])
            break

        match_abs_start = i + m.start()
        prefix_start = max(0, match_abs_start - 3)
        prefix = content[prefix_start:match_abs_start]
        if prefix.endswith("sub"):
            result.append(content[i:match_abs_start + m.end() - m.start()])
            i = match_abs_start + m.end() - m.start()
            continue

        result.append(content[i:match_abs_start])
        brace_start = match_abs_start + m.end() - m.start() - 1
        brace_end = find_brace_end_fn(content, brace_start)
        remainder_pos = brace_end

        rest = content[remainder_pos:]
        label_m = re.match(r'\s*\\label\{', rest)
        if label_m:
            label_brace = remainder_pos + label_m.end() - 1
            label_end = find_brace_end_fn(content, label_brace)
            remainder_pos = label_end

        i = remainder_pos

    cleaned = ''.join(result)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def write_section_files(
    *,
    work_dir: str,
    sections: Dict[str, str],
    section_order: Optional[List[str]] = None,
    section_titles: Optional[Dict[str, str]] = None,
    citation_style: str = "cite",
    use_appendices_env: bool = False,
    strip_leading_section_command_fn,
    apply_citation_style_fn,
    logger,
) -> Dict[str, str]:
    order = section_order or DEFAULT_SECTION_ORDER
    titles = section_titles or DEFAULT_SECTION_TITLES

    sections_dir = os.path.join(work_dir, "sections")
    os.makedirs(sections_dir, exist_ok=True)
    section_file_map: Dict[str, str] = {}

    def _write_one(section_type: str, content: str) -> None:
        content = content.strip()
        content = strip_leading_section_command_fn(content)
        content = apply_citation_style_fn(content, citation_style)
        content = re.sub(r'(?<!\\)%', r'\\%', content)
        title = titles.get(section_type, section_type.replace("_", " ").title())

        if section_type == "appendix":
            if use_appendices_env:
                file_content = (
                    f"\\begin{{appendices}}\n"
                    f"\\section{{{title}}}\\label{{secA1}}\n\n{content}\n"
                    f"\\end{{appendices}}\n"
                )
            else:
                file_content = f"\\appendix\n\\section{{{title}}}\n\n{content}\n"
        else:
            file_content = f"\\section{{{title}}}\n\n{content}\n"

        file_name = f"{section_type}.tex"
        file_path = os.path.join(sections_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
        section_file_map[section_type] = f"sections/{section_type}"
        logger.info("typesetter.write_section file=sections/%s chars=%d", file_name, len(file_content))

    for section_type in order:
        if section_type not in sections or not sections[section_type].strip():
            continue
        if section_type == "abstract":
            continue
        _write_one(section_type, sections[section_type])

    for section_type, content in sections.items():
        if section_type == "abstract" or section_type in section_file_map:
            continue
        if not content.strip():
            continue
        _write_one(section_type, content)

    logger.info("typesetter.write_sections total=%d files=%s", len(section_file_map), list(section_file_map.keys()))
    return section_file_map


def apply_citation_style(content: str, citation_style: str) -> str:
    if citation_style == "citep":
        content = re.sub(r'\\cite\{', r'\\citep{', content)
    elif citation_style == "citet":
        content = re.sub(r'\\cite\{', r'\\citet{', content)
    return content


def normalize_abstract(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r'\n\s*\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
