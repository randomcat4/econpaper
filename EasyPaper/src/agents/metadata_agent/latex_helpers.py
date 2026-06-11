"""
Stateless LaTeX and typesetter-support helpers for MetaDataAgent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from ..shared.asset_paths import resolve_asset_path

if TYPE_CHECKING:
    from .models import FigureSpec


def collect_figure_paths(
    figures: List["FigureSpec"],
    base_path: Optional[str] = None,
) -> Dict[str, str]:
    paths = {}
    for fig in figures:
        if fig.auto_generate:
            print(f"[MetaDataAgent] Figure auto-generation not implemented: {fig.id}")
            continue
        figure_path = getattr(fig, "derived_file_path", None) or fig.file_path
        if figure_path:
            resolved = resolve_asset_path(
                figure_path,
                materials_root=base_path,
                require_within_root=bool(base_path),
            )
            if resolved.exists and resolved.resolved_path:
                paths[fig.id] = resolved.resolved_path
            else:
                print(f"[MetaDataAgent] Warning: Figure file not found: {resolved.resolved_path}")
    return paths


def fix_latex_references(content: str) -> str:
    content = re.sub(r'\\%[-=]+\s*\n?', '', content)
    content = re.sub(r'^\s*\\%[-=]+.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'\\reftab\{([^}]+)\}', r'\\ref{tab:\1}', content)
    content = re.sub(r'\\reffig\{([^}]+)\}', r'\\ref{fig:\1}', content)
    content = re.sub(r'(Table~?\\ref\{)(?!tab:|fig:)([^}]+)\}', r'\1tab:\2}', content)
    content = re.sub(r'(Figure~?\\ref\{)(?!tab:|fig:)([^}]+)\}', r'\1fig:\2}', content)
    return content


def extract_valid_citation_keys(parsed_refs: List[Dict[str, Any]]) -> set:
    keys = set()
    for ref in parsed_refs:
        ref_id = ref.get("ref_id", "")
        if ref_id:
            keys.add(ref_id)
    return keys


def validate_and_fix_citations(
    content: str,
    valid_keys: set,
    remove_invalid: bool = True,
) -> Tuple[str, List[str], List[str]]:
    cite_pattern = r'\\(cite[pt]?|citeauthor|citeyear|citealt|citealp)\{([^}]+)\}'
    invalid_keys: List[str] = []
    valid_keys_used: List[str] = []

    def process_cite(match):
        cmd_name = match.group(1)
        cite_content = match.group(2)
        keys = [k.strip() for k in cite_content.split(',')]

        valid_in_cite = []
        for key in keys:
            if key in valid_keys:
                valid_in_cite.append(key)
                if key not in valid_keys_used:
                    valid_keys_used.append(key)
            else:
                if key not in invalid_keys:
                    invalid_keys.append(key)

        if remove_invalid:
            if valid_in_cite:
                return f'\\{cmd_name}{{{", ".join(valid_in_cite)}}}'
            return ''
        return match.group(0)

    fixed_content = re.sub(cite_pattern, process_cite, content)
    fixed_content = re.sub(r'\\(?:cite[pt]?|citeauthor|citeyear|citealt|citealp)\{\s*\}', '', fixed_content)
    fixed_content = re.sub(r'  +', ' ', fixed_content)
    fixed_content = re.sub(r' +([.,;:])', r'\1', fixed_content)
    return fixed_content, invalid_keys, valid_keys_used


def deduplicate_figure_environments(
    generated_sections: Dict[str, str],
    section_order: Optional[List[str]] = None,
) -> Dict[str, str]:
    if section_order:
        ordered_keys = [k for k in section_order if k in generated_sections]
        ordered_keys += [k for k in generated_sections if k not in ordered_keys]
    else:
        ordered_keys = list(generated_sections.keys())

    seen_labels: set = set()
    total_removed = 0

    for section_type in ordered_keys:
        content = generated_sections.get(section_type, "")
        if not content:
            continue

        env_pattern = re.compile(r'\\begin\{(figure\*?)\}(?:\[[^\]]*\])?.*?\\end\{\1\}', re.DOTALL)
        new_content = content
        offset = 0

        for m in env_pattern.finditer(content):
            block = m.group(0)
            labels = re.findall(r'\\label\{([^}]+)\}', block)
            label = labels[0] if labels else None
            if label and label in seen_labels:
                start = m.start() + offset
                end = m.end() + offset
                new_content = new_content[:start] + new_content[end:]
                offset += -(m.end() - m.start())
                total_removed += 1
            elif label:
                seen_labels.add(label)

        generated_sections[section_type] = new_content.strip()

    if total_removed > 0:
        print(f"[DeduplicateFigures] Removed {total_removed} duplicate figure environments")
    return generated_sections


def enforce_table_placement(
    sections: Dict[str, str],
    table_assignments: Dict[str, str],
) -> Dict[str, str]:
    if not table_assignments:
        return sections

    result = dict(sections)
    total_removed = 0

    for section_type, content in sections.items():
        if not content:
            continue

        env_pattern = re.compile(r'\\begin\{(table\*?)\}(?:\[[^\]]*\])?.*?\\end\{\1\}', re.DOTALL)
        new_content = content
        offset = 0

        for m in env_pattern.finditer(content):
            block = m.group(0)
            labels = re.findall(r'\\label\{([^}]+)\}', block)
            label = labels[0] if labels else None
            if label and label in table_assignments:
                assigned_section = table_assignments[label]
                if section_type != assigned_section:
                    start = m.start() + offset
                    end = m.end() + offset
                    new_content = new_content[:start] + new_content[end:]
                    offset -= (m.end() - m.start())
                    total_removed += 1

        result[section_type] = new_content.strip()

    if total_removed > 0:
        print(f"[EnforceTablePlacement] Removed {total_removed} misplaced table(s)")
    return result


def enforce_figure_placement(
    sections: Dict[str, str],
    figure_assignments: Dict[str, str],
) -> Dict[str, str]:
    """
    Remove assigned figure environments from non-owner sections.

    The owner-section fallback injector runs after this helper. That ordering is
    intentional: a misplaced figure definition must not make the correct owner
    section look satisfied.
    """
    if not figure_assignments:
        return sections

    result = dict(sections)
    total_removed = 0

    for section_type, content in sections.items():
        if not content:
            continue

        env_pattern = re.compile(r'\\begin\{(figure\*?)\}(?:\[[^\]]*\])?.*?\\end\{\1\}', re.DOTALL)
        new_content = content
        offset = 0

        for m in env_pattern.finditer(content):
            block = m.group(0)
            labels = re.findall(r'\\label\{([^}]+)\}', block)
            label = labels[0] if labels else None
            if label and label in figure_assignments:
                assigned_section = figure_assignments[label]
                if section_type != assigned_section:
                    start = m.start() + offset
                    end = m.end() + offset
                    new_content = new_content[:start] + new_content[end:]
                    offset -= (m.end() - m.start())
                    total_removed += 1

        result[section_type] = new_content.strip()

    if total_removed > 0:
        print(f"[EnforceFigurePlacement] Removed {total_removed} misplaced figure(s)")
    return result


def _strip_latex_comments(content: str) -> str:
    return re.sub(r'(?m)^\s*%.*$', '', content or "")


def _strip_float_environments(content: str) -> str:
    content = re.sub(r'\\begin\{figure\*?\}(?:\[[^\]]*\])?.*?\\end\{figure\*?\}', '', content or "", flags=re.DOTALL)
    content = re.sub(r'\\begin\{table\*?\}(?:\[[^\]]*\])?.*?\\end\{table\*?\}', '', content, flags=re.DOTALL)
    return content


_HARDCODED_FIGURE_RE = re.compile(r'(?<![A-Za-z])(?:Figure|Fig\.)\s*~?\s*(\d+|\[[A-Za-z0-9?]+\])')


def _stash_figure_float_blocks(content: str) -> Tuple[str, List[str]]:
    float_blocks: List[str] = []

    def _stash_float(match: re.Match[str]) -> str:
        float_blocks.append(match.group(0))
        return f"@@EASYPAPER_FLOAT_{len(float_blocks) - 1}@@"

    stashed = re.sub(r'\\begin\{figure\*?\}(?:\[[^\]]*\])?.*?\\end\{figure\*?\}', _stash_float, content, flags=re.DOTALL)
    return stashed, float_blocks


def _restore_figure_float_blocks(content: str, float_blocks: List[str]) -> str:
    restored = content
    for idx, block in enumerate(float_blocks):
        restored = restored.replace(f"@@EASYPAPER_FLOAT_{idx}@@", block)
    return restored


def _remove_unowned_hardcoded_figure_references(content: str) -> str:
    """
    Delete unrecoverable hard-coded figure numbers from prose.

    If a section has no unique assigned figure, guessing a label would violate
    semantic ownership. The least-bad deterministic repair is to remove only the
    invalid visual pointer while leaving the scientific claim intact.
    """
    stashed, float_blocks = _stash_figure_float_blocks(content)
    target = r'(?:\d+|\[[A-Za-z0-9?]+\])'
    figure_token = rf'(?:Figure|Fig\.)\s*~?\s*{target}'

    stashed = re.sub(
        rf'\s*\(\s*(?:see\s+)?{figure_token}\s*\)',
        '',
        stashed,
        flags=re.IGNORECASE,
    )
    stashed = re.sub(
        rf'\bis\s+(?:illustrated|shown|depicted)\s+in\s+{figure_token}\s*,\s+which\s+details\b',
        'details',
        stashed,
        flags=re.IGNORECASE,
    )
    stashed = re.sub(
        rf'\b(?:as\s+)?(?:illustrated|shown|depicted)\s+in\s+{figure_token}\s*,?\s*',
        '',
        stashed,
        flags=re.IGNORECASE,
    )
    stashed = re.sub(
        rf'\s+\bin\s+{figure_token}\b',
        '',
        stashed,
        flags=re.IGNORECASE,
    )
    stashed = re.sub(
        rf'\s+(?:and|or)\s+{figure_token}\b',
        '',
        stashed,
        flags=re.IGNORECASE,
    )
    stashed = re.sub(r'\s+([,.;:])', r'\1', stashed)
    stashed = re.sub(r' {2,}', ' ', stashed)
    return _restore_figure_float_blocks(stashed, float_blocks)


def repair_hardcoded_figure_references(
    generated_sections: Dict[str, str],
    paper_plan: Any,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Repair hard-coded figure prose only when the section has one clear owner.

    Cross-section or multi-figure guesses are intentionally rejected by returning
    diagnostics for the validator to surface before compilation.
    """
    if not paper_plan:
        return generated_sections, []

    repaired = dict(generated_sections)
    diagnostics: List[str] = []

    for section in getattr(paper_plan, "sections", []) or []:
        section_type = str(getattr(section, "section_type", "") or "")
        content = repaired.get(section_type, "") or ""
        if not content:
            continue

        owner_figures = [
            str(getattr(placement, "figure_id", "") or "")
            for placement in (getattr(section, "figures", []) or [])
            if str(getattr(placement, "figure_id", "") or "")
        ]
        body = _strip_float_environments(_strip_latex_comments(content))
        matches = list(_HARDCODED_FIGURE_RE.finditer(body))
        if not matches:
            continue

        unique_owner = owner_figures[0] if len(set(owner_figures)) == 1 else ""
        if not unique_owner:
            repaired[section_type] = _remove_unowned_hardcoded_figure_references(content)
            continue

        def _replace(match: re.Match[str]) -> str:
            return f"Figure~\\ref{{{unique_owner}}}"

        # Apply to non-float prose. This keeps captions untouched while repairing
        # the common generated-body failure mode.
        stashed, float_blocks = _stash_figure_float_blocks(content)
        stashed = _HARDCODED_FIGURE_RE.sub(_replace, stashed)
        repaired[section_type] = _restore_figure_float_blocks(stashed, float_blocks)

    return repaired, diagnostics


def repair_non_owner_figure_references(
    generated_sections: Dict[str, str],
    paper_plan: Any,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Remove prose references to assigned figures from non-owner sections.

    Figure placement is a semantic contract, not just a float-location hint. A
    result figure assigned to Results should not be introduced by Introduction
    prose because that revives the original result-figure-in-intro failure mode.
    """
    if not paper_plan:
        return generated_sections, []

    figure_owner: Dict[str, str] = {}
    for section in getattr(paper_plan, "sections", []) or []:
        section_type = str(getattr(section, "section_type", "") or "")
        for placement in getattr(section, "figures", []) or []:
            figure_id = str(getattr(placement, "figure_id", "") or "")
            if figure_id and section_type:
                figure_owner.setdefault(figure_id, section_type)

    if not figure_owner:
        return generated_sections, []

    repaired = dict(generated_sections)
    diagnostics: List[str] = []
    ref_re = re.compile(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}")

    def _repair_reference_phrase(content: str, figure_id: str) -> str:
        cmd_ref = rf"\\(?:ref|autoref|cref|Cref)\{{{re.escape(figure_id)}\}}"
        figure_ref = rf"(?:Figure~)?{cmd_ref}"
        stashed, float_blocks = _stash_figure_float_blocks(content)
        stashed = re.sub(
            rf"\s*\(\s*(?:see\s+)?{figure_ref}\s*\)",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(
            rf",?\s+as\s+(?:illustrated|shown|depicted)\s+in\s+{figure_ref}",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(
            rf"\s+(?:see\s+)?{figure_ref}",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(r"\s+([,.;:])", r"\1", stashed)
        stashed = re.sub(r" {2,}", " ", stashed)
        return _restore_figure_float_blocks(stashed, float_blocks)

    for section in getattr(paper_plan, "sections", []) or []:
        section_type = str(getattr(section, "section_type", "") or "")
        content = repaired.get(section_type, "") or ""
        if not section_type or not content:
            continue

        section_owned = {
            str(getattr(placement, "figure_id", "") or "")
            for placement in getattr(section, "figures", []) or []
        }
        section_owned.discard("")
        body = _strip_float_environments(_strip_latex_comments(content))
        non_owner_ids = sorted({
            fig_id
            for fig_id in ref_re.findall(body)
            if fig_id in figure_owner and fig_id not in section_owned
        })
        if not non_owner_ids:
            continue

        for fig_id in non_owner_ids:
            content = _repair_reference_phrase(content, fig_id)

        body_after = _strip_float_environments(_strip_latex_comments(content))
        remaining = sorted({
            fig_id
            for fig_id in ref_re.findall(body_after)
            if fig_id in figure_owner and fig_id not in section_owned
        })
        if remaining:
            diagnostics.append(
                f"Section '{section_type}' references assigned figure(s) outside owner section: "
                + ", ".join(remaining)
            )
        repaired[section_type] = content

    return repaired, diagnostics


_FLOAT_MARKER_RE = re.compile(r"\[FLOAT:([^\]]+)\]")


def repair_float_markers(
    generated_sections: Dict[str, str],
    paper_plan: Any,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Resolve writer/reviewer ``[FLOAT:...]`` markers before LaTeX compilation.

    Paragraph-stage float injection can be bypassed by later section-level
    revisions. At the deterministic compile boundary, an owned assigned figure
    marker becomes a label-based reference; markers to figures owned by other
    sections or unknown ids are removed rather than guessed.
    """
    if not paper_plan:
        return generated_sections, []

    repaired = dict(generated_sections)
    diagnostics: List[str] = []

    def _remove_orphaned_marker_phrase(content: str, marker: str) -> str:
        stashed, float_blocks = _stash_figure_float_blocks(content)
        escaped = re.escape(marker)
        stashed = re.sub(
            rf"\s*\(\s*(?:see\s+)?{escaped}\s*\)",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(
            rf",?\s+as\s+(?:illustrated|shown|depicted)\s+in\s+{escaped}",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(
            rf"\s+(?:see\s+)?{escaped}",
            "",
            stashed,
            flags=re.IGNORECASE,
        )
        stashed = re.sub(escaped, "", stashed)
        stashed = re.sub(r"\s+([,.;:])", r"\1", stashed)
        stashed = re.sub(r" {2,}", " ", stashed)
        return _restore_figure_float_blocks(stashed, float_blocks)

    for section in getattr(paper_plan, "sections", []) or []:
        section_type = str(getattr(section, "section_type", "") or "")
        content = repaired.get(section_type, "") or ""
        if not section_type or not content:
            continue
        section_owned = {
            str(getattr(placement, "figure_id", "") or "")
            for placement in getattr(section, "figures", []) or []
        }
        section_owned.discard("")

        def _replace(match: re.Match[str]) -> str:
            float_id = match.group(1)
            if float_id in section_owned:
                return f"Figure~\\ref{{{float_id}}}"
            return match.group(0)

        content = _FLOAT_MARKER_RE.sub(_replace, content)
        for marker_id in sorted(set(_FLOAT_MARKER_RE.findall(content))):
            content = _remove_orphaned_marker_phrase(content, f"[FLOAT:{marker_id}]")
        repaired[section_type] = content

        remaining = _FLOAT_MARKER_RE.findall(content)
        if remaining:
            diagnostics.append(
                f"Section '{section_type}' contains unresolved FLOAT marker(s): "
                + ", ".join(sorted(set(remaining)))
            )

    return repaired, diagnostics


def strip_code_path_references(
    generated_sections: Dict[str, str],
) -> Dict[str, str]:
    total_stripped = 0
    for section_type in list(generated_sections.keys()):
        content = generated_sections[section_type]
        original = content
        content = re.sub(
            r'(?:,?\s*(?:implemented|defined|derived|found|coded|written|specified|described)'
            r'\s+(?:in|from|within|via|using)\s+)?'
            r'\\texttt\{[^}]*(?:\.py|\.c|\.cc|\.cpp|\.R|\.jl|\.ipynb|code/)[^}]*\}',
            '',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(
            r'\s*\((?:derived\s+from|from|in|see)\s+\\texttt\{[^}]*(?:\.py|\.c|\.cpp|code/)[^}]*\}\)',
            '',
            content,
            flags=re.IGNORECASE,
        )
        content = re.sub(r'\s*,\s*,', ',', content)
        content = re.sub(r'  +', ' ', content)

        if content != original:
            total_stripped += 1
            generated_sections[section_type] = content

    if total_stripped > 0:
        print(f"[StripCodePaths] Cleaned code path references in {total_stripped} section(s)")
    return generated_sections


def normalize_float_placement(content: str) -> str:
    if not content:
        return content

    def _figure_float(match: re.Match[str]) -> str:
        env_name = match.group(1)
        return f"\\begin{{{env_name}}}[tbp]"

    content = re.sub(r'\\begin\{(figure\*?)\}\[h!?tbp\]', _figure_float, content)
    content = re.sub(r'\\begin\{figure\*?\}\[t\]', lambda m: m.group(0).replace('[t]', '[tbp]'), content)
    content = re.sub(r'\\begin\{table\*?\}\[t\]', lambda m: m.group(0).replace('[t]', '[htbp]'), content)
    return content


def _strip_latex_for_sentence(text: str) -> str:
    """Return compact text suitable for prose synthesis from a LaTeX list item."""
    text = re.sub(r"\\cite[tp]?\{[^}]*\}", "", text or "")
    text = re.sub(r"\\ref\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^}]*)\})?", r"\1", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .;:")


def _join_items_as_sentence(items: List[str]) -> str:
    """Join list items into one readable sentence fragment."""
    cleaned = [_strip_latex_for_sentence(item) for item in items]
    cleaned = [item for item in cleaned if item]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{'; '.join(cleaned[:-1])}; and {cleaned[-1]}"


def collapse_duplicate_introduction_contributions(content: str) -> str:
    """
    Keep Introduction to a single contribution list.

    Review rewrites can occasionally append a second complete introduction arc
    after an already terminal contribution list. When that happens, the first
    contribution list is kept and the duplicated tail is removed.
    """
    if not content or content.count(r"\begin{itemize}") < 2:
        return content

    itemize_pattern = re.compile(
        r"\\begin\{itemize\}.*?\\end\{itemize\}",
        flags=re.DOTALL,
    )
    matches = list(itemize_pattern.finditer(content))
    if len(matches) < 2:
        return content

    contribution_signal = re.compile(
        r"(main\s+contributions?|this\s+work\s+contributes|our\s+contributions?|"
        r"in\s+summary,\s+this\s+work\s+contributes)",
        flags=re.IGNORECASE,
    )
    first = matches[0]
    second = matches[1]
    first_lead = content[max(0, first.start() - 240):first.start()]
    duplicated_tail = content[first.end():second.start()]
    second_lead = content[max(first.end(), second.start() - 240):second.start()]
    if (
        contribution_signal.search(first_lead)
        and (
            contribution_signal.search(duplicated_tail)
            or contribution_signal.search(second_lead)
        )
    ):
        return content[:first.end()].strip()
    return content


def proseify_conclusion_itemize(content: str) -> str:
    """
    Convert itemized conclusion summaries into prose.

    The standalone conclusion prompt asks for one paragraph, but plans may also
    create a ``Conclusion`` subsection inside a body discussion section. This
    guard prevents bullet-list conclusions in either location.
    """
    if not content or r"\begin{itemize}" not in content:
        return content

    itemize_pattern = re.compile(
        r"(?P<label>(?:[^\n]*?(?:contributes?|contributions?|in summary)[^\n]*?\n)?)"
        r"\\begin\{itemize\}(?P<body>.*?)\\end\{itemize\}",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        items = re.findall(r"\\item\s*(.+?)(?=\\item|$)", match.group("body"), flags=re.DOTALL)
        sentence = _join_items_as_sentence(items)
        if not sentence:
            return ""
        label = re.sub(r"\s+", " ", match.group("label") or "").strip()
        if not label:
            return f"In summary, this work contributes {sentence}."
        label = label.rstrip(": ")
        if re.search(r"contributes?\s*$", label, flags=re.IGNORECASE):
            return f"{label} {sentence}."
        return f"{label}: {sentence}."

    return itemize_pattern.sub(replace, content)


def normalize_narrative_section_shapes(
    generated_sections: Dict[str, str],
) -> Dict[str, str]:
    """
    Enforce high-level narrative shape for generated paper prose.

    This is intentionally narrow and deterministic: it fixes known structural
    failures without rewriting scientific content.
    """
    normalized = dict(generated_sections)
    for section_type, content in list(normalized.items()):
        if section_type == "introduction":
            content = collapse_duplicate_introduction_contributions(content)
        if section_type == "conclusion" or re.search(
            r"\\(?:sub)?section\{[^}]*conclusion[^}]*\}",
            content or "",
            flags=re.IGNORECASE,
        ):
            content = proseify_conclusion_itemize(content)
        normalized[section_type] = content
    return normalized


def collect_typesetter_figure_ids(
    generated_sections: Dict[str, str],
    figures: Optional[List["FigureSpec"]],
    figure_paths: Optional[Dict[str, str]],
) -> List[str]:
    ids: set[str] = set()
    for fig in (figures or []):
        if getattr(fig, "id", None):
            ids.add(str(fig.id))
    for key in (figure_paths or {}).keys():
        if key:
            ids.add(str(key))

    pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
    for content in generated_sections.values():
        for raw in re.findall(pattern, content or ""):
            token = str(raw).strip()
            if not token:
                continue
            if "/" in token or token.startswith(".") or token.endswith((".png", ".jpg", ".jpeg", ".pdf", ".svg")):
                continue
            ids.add(token)
    return sorted(ids)


def validate_assigned_figure_labels_and_refs(
    generated_sections: Dict[str, str],
    paper_plan: Any,
    figures: Optional[List["FigureSpec"]],
) -> List[str]:
    """
    Validate that planned figure assignments have a concrete writer usage path.

    This runs before typesetting, so it checks labels and section-level reference
    contracts rather than rewritten includegraphics paths.
    """
    known_figures = {str(getattr(fig, "id", "") or "") for fig in (figures or [])}
    known_figures = {fig_id for fig_id in known_figures if fig_id}
    errors: List[str] = []
    for section in getattr(paper_plan, "sections", []) or []:
        section_type = str(getattr(section, "section_type", "") or "")
        section_content = generated_sections.get(section_type, "") or ""
        body_content = _strip_float_environments(_strip_latex_comments(section_content))
        content_refs = set(re.findall(r"\\(?:ref|autoref|cref|Cref)\{([^}]+)\}", body_content))
        float_markers = _FLOAT_MARKER_RE.findall(body_content)
        if float_markers:
            errors.append(
                f"Section '{section_type}' contains unresolved FLOAT marker(s): "
                + ", ".join(sorted(set(float_markers)))
            )
        hardcoded_refs = _HARDCODED_FIGURE_RE.findall(body_content)
        if hardcoded_refs:
            refs = [f"Figure {num}" for num in sorted(set(hardcoded_refs))]
            errors.append(
                f"Section '{section_type}' contains hard-coded figure number reference(s): "
                + ", ".join(refs)
            )
        for placement in getattr(section, "figures", []) or []:
            figure_id = str(getattr(placement, "figure_id", "") or "")
            if not figure_id:
                continue
            if known_figures and figure_id not in known_figures:
                errors.append(
                    f"Figure '{figure_id}' is assigned to section '{section_type}' but is not defined in metadata."
                )
            if figure_id not in content_refs:
                errors.append(
                    f"Figure '{figure_id}' is assigned to section '{section_type}' without a generated label-based prose reference."
                )
    return errors


def _column_format_from_policy(
    *,
    template_guide: Any = None,
    column_format: Optional[str] = None,
) -> str:
    fmt = (column_format or getattr(template_guide, "column_format", None) or "single")
    fmt = str(fmt).strip().lower()
    return "double" if fmt == "double" else "single"


def validate_figure_layout_contract(
    generated_sections: Dict[str, str],
    paper_plan: Any,
    figures: Optional[List["FigureSpec"]],
    *,
    template_guide: Any = None,
    column_format: Optional[str] = None,
) -> List[str]:
    """
    Validate figure environment/width contracts before LaTeX compilation.

    The assignment/ref validator checks semantic usage. This validator checks
    template-scoped float shape so a double-column `figure` cannot carry
    text-width graphics and single-column templates do not receive `figure*`.
    """
    fmt = _column_format_from_policy(template_guide=template_guide, column_format=column_format)
    wide_figures = {
        str(fid) for fid in (getattr(paper_plan, "wide_figures", []) or [])
        if str(fid)
    }
    for fig in figures or []:
        if getattr(fig, "wide", False) and getattr(fig, "id", None):
            wide_figures.add(str(fig.id))

    errors: List[str] = []
    block_re = re.compile(
        r"\\begin\{(figure\*?)\}(?:\[[^\]]*\])?(?P<body>.*?)\\end\{\1\}",
        re.DOTALL,
    )
    label_re = re.compile(r"\\label\{([^}]+)\}")
    width_re = re.compile(r"width\s*=\s*([^,\]\s]+)")

    for section_type, content in (generated_sections or {}).items():
        for match in block_re.finditer(content or ""):
            env_name = match.group(1)
            body = match.group("body") or ""
            label_match = label_re.search(body)
            label = label_match.group(1) if label_match else "<unlabelled>"
            width_match = width_re.search(body)
            width = width_match.group(1) if width_match else ""
            uses_textwidth = "\\textwidth" in width
            uses_line_or_col = "\\linewidth" in width or "\\columnwidth" in width

            if fmt == "single" and env_name == "figure*":
                errors.append(
                    f"Figure '{label}' in section '{section_type}' uses figure* in a single-column template."
                )
            if env_name == "figure" and uses_textwidth:
                errors.append(
                    f"Figure '{label}' in section '{section_type}' is single-column figure with text-width graphic ({width})."
                )
            if fmt == "double" and label in wide_figures and env_name != "figure*":
                if not uses_line_or_col:
                    errors.append(
                        f"Wide figure '{label}' in section '{section_type}' was downgraded without column-safe width."
                    )

    return errors


def validate_table_layout_contract(
    generated_sections: Dict[str, str],
    paper_plan: Any,
    tables: Optional[List["TableSpec"]],
    *,
    template_guide: Any = None,
    column_format: Optional[str] = None,
) -> List[str]:
    """
    Validate deterministic table layout contracts before final compilation.

    This mirrors ``validate_figure_layout_contract`` while delegating the table
    evidence model to the shared table converter so deterministic, preview, and
    final-review stages use the same payload shape.
    """
    fmt = _column_format_from_policy(
        template_guide=template_guide,
        column_format=column_format,
    )
    if fmt != "double":
        return []

    from ..shared.table_converter import validate_table_layout_contract as _validate

    return _validate(
        generated_sections,
        paper_plan=paper_plan,
        tables=tables,
    )


def detect_contextless_figure_pages(
    pdf_path: Optional[str],
    latex_dir: Optional[str],
    figure_ids: List[str],
) -> List[str]:
    """
    Warn when a labelled figure appears on a sparse PDF page.

    This is intentionally heuristic and warning-only. It uses LaTeX aux label
    pages plus extracted PDF text to find pages that appear to contain little
    beyond a figure caption/header/footer.
    """
    if not pdf_path or not latex_dir or not figure_ids:
        return []

    aux_path = Path(latex_dir) / "main.aux"
    pdf = Path(pdf_path)
    if not aux_path.exists() or not pdf.exists():
        return []

    try:
        aux_text = aux_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    label_pages: Dict[str, int] = {}
    for fig_id in figure_ids:
        pattern = re.compile(r"\\newlabel\{" + re.escape(fig_id) + r"\}\{\{[^{}]*\}\{(\d+)\}")
        match = pattern.search(aux_text)
        if match:
            label_pages[fig_id] = int(match.group(1))

    if not label_pages:
        return []

    try:
        import fitz  # type: ignore
    except Exception:
        return []

    warnings: List[str] = []
    try:
        doc = fitz.open(str(pdf))
    except Exception:
        return []

    try:
        for fig_id, page_num in sorted(label_pages.items(), key=lambda item: item[1]):
            if page_num < 1 or page_num > len(doc):
                continue
            text = doc[page_num - 1].get_text("text") or ""
            words = re.findall(r"[A-Za-z][A-Za-z0-9-]*", text)
            body_words = [
                word for word in words
                if word.lower() not in {"figure", "fig", "table", "page"}
            ]
            if len(body_words) <= 45 and re.search(r"\bFigure\s+\d+", text):
                warnings.append(
                    f"Figure '{fig_id}' appears on page {page_num} with little surrounding body-text context."
                )
    finally:
        doc.close()

    return warnings


def generate_bib_file(references: List[Dict[str, Any]]) -> str:
    bib_entries = []
    for ref in references:
        if ref.get("bibtex"):
            bib_entries.append(ref["bibtex"])
        else:
            ref_id = ref.get("ref_id", "unknown")
            title = ref.get("title", "Unknown Title")
            authors = ref.get("authors", "Unknown Author")
            year = ref.get("year", 2024)
            entry = f"""@article{{{ref_id},
  title = {{{title}}},
  author = {{{authors}}},
  year = {{{year}}},
}}"""
            bib_entries.append(entry)
    return "\n\n".join(bib_entries)


def escape_latex(text: str) -> str:
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def validate_main_tex_structure(main_tex_path: Path) -> List[str]:
    if not main_tex_path.exists():
        return [f"main.tex not found: {main_tex_path}"]
    try:
        text = main_tex_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [f"cannot read main.tex: {e}"]

    errors: List[str] = []
    title_match = re.search(
        r'\\(?:icml)?title(?:\[[^\]]*\])?\{([^}]*)\}',
        text,
        flags=re.DOTALL,
    )
    if not title_match or not title_match.group(1).strip():
        errors.append("missing_or_empty_title")

    abstract_cmd = re.search(r'\\abstract\{([^}]*)\}', text, flags=re.DOTALL)
    abstract_env = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, flags=re.DOTALL)
    abstract_text = abstract_cmd.group(1) if abstract_cmd else abstract_env.group(1) if abstract_env else ""
    if not abstract_text.strip():
        errors.append("missing_or_empty_abstract")

    return errors
