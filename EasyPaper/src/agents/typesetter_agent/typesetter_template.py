"""
Template analysis and content-injection helpers for TypesetterAgent.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .models import BibEntry, TemplateConfig, TemplateStructureProfile
from .typesetter_sections import normalize_abstract


def find_brace_end(text: str, open_brace_pos: int) -> int:
    depth = 0
    i = open_brace_pos
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return open_brace_pos + 1


def find_bracket_end(text: str, open_bracket_pos: int) -> int:
    depth = 0
    i = open_bracket_pos
    while i < len(text):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return open_bracket_pos + 1


def validate_compiled_tex_structure(compiled_tex: str) -> List[str]:
    errors: List[str] = []

    title_match = re.search(
        r"\\(?:icml)?title(?:\[[^\]]*\])?\{([^}]*)\}",
        compiled_tex,
        flags=re.DOTALL,
    )
    if not title_match or not title_match.group(1).strip():
        errors.append("missing_or_empty_title")

    abstract_cmd = re.search(r"\\abstract\{([^}]*)\}", compiled_tex, flags=re.DOTALL)
    abstract_env = re.search(
        r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
        compiled_tex,
        flags=re.DOTALL,
    )
    abstract_text = ""
    if abstract_cmd:
        abstract_text = abstract_cmd.group(1)
    elif abstract_env:
        abstract_text = abstract_env.group(1)
    if not abstract_text.strip():
        errors.append("missing_or_empty_abstract")

    return errors


def ensure_maketitle_present(
    text: str,
    profile: Optional[TemplateStructureProfile] = None,
) -> str:
    if profile is not None and not profile.needs_maketitle:
        return text

    if "\\maketitle" in text or "\\begin{document}" not in text:
        return text

    anchor = text.index("\\begin{document}") + len("\\begin{document}")

    abstract_cmd_match = re.search(r"\\abstract\{", text)
    if abstract_cmd_match:
        end = find_brace_end(text, abstract_cmd_match.start() + len("\\abstract"))
        anchor = max(anchor, end)
    else:
        abstract_env_match = re.search(
            r"\\begin\{abstract\}.*?\\end\{abstract\}",
            text,
            flags=re.DOTALL,
        )
        if abstract_env_match:
            anchor = max(anchor, abstract_env_match.end())

    return text[:anchor] + "\n\n\\maketitle" + text[anchor:]


def replace_all_authors(text: str, new_author: str) -> str:
    first_pos = None
    i = 0
    regions_to_remove = []
    while i < len(text):
        match = re.search(r"\\author\*?", text[i:])
        if not match:
            break
        start = i + match.start()
        line_start = text.rfind("\n", 0, start) + 1
        if re.match(r"^\s*%", text[line_start:start]):
            i = start + len(match.group(0))
            continue
        pos = start + match.end() - match.start()
        if pos < len(text) and text[pos] == "[":
            bracket_depth = 1
            pos += 1
            while pos < len(text) and bracket_depth > 0:
                if text[pos] == "[":
                    bracket_depth += 1
                elif text[pos] == "]":
                    bracket_depth -= 1
                pos += 1
        if pos < len(text) and text[pos] == "{":
            brace_depth = 1
            pos += 1
            while pos < len(text) and brace_depth > 0:
                if text[pos] == "{":
                    brace_depth += 1
                elif text[pos] == "}":
                    brace_depth -= 1
                pos += 1
            if first_pos is None:
                first_pos = start
            regions_to_remove.append((start, pos))
        i = pos if pos > start else start + 1

    if not regions_to_remove:
        title_match = re.search(
            r"\\(?:icml)?title(?:\[[^\]]*\])?\{[^}]*\}",
            text,
            flags=re.DOTALL,
        )
        insertion = f"\n\\author{{{new_author}}}\n"
        if title_match:
            insert_pos = title_match.end()
            return text[:insert_pos] + insertion + text[insert_pos:]
        return text

    for start, end in reversed(regions_to_remove):
        text = text[:start] + text[end:]

    replacement = f"\\author{{{new_author}}}"
    return text[:first_pos] + replacement + text[first_pos:]


def replace_abstract_command(text: str, new_content: str) -> str:
    pattern_start = "\\abstract{"
    start_idx = text.find(pattern_start)
    if start_idx == -1:
        return text
    brace_count = 1
    content_start = start_idx + len(pattern_start)
    i = content_start
    while i < len(text) and brace_count > 0:
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
        i += 1
    if brace_count == 0:
        return text[:start_idx] + f"\\abstract{{{new_content}}}" + text[i:]
    return text


def remove_abstract_command(text: str) -> str:
    pattern_start = "\\abstract{"
    start_idx = text.find(pattern_start)
    if start_idx == -1:
        return text
    brace_count = 1
    i = start_idx + len(pattern_start)
    while i < len(text) and brace_count > 0:
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
        i += 1
    if brace_count == 0:
        return text[:start_idx] + text[i:]
    return text


def extract_bib_commands(text: str) -> str:
    bib_commands = ""
    bib_style_match = re.search(r"\\bibliographystyle\{[^}]+\}", text)
    bib_file_match = re.search(r"\\bibliography\{[^}]+\}", text)
    printbib_match = re.search(r"\\printbibliography", text)
    if bib_style_match:
        bib_commands += bib_style_match.group(0) + "\n"
    if bib_file_match:
        bib_commands += "\\bibliography{references}\n"
    elif printbib_match:
        bib_commands += "\\printbibliography\n"
    return bib_commands


def analyze_template_structure(template_tex: str) -> TemplateStructureProfile:
    title_command = "\\title"
    if re.search(r"\\icmltitle\b", template_tex):
        title_command = "\\icmltitle"

    author_system = "standard"
    if re.search(r"\\begin\{icmlauthorlist\}", template_tex):
        author_system = "icml"
    elif re.search(r"\\IEEEauthorblockN\b", template_tex):
        author_system = "ieee"
    elif re.search(r"\\author\[.*?\]\{.*?\\fnm\{", template_tex, re.DOTALL):
        author_system = "nature"
    elif re.search(r"\\documentclass.*\{acmart\}", template_tex):
        author_system = "acm"

    abstract_format = "none"
    if re.search(r"\\begin\{abstract\}", template_tex):
        abstract_format = "environment"
    elif re.search(r"(?<!\\begin\{)\\abstract\{", template_tex):
        abstract_format = "command"

    has_twocolumn_bracket = bool(re.search(r"\\twocolumn\s*\[", template_tex))

    abstract_inside_twocolumn = False
    if has_twocolumn_bracket:
        tc_match = re.search(r"\\twocolumn\s*\[", template_tex)
        if tc_match:
            bracket_start = tc_match.end() - 1
            bracket_end = find_bracket_end(template_tex, bracket_start)
            bracket_region = template_tex[bracket_start:bracket_end]
            if "\\begin{abstract}" in bracket_region or "\\abstract{" in bracket_region:
                abstract_inside_twocolumn = True

    needs_maketitle = True
    if has_twocolumn_bracket or author_system == "icml":
        needs_maketitle = False

    needs_date = bool(re.search(r"\\date\{", template_tex))

    return TemplateStructureProfile(
        title_command=title_command,
        author_system=author_system,
        abstract_format=abstract_format,
        abstract_inside_twocolumn=abstract_inside_twocolumn,
        needs_maketitle=needs_maketitle,
        needs_date=needs_date,
        has_twocolumn_bracket=has_twocolumn_bracket,
    )


def promote_wide_tables(content: str, column_threshold: int = 5) -> str:
    env_pattern = re.compile(
        r"\\begin\{table\}(.*?)\\end\{table\}",
        flags=re.DOTALL,
    )

    def _check_and_promote(match: re.Match) -> str:
        block = match.group(0)
        tabular_match = re.search(
            r"\\begin\{tabular\}.*?\n(.*?)\n",
            block,
            flags=re.DOTALL,
        )
        if not tabular_match:
            return block
        first_row = tabular_match.group(1)
        col_count = first_row.count("&") + 1
        if col_count > column_threshold:
            return block.replace("\\begin{table}", "\\begin{table*}", 1).replace(
                "\\end{table}",
                "\\end{table*}",
                1,
            )
        return block

    return env_pattern.sub(_check_and_promote, content)


def smart_inject_content(
    template_content: str,
    sections: Dict[str, str],
    template_config: TemplateConfig,
    bib_entries: List[BibEntry],
    profile: Optional[TemplateStructureProfile] = None,
) -> str:
    if profile is None:
        profile = analyze_template_structure(template_content)

    result = template_content

    if template_config.paper_title:
        title = template_config.paper_title
        result = re.sub(
            r"\\title(?:\[[^\]]*\])?\{[^}]*\}",
            lambda _m: f"\\title{{{title}}}",
            result,
        )

        def replace_icmltitle(text: str, new_title: str) -> str:
            pattern_start = "\\icmltitle{"
            start_idx = text.find(pattern_start)
            if start_idx == -1:
                return text
            brace_count = 1
            content_start = start_idx + len(pattern_start)
            i = content_start
            while i < len(text) and brace_count > 0:
                if text[i] == "{":
                    brace_count += 1
                elif text[i] == "}":
                    brace_count -= 1
                i += 1
            if brace_count == 0:
                return text[:start_idx] + f"\\icmltitle{{{new_title}}}" + text[i:]
            return text

        result = replace_icmltitle(result, title)
        result = re.sub(
            r"\\icmltitlerunning\{[^}]*\}",
            lambda _m: (
                f"\\icmltitlerunning{{{title[:50]}...}}"
                if len(title) > 50
                else f"\\icmltitlerunning{{{title}}}"
            ),
            result,
        )

    authors = template_config.paper_authors or "EasyPaper"

    if profile.author_system in ("icml", "ieee"):
        pass
    elif profile.author_system == "nature":
        result = replace_all_authors(result, authors)
        result = re.sub(r"\\affil\*?\[[^\]]*\]\{[^}]*\}", "", result)
        result = re.sub(r"\\affiliation\{[^}]*\}", "", result)
        result = re.sub(r"\\institute\{[^}]*\}", "", result)
        result = re.sub(r"\\equalcont\{[^}]*\}", "", result)
        result = re.sub(r"\\email\{[^}]*\}", "", result)
        result = re.sub(
            r"^[,\s]*\\org(?:name|address|div)\{[^}]*(?:\{[^}]*\}[^}]*)*\}[^\n]*$",
            "",
            result,
            flags=re.MULTILINE,
        )
    else:
        result = replace_all_authors(result, authors)

    result = re.sub(r"\n{3,}", "\n\n", result)

    abstract_content = sections.get("abstract", "")
    if abstract_content:
        abstract_content = normalize_abstract(abstract_content)
        abstract_content = re.sub(r"(?<!\\)%", r"\\%", abstract_content)

        has_env = "\\begin{abstract}" in result
        has_cmd = bool(re.search(r"(?<!\\begin\{)\\abstract\{", result))

        if has_cmd:
            result = replace_abstract_command(result, abstract_content)

        if has_env:
            result = re.sub(
                r"\\begin\{abstract\}.*?\\end\{abstract\}",
                lambda _m: f"\\begin{{abstract}}\n{abstract_content}\n\\end{{abstract}}",
                result,
                flags=re.DOTALL,
            )
            if has_cmd:
                result = remove_abstract_command(result)

        if not has_env and not has_cmd and "\\maketitle" in result:
            result = result.replace(
                "\\maketitle",
                f"\\maketitle\n\n\\begin{{abstract}}\n{abstract_content}\n\\end{{abstract}}",
            )

    body_content = sections.get("body", "")
    if body_content:
        body_content = re.sub(r"(?<!\\)%", r"\\%", body_content)
        body_content = re.sub(r"\\% === Section: \w+ ===\n?", "", body_content)

        bib_commands = extract_bib_commands(result)

        if "\\end{abstract}" in result and "\\end{document}" in result:
            result = re.sub(
                r"(\\end\{abstract\}).*?(\\end\{document\})",
                lambda m: f"{m.group(1)}\n\n{body_content}\n\n{bib_commands}\n{m.group(2)}",
                result,
                flags=re.DOTALL,
            )
        elif "\\maketitle" in result and "\\end{document}" in result:
            abstract_cmd_match = re.search(r"\\abstract\{", result)
            if abstract_cmd_match:
                anchor_end = find_brace_end(result, abstract_cmd_match.start() + len("\\abstract"))
            else:
                anchor_end = result.index("\\maketitle") + len("\\maketitle")

            end_doc_match = re.search(r"\\end\{document\}", result)
            if end_doc_match:
                result = (
                    result[:anchor_end]
                    + f"\n\n{body_content}\n\n{bib_commands}\n"
                    + result[end_doc_match.start():]
                )
        else:
            if "\\maketitle" not in result:
                result = result.replace(
                    "\\begin{document}",
                    f"\\begin{{document}}\n\n\\maketitle\n\n{body_content}",
                )
            else:
                result = result.replace(
                    "\\begin{document}",
                    f"\\begin{{document}}\n\n{body_content}",
                )

    if bib_entries and "\\bibliography" not in result and "\\printbibliography" not in result:
        if "icml" in result.lower() or "natbib" in result.lower():
            bib_style = "icml2026"
        elif "neurips" in result.lower() or "nips" in result.lower():
            bib_style = "plainnat"
        else:
            bib_style = "plainnat"

        bib_command = f"\\bibliographystyle{{{bib_style}}}\n\\bibliography{{references}}\n"
        result = result.replace(
            "\\end{document}",
            f"\n{bib_command}\n\\end{{document}}",
        )

    return ensure_maketitle_present(result, profile=profile)
