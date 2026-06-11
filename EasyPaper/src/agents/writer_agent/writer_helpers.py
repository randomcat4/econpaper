"""
Utility helpers for WriterAgent.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List


def build_revision_prompt(review_result: Dict[str, Any]) -> str:
    """
    Build a revision prompt from review results.
    """
    parts = ["The following issues were found in your output:"]

    for issue in review_result.get("issues", []):
        parts.append(f"- ISSUE: {issue}")

    for warning in review_result.get("warnings", []):
        parts.append(f"- WARNING: {warning}")

    parts.append("\nPlease revise your output to address these issues.")

    if review_result.get("invalid_citations"):
        parts.append(
            f"\nREMOVE these invalid citations completely (do not replace): {review_result['invalid_citations']}"
        )

    missing = review_result.get("missing_key_points", [])
    if missing:
        parts.append("\nYou MUST address the following key points that are currently missing:")
        for kp in missing:
            parts.append(f"  - {kp}")

    return "\n".join(parts)


def extract_paragraph_units(
    section_type: str,
    latex_content: str,
) -> List[Dict[str, Any]]:
    """
    Extract paragraph-addressable units from section LaTeX.
    """
    units: List[Dict[str, Any]] = []
    if not latex_content or not latex_content.strip():
        return units

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", latex_content) if p.strip()]
    for idx, paragraph in enumerate(paragraphs):
        sentence_candidates = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", paragraph.replace("\n", " "))
            if s.strip()
        ]
        units.append(
            {
                "paragraph_id": f"{section_type}.p{idx}",
                "section_type": section_type,
                "paragraph_index": idx,
                "text": paragraph,
                "sentence_count": len(sentence_candidates),
                "sentences": sentence_candidates,
            }
        )
    return units


def clean_latex_output(content: str) -> str:
    """
    Clean LLM output to ensure pure LaTeX.
    """
    content = re.sub(r'^```(?:latex|tex)?\s*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)
    content = re.sub(r'^```\s*\n', '', content)
    content = re.sub(r'\n```\s*$', '', content)

    content = re.sub(r'\\documentclass.*?\n', '', content)
    content = re.sub(r'\\begin\{document\}', '', content)
    content = re.sub(r'\\end\{document\}', '', content)
    content = re.sub(r'\\usepackage.*?\n', '', content)

    content = re.sub(r'\*\*(.+?)\*\*', r'\\textbf{\1}', content)
    content = re.sub(r'__(.+?)__', r'\\textbf{\1}', content)
    content = re.sub(r'(?<![\\{])\*([^*\n]+?)\*', r'\\textit{\1}', content)
    content = re.sub(r'(?<=\s)_([^_\n]+?)_(?=[\s.,;:)])', r'\\textit{\1}', content)
    content = re.sub(r'`([^`\n]+?)`', r'\\texttt{\1}', content)
    content = re.sub(r'^###\s+(.+)$', r'\\subsubsection{\1}', content, flags=re.MULTILINE)
    content = re.sub(r'^##\s+(.+)$', r'\\subsection{\1}', content, flags=re.MULTILINE)

    return content.strip()
