"""
Paper assembly and discovered-reference merge helpers for MetaDataAgent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from ..shared.reference_pool import ReferencePool


def _venue_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _latex_word_count(text: str) -> int:
    cleaned = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text or "")
    cleaned = re.sub(r"[^A-Za-z0-9']+", " ", cleaned)
    return len([word for word in cleaned.split() if word])


def _truncate_to_word_limit(text: str, limit: int) -> str:
    words = str(text or "").split()
    if len(words) <= limit:
        return str(text or "")
    return " ".join(words[:limit])


def _venue_author(venue_config: Optional[Dict[str, Any]]) -> str:
    if isinstance(venue_config, dict) and venue_config.get("anonymous"):
        return "Anonymous Manuscript"
    return "Author Names"


def _total_word_count(sections: Dict[str, str]) -> int:
    return sum(_latex_word_count(content) for content in (sections or {}).values())


def assemble_paper(
    *,
    title: str,
    sections: Dict[str, str],
    references: List[Dict[str, Any]],
    valid_citation_keys: Set[str],
    escape_latex_fn,
    fix_latex_references_fn,
    validate_and_fix_citations_fn,
    section_order: Optional[List[str]] = None,
    section_titles: Optional[Dict[str, str]] = None,
    venue_config: Optional[Dict[str, Any]] = None,
) -> str:
    venue_config = venue_config or {}
    abstract_limit = _venue_int(venue_config.get("abstract_limit"))
    author = _venue_author(venue_config)
    total_word_count = _total_word_count(sections)
    latex = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{natbib}

\title{""" + escape_latex_fn(title) + r"""}
\author{""" + escape_latex_fn(author) + r"""}
\date{\today}

\begin{document}

\maketitle

"""
    if venue_config.get("require_total_word_count"):
        latex += (
            "\\noindent\\textbf{Total word count:} "
            f"{total_word_count}\\par\n\n"
        )

    if "abstract" in sections:
        abstract_text = sections["abstract"].strip()
        abstract_text = re.sub(r'\\title\{[^}]*\}\s*', '', abstract_text)
        abstract_text = re.sub(r'\\maketitle\s*', '', abstract_text)
        abstract_text = re.sub(r'\\begin\{abstract\}\s*', '', abstract_text)
        abstract_text = re.sub(r'\s*\\end\{abstract\}', '', abstract_text)
        abstract_text = abstract_text.strip()
        if abstract_limit:
            abstract_text = _truncate_to_word_limit(abstract_text, abstract_limit)
        latex += r"\begin{abstract}" + "\n"
        latex += abstract_text + "\n"
        latex += r"\end{abstract}" + "\n\n"

    _default_order = ["introduction", "related_work", "method", "experiment", "result", "discussion", "conclusion"]
    _default_titles = {
        "introduction": "Introduction",
        "related_work": "Related Work",
        "method": "Methodology",
        "experiment": "Experiments",
        "result": "Results",
        "discussion": "Discussion",
        "conclusion": "Conclusion",
    }
    titles = dict(_default_titles)
    titles.update(section_titles or {})
    if section_order:
        ordered_sections = [
            section_type
            for section_type in section_order
            if section_type != "abstract" and section_type in sections
        ]
        for s in sections:
            if (
                s != "abstract"
                and s not in ordered_sections
                and s not in _default_order
            ):
                ordered_sections.append(s)
    else:
        ordered_sections = [s for s in _default_order if s in sections]
        for s in sections:
            if s != "abstract" and s not in ordered_sections:
                ordered_sections.append(s)

    for section_type in ordered_sections:
        if section_type in sections and sections[section_type]:
            sec_title = titles.get(section_type, section_type.replace("_", " ").title())
            latex += f"\\section{{{sec_title}}}\n"
            content = re.sub(r'\\section\*?\s*\{[^}]*\}\s*(?:\\label\{[^}]*\}\s*)?', '', sections[section_type])
            content = fix_latex_references_fn(content)
            content, invalid, _ = validate_and_fix_citations_fn(
                content, valid_citation_keys, remove_invalid=True
            )
            if invalid:
                print(f"[Assemble] Removed {len(invalid)} invalid citations from {section_type}: {invalid[:5]}")
            latex += content + "\n\n"

    latex += r"""
\bibliographystyle{plainnat}
\bibliography{references}

\end{document}
"""
    return latex


def validate_and_merge_new_references(
    *,
    content: str,
    msg_history: List[Dict[str, Any]],
    ref_pool: ReferencePool,
) -> str:
    search_results = ReferencePool.extract_search_results_from_history(msg_history)
    if search_results:
        print(f"[ValidateRefs] Found {len(search_results)} papers from search results")

    cited_keys = ReferencePool.extract_cite_keys(content)
    if not cited_keys:
        return content

    print(f"[ValidateRefs] Content cites {len(cited_keys)} keys: {cited_keys}")
    removable_keys = []
    for key in cited_keys:
        if key in ref_pool.valid_citation_keys:
            continue
        if key in search_results:
            added = ref_pool.add_discovered(key, search_results[key], source="search")
            if added:
                print(f"[ValidateRefs] Stored unvetted discovered ref and removed citation: {key}")
            else:
                print(f"[ValidateRefs] Non-citable discovered ref removed: {key}")
            removable_keys.append(key)
        else:
            removable_keys.append(key)
            print(f"[ValidateRefs] Hallucinated key removed: {key}")

    for key in removable_keys:
        content = ReferencePool.remove_citation(content, key)

    if removable_keys:
        print(f"[ValidateRefs] Removed {len(removable_keys)} non-citable citations")
    return content
