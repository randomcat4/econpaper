"""
Helper utilities for TemplateParserAgent.
"""
from __future__ import annotations

import re
from typing import Dict, Optional


def clean_json_content(content: str) -> str:
    """
    Clean and extract JSON from LLM response.
    """
    if not content:
        return "{}"
    content = content.strip()
    if content.startswith('{'):
        return content

    markdown_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', content)
    if markdown_match:
        return markdown_match.group(1)

    json_match = re.search(r'\{[\s\S]*\}', content)
    if json_match:
        return json_match.group()

    return "{}"


def find_main_tex_path(extracted_files: Dict[str, str]) -> str:
    for path, content in extracted_files.items():
        if path.endswith('.tex') and '\\documentclass' in content:
            return path
    return "main.tex"


def extract_preamble(content: str) -> Optional[str]:
    if not content:
        return None
    match = re.search(r'(\\documentclass.*?)\\begin\{document\}', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def parse_template_rules(extracted_files: Dict[str, str]) -> Dict[str, object]:
    template_info = {
        "template_id": "unknown",
        "main_tex_path": "main.tex",
        "citation_style": "cite",
        "figure_placement": "htbp",
        "section_commands": ["section", "subsection", "subsubsection"],
        "required_packages": [],
        "bib_style": None,
        "document_class": "article",
        "template_structure": {},
        "has_abstract": True,
        "has_acknowledgment": False,
        "column_format": "single",
    }

    for path, content in extracted_files.items():
        if not path.endswith('.tex'):
            continue

        doc_class = re.search(r'\\documentclass(?:\[.*?\])?\{(\w+)\}', content)
        if doc_class:
            template_info["document_class"] = doc_class.group(1)

        if 'twocolumn' in content or 'IEEEtran' in content:
            template_info["column_format"] = "double"

        packages = re.findall(r'\\usepackage(?:\[.*?\])?\{([^}]+)\}', content)
        for pkg in packages:
            for package in pkg.split(','):
                package = package.strip()
                if package and package not in template_info["required_packages"]:
                    template_info["required_packages"].append(package)

        if '\\citep' in content or 'natbib' in content:
            template_info["citation_style"] = "citep"
        elif '\\citet' in content:
            template_info["citation_style"] = "citet"

        if '\\begin{abstract}' in content or '\\abstract' in content:
            template_info["has_abstract"] = True

        if 'acknowledgment' in content.lower() or 'acknowledgement' in content.lower():
            template_info["has_acknowledgment"] = True

        bib_style = re.search(r'\\bibliographystyle\{(\w+)\}', content)
        if bib_style:
            template_info["bib_style"] = bib_style.group(1)

    return template_info
