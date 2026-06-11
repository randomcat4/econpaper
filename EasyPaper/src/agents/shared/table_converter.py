"""
Table Converter - Convert any readable format to LaTeX tables
- **Description**:
    - Converts CSV, Markdown, plain text tables to LaTeX
    - Uses LLM for intelligent format detection and conversion
    - Handles special characters and academic table formatting
    - Pre-analyzes table structure for layout-aware conversion
    - Post-validates LLM output for data fidelity
"""
import csv
import hashlib
import io
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING, Tuple

from .asset_paths import resolve_asset_path

if TYPE_CHECKING:
    from ..metadata_agent.models import TableSpec

logger = logging.getLogger("uvicorn.error")


# ═══════════════════════════════════════════════════════════════════════════
# TableStructure — result of structural analysis
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TableStructure:
    """
    Structural metadata extracted from raw table content before LLM conversion.
    - **Description**:
        - Captures row/col counts, header structure, width estimates,
          and sub-group rows for layout-aware LaTeX generation.
    """
    col_count: int = 0
    data_row_count: int = 0
    has_multirow_header: bool = False
    max_cell_width: int = 0
    estimated_row_width: float = 0.0
    estimated_width_class: str = "narrow"
    header_levels: List[List[str]] = field(default_factory=list)
    subgroup_row_count: int = 0
    detected_format: str = "unknown"


# ═══════════════════════════════════════════════════════════════════════════
# TableAnalyzer — pure-code structural pre-processing
# ═══════════════════════════════════════════════════════════════════════════

class TableAnalyzer:
    """
    Analyze CSV/Markdown table content to extract structural metadata.
    - **Description**:
        - Detects format (CSV vs Markdown) automatically.
        - Parses hierarchical (dot-separated) headers.
        - Counts rows, columns, sub-group divider rows.
        - Estimates rendered width class for layout decisions.
    """

    # Width thresholds: total estimated char-width of one row
    _WIDTH_THRESHOLDS = {
        "narrow": 40,
        "medium": 80,
        "wide": 140,
    }

    @classmethod
    def analyze(cls, content: str) -> TableStructure:
        """
        Analyze raw table content and return structural metadata.
        - **Args**:
            - `content` (str): Raw CSV or Markdown table text.
        - **Returns**:
            - `TableStructure`: Extracted structural information.
        """
        content = content.strip()
        if not content:
            return TableStructure()

        fmt = cls._detect_format(content)
        if fmt == "markdown":
            return cls._analyze_markdown(content)
        return cls._analyze_csv(content)

    @staticmethod
    def _detect_format(content: str) -> str:
        """Heuristic: if first non-empty line starts with '|', it's Markdown."""
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("|"):
                return "markdown"
            return "csv"
        return "csv"

    @classmethod
    def _analyze_csv(cls, content: str) -> TableStructure:
        """Parse CSV content and build TableStructure."""
        reader = csv.reader(io.StringIO(content))
        rows: List[List[str]] = []
        for row in reader:
            rows.append(row)

        if not rows:
            return TableStructure(detected_format="csv")

        header_row = rows[0]
        col_count = len(header_row)

        # Detect multi-level headers (dot-separated like "NoCaps (val).CIDEr")
        has_multirow = any("." in h and not h.endswith(".") for h in header_row)
        # Also check for repeated sub-header pattern like "X.X"
        if not has_multirow:
            has_multirow = any(
                "." in h and len(h.split(".")) >= 2 and len(h.split(".")[0]) > 1
                for h in header_row
            )

        # Build header levels
        header_levels: List[List[str]] = []
        if has_multirow:
            max_depth = max(len(h.split(".")) for h in header_row)
            for level in range(max_depth):
                level_headers = []
                for h in header_row:
                    parts = h.split(".")
                    if level < len(parts):
                        level_headers.append(parts[level].strip())
                    else:
                        level_headers.append("")
                header_levels.append(level_headers)
        else:
            header_levels = [header_row]

        # Analyze data rows (skip header)
        data_rows = rows[1:]
        subgroup_count = 0
        actual_data_rows = 0
        max_cell_w = max((len(h) for h in header_row), default=0)

        for row in data_rows:
            # Sub-group row: first cell has content, most others are empty
            non_empty = sum(1 for c in row if c.strip())
            if len(row) > 2 and non_empty <= 2 and row[0].strip():
                subgroup_count += 1
            else:
                actual_data_rows += 1

            for cell in row:
                max_cell_w = max(max_cell_w, len(cell.strip()))

        # Estimate width: average cell width * col_count
        total_cells = sum(len(r) for r in rows)
        total_chars = sum(len(c) for r in rows for c in r)
        avg_cell_w = total_chars / max(total_cells, 1)
        row_width = avg_cell_w * col_count

        width_class = cls._classify_width(row_width, col_count)

        return TableStructure(
            col_count=col_count,
            data_row_count=actual_data_rows,
            has_multirow_header=has_multirow,
            max_cell_width=max_cell_w,
            estimated_row_width=row_width,
            estimated_width_class=width_class,
            header_levels=header_levels,
            subgroup_row_count=subgroup_count,
            detected_format="csv",
        )

    @classmethod
    def _analyze_markdown(cls, content: str) -> TableStructure:
        """Parse Markdown table and build TableStructure."""
        lines = [l.strip() for l in content.strip().splitlines() if l.strip()]

        # Filter out separator lines (e.g. |---|---|)
        data_lines = []
        header_line = None
        for i, line in enumerate(lines):
            cleaned = line.strip("|").strip()
            if re.match(r'^[\s\-:|]+$', cleaned):
                continue
            if header_line is None:
                header_line = line
            else:
                data_lines.append(line)

        if header_line is None:
            return TableStructure(detected_format="markdown")

        headers = [h.strip() for h in header_line.strip("|").split("|")]
        col_count = len(headers)
        max_cell_w = max((len(h) for h in headers), default=0)

        for line in data_lines:
            cells = [c.strip() for c in line.strip("|").split("|")]
            for c in cells:
                max_cell_w = max(max_cell_w, len(c))

        has_multirow = any("." in h and not h.endswith(".") for h in headers)
        header_levels = [headers]

        avg_w = sum(len(h) for h in headers) / max(len(headers), 1)
        row_width = avg_w * col_count
        width_class = cls._classify_width(row_width, col_count)

        return TableStructure(
            col_count=col_count,
            data_row_count=len(data_lines),
            has_multirow_header=has_multirow,
            max_cell_width=max_cell_w,
            estimated_row_width=row_width,
            estimated_width_class=width_class,
            header_levels=header_levels,
            subgroup_row_count=0,
            detected_format="markdown",
        )

    @classmethod
    def _classify_width(cls, row_width: float, col_count: int) -> str:
        """
        Classify table width based on estimated row character width and column count.
        - **Description**:
            - Uses both character width and column count for classification.
            - A 14-col table is always at least "wide" regardless of cell widths.
        """
        if col_count >= 10 or row_width >= cls._WIDTH_THRESHOLDS["wide"]:
            return "very_wide"
        if col_count >= 8 or row_width >= cls._WIDTH_THRESHOLDS["medium"]:
            return "wide"
        if col_count >= 5 or row_width >= cls._WIDTH_THRESHOLDS["narrow"]:
            return "medium"
        return "narrow"


# Legacy prompt kept for backward compatibility
TABLE_CONVERSION_PROMPT = """You are an expert LaTeX typesetter. Convert the following table data into a properly formatted LaTeX table.

## Table Information
- **Label**: {label}
- **Caption**: {caption}

## Table Data (in any format)
```
{content}
```

## Requirements
1. Generate a complete LaTeX table environment with \\begin{{table}}...\\end{{table}}
2. Use \\centering for the table
3. Use booktabs style (\\toprule, \\midrule, \\bottomrule)
4. Include the caption and label
5. Use appropriate column alignment (l for text, c for short items, r for numbers)
6. If numbers represent best results, make them bold with \\textbf{{}}
7. Handle any special characters that need escaping in LaTeX
8. Use [t] or [h] for table placement

## Output
Output ONLY the LaTeX code, no explanations or markdown code blocks.
"""


# ═══════════════════════════════════════════════════════════════════════════
# Enhanced prompt builder — context-aware conversion
# ═══════════════════════════════════════════════════════════════════════════

def build_conversion_prompt(
    label: str,
    caption: str,
    content: str,
    structure: TableStructure,
    column_format: str = "double",
    return_max_tokens: bool = False,
) -> Any:
    """
    Build a context-aware LaTeX table conversion prompt.
    - **Description**:
        - Injects structural metadata (row/col counts, width class) into the prompt
          so the LLM produces faithful, layout-correct LaTeX.
        - Dynamically adjusts guidance for multi-level headers, wide tables,
          sub-group rows, and template column format.

    - **Args**:
        - `label` (str): LaTeX label for the table.
        - `caption` (str): Table caption.
        - `content` (str): Raw table data (CSV or Markdown).
        - `structure` (TableStructure): Pre-analyzed structural metadata.
        - `column_format` (str): Template column format ("single" or "double").
        - `return_max_tokens` (bool): If True, return (prompt, max_tokens) tuple.

    - **Returns**:
        - `str`: The formatted prompt, or `(str, int)` if return_max_tokens is True.
    """
    parts: List[str] = []

    caption = normalize_caption(caption)

    parts.append(
        "You are an expert LaTeX typesetter. Convert the following table data "
        "into a properly formatted LaTeX table.\n"
    )

    # -- Table metadata --
    parts.append(f"## Table Information")
    parts.append(f"- **Label**: {label}")
    parts.append(f"- **Caption**: {caption}")
    parts.append(f"- **Source data has {structure.col_count} columns and "
                 f"{structure.data_row_count} data rows**")
    parts.append("")

    # -- Raw data --
    parts.append("## Table Data")
    parts.append("```")
    parts.append(content.strip())
    parts.append("```")
    parts.append("")

    # -- Data fidelity rules --
    parts.append("## CRITICAL — Data Preservation Rules")
    parts.append(
        f"- You MUST include ALL rows ({structure.data_row_count} data rows) "
        f"and ALL columns ({structure.col_count} columns) from the source data."
    )
    parts.append("- Do NOT summarize, truncate, or omit any rows or columns.")
    parts.append("- Preserve all numeric values exactly as given.")
    parts.append("- Use '-' for missing/empty values.")
    parts.append("")

    # -- Layout rules based on structure --
    parts.append("## Layout Requirements")

    # Environment type and sizing
    is_wide = structure.estimated_width_class in ("wide", "very_wide")
    font_policy = _table_font_policy(
        col_count=structure.col_count,
        row_width=int(structure.estimated_row_width or 0),
        multicolumn_span=_MULTICOLUMN_WIDE_MIN_SPAN if structure.has_multirow_header else 0,
        env_name="table*" if column_format == "double" and is_wide else "table",
        expected_wide=(column_format == "double" and is_wide),
    )

    if column_format == "double" and is_wide:
        parts.append(
            f"- Use \\begin{{table*}}...\\end{{table*}} (spans both columns) "
            f"since this table has {structure.col_count} columns."
        )
        width_target = "\\textwidth"
        parts.append(
            f"- Wrap the tabular inside \\adjustbox{{max width={width_target},center}}{{...}} "
            "rather than \\resizebox. This caps overflow without enlarging "
            "low-density tables."
        )
        preferred_font = str(font_policy.get("preferred_command") or "")
        if preferred_font == "\\scriptsize":
            parts.append(
                "- Use \\scriptsize inside the table because deterministic "
                "density evidence indicates it is unlikely to fit otherwise."
            )
        elif preferred_font == "\\small":
            parts.append(
                "- Use \\small inside the table. Do NOT use \\scriptsize "
                "unless the table is too dense to fit after max-width guarding."
            )
    elif column_format == "double" and not is_wide:
        parts.append(
            "- Use \\begin{table}...\\end{table} (single column width)."
        )
    else:
        parts.append(
            "- Use \\begin{table}...\\end{table} with full page width."
        )

    parts.append("- Use \\centering for the table.")
    parts.append("- Use [htbp] for table placement.")
    parts.append("- Use booktabs style (\\toprule, \\midrule, \\bottomrule).")
    parts.append(f"- Include \\caption{{{caption}}} and \\label{{{label}}}.")
    parts.append(
        "- Use appropriate column alignment: l for text, c for short items, "
        "r for numbers."
    )
    parts.append(
        "- Handle any special characters (%, &, _, #, $, ~, ^) that need "
        "escaping in LaTeX."
    )
    parts.append("")

    # -- Multi-level header guidance --
    if structure.has_multirow_header:
        parts.append("## Multi-Level Header Handling")
        parts.append(
            "- The source data has hierarchical (dot-separated) column headers."
        )
        parts.append(
            "- Use \\multicolumn{n}{c}{Group Header} to merge cells for "
            "top-level header groups."
        )
        parts.append(
            "- Use \\cmidrule{start-end} to separate header groups visually."
        )
        if len(structure.header_levels) >= 2:
            top_groups = []
            seen = set()
            for h in structure.header_levels[0]:
                if h and h not in seen:
                    top_groups.append(h)
                    seen.add(h)
            parts.append(
                f"- Top-level groups detected: {', '.join(top_groups[:8])}"
            )
        parts.append("")

    # -- Sub-group rows --
    if structure.subgroup_row_count > 0:
        parts.append("## Sub-Group Row Handling")
        parts.append(
            f"- The table contains {structure.subgroup_row_count} sub-group "
            f"divider rows (rows where only the first cell has content)."
        )
        parts.append(
            "- Render each sub-group label spanning all columns using "
            "\\multicolumn{N}{l}{\\textit{Sub-group Name}}."
        )
        parts.append(
            "- Insert \\midrule before each sub-group divider for visual separation."
        )
        parts.append("")

    # -- Output --
    parts.append("## Output")
    parts.append(
        "Output ONLY the LaTeX code. No explanations, no markdown code blocks."
    )

    prompt = "\n".join(parts)

    # Dynamic max_tokens based on table size
    base_tokens = 1500
    per_row = 80
    per_col_extra = 50
    multirow_extra = 500 if structure.has_multirow_header else 0
    max_tokens = (
        base_tokens
        + structure.data_row_count * per_row
        + max(0, structure.col_count - 5) * per_col_extra
        + multirow_extra
    )
    max_tokens = min(max_tokens, 8000)

    if return_max_tokens:
        return prompt, max_tokens
    return prompt


# ═══════════════════════════════════════════════════════════════════════════
# ValidationResult & TableValidator — post-processing validation
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationResult:
    """
    Result of validating LLM-generated LaTeX table output.
    - **Description**:
        - Captures errors (hard failures) and warnings (soft issues).
        - `is_valid` is True only when there are zero errors.
    """
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


TABLE_SEVERITIES = {"blocking", "warning", "info"}
TABLE_ACTIONABILITIES = {
    "repairable_formatting",
    "restructure_candidate",
    "manual_review",
    "no_action",
}


def _new_table_review_payload(
    *,
    table_id: str,
    section_type: str = "",
    source_kind: str = "user_provided",
) -> Dict[str, Any]:
    """Return the canonical table-review payload used by table QA stages."""
    return {
        "table_id": table_id,
        "section_type": section_type,
        "source_kind": source_kind,
        "deterministic_evidence": {},
        "rendered_evidence": {},
        "span_decision": {
            "current_env": "",
            "recommended_env": "",
            "confidence": 0.0,
            "reason": "",
        },
        "typography_decision": {
            "current_commands": [],
            "recommended_commands": [],
            "confidence": 0.0,
            "exception_reason": "",
            "density_class": "",
            "scriptsize_justified": False,
        },
        "issues": [],
        "severity": "info",
        "actionability": "no_action",
        "restructure_candidate": False,
        "restructure_rationale": "",
        "final_action": "no_action",
    }


def _append_table_issue(
    payload: Dict[str, Any],
    *,
    issue_type: str,
    severity: str,
    message: str,
    evidence: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
    actionability: str = "repairable_formatting",
) -> None:
    severity = severity if severity in TABLE_SEVERITIES else "warning"
    actionability = (
        actionability if actionability in TABLE_ACTIONABILITIES else "manual_review"
    )
    payload.setdefault("issues", []).append(
        {
            "type": issue_type,
            "severity": severity,
            "message": message,
            "evidence": evidence or {},
            "confidence": confidence,
        }
    )
    if severity == "blocking":
        payload["severity"] = "blocking"
    elif payload.get("severity") != "blocking" and severity == "warning":
        payload["severity"] = "warning"
    payload["actionability"] = actionability


def _extract_table_label(body: str) -> str:
    match = re.search(r"\\label\{([^}]+)\}", body or "")
    return match.group(1) if match else ""


def _table_font_commands(body: str) -> List[str]:
    found = []
    for command in ("\\tiny", "\\scriptsize", "\\footnotesize", "\\small"):
        if command in (body or ""):
            found.append(command)
    return found


def _table_font_rank(command: str) -> int:
    return {
        "": 0,
        "\\small": 1,
        "\\footnotesize": 2,
        "\\scriptsize": 3,
        "\\tiny": 4,
    }.get(command, 0)


def _strongest_table_font_command(commands: List[str]) -> str:
    if not commands:
        return ""
    return max(commands, key=_table_font_rank)


def _table_font_policy(
    *,
    col_count: int,
    row_width: int,
    multicolumn_span: int,
    env_name: str = "",
    expected_wide: Optional[bool] = None,
) -> Dict[str, Any]:
    """Classify table density and choose a conservative font policy."""
    extreme = (
        col_count >= 12
        or row_width >= 112
        or (col_count >= 10 and row_width >= 96)
    )
    wide = (
        4 <= col_count < 12
        or 55 <= row_width < 96
        or multicolumn_span >= 3
    )
    normal = col_count < 4 and row_width < 55 and multicolumn_span < 3
    is_full_width = env_name == "table*" or expected_wide is True

    if extreme:
        density = "extreme"
        preferred = "\\scriptsize"
        reason = "extreme density requires scriptsize to fit without overflow"
    elif wide:
        density = "wide"
        preferred = "\\small"
        reason = "wide table should stay near body size; scriptsize is not justified"
    else:
        density = "normal" if normal else "wide"
        preferred = "\\small" if is_full_width else ""
        reason = (
            "low-density full-width table should avoid upscaling and remain near body size"
            if preferred
            else "low-density table should remain at body font size"
        )

    return {
        "density_class": density,
        "preferred_command": preferred,
        "recommended_commands": [preferred] if preferred else [],
        "scriptsize_justified": preferred == "\\scriptsize",
        "reason": reason,
        "evidence": {
            "col_count": col_count,
            "row_width": row_width,
            "multicolumn_span": multicolumn_span,
            "env_name": env_name,
            "expected_wide": expected_wide,
        },
    }


def _requires_full_width_table(
    *,
    col_count: int,
    row_width: int,
    multicolumn_span: int,
) -> bool:
    """Return True only when a table is unlikely to fit in one column."""
    return (
        col_count >= _PROMOTE_TO_TABLE_STAR_MIN_COLS
        or row_width >= _PROMOTE_TO_TABLE_STAR_MIN_CONTENT_WIDTH
        or (multicolumn_span >= _MULTICOLUMN_WIDE_MIN_SPAN and col_count >= 8)
    )


def analyze_table_latex_contract(
    table_latex: str,
    *,
    table_id: str = "",
    section_type: str = "",
    expected_wide: Optional[bool] = None,
    source_kind: str = "user_provided",
) -> Dict[str, Any]:
    """
    Analyze one LaTeX table environment into the canonical table-review contract.

    This is deterministic and intentionally conservative. It records high-confidence
    formatting defects as blocking and leaves expensive/uncertain improvements as
    warnings for downstream rendered review.
    """
    latex = table_latex or ""
    env_match = re.search(
        r"\\begin\{(table\*?)\}(?:\[[^\]]*\])?(?P<body>.*?)\\end\{\1\}",
        latex,
        re.DOTALL,
    )
    env_name = env_match.group(1) if env_match else ""
    body = env_match.group("body") if env_match else latex
    label = table_id or _extract_table_label(body)
    payload = _new_table_review_payload(
        table_id=label,
        section_type=section_type,
        source_kind=source_kind,
    )

    col_spec = _extract_tabular_col_spec(body) or ""
    col_count = _count_cols_from_spec(col_spec) if col_spec else 0
    row_width = max(_estimate_row_width(body), _estimate_max_tabular_row_width(body))
    font_commands = _table_font_commands(body)
    strongest_font = _strongest_table_font_command(font_commands)
    has_resize = "\\resizebox" in body
    has_adjust = "\\adjustbox" in body
    mc_span = _max_multicolumn_span(body)
    wide_by_density = _requires_full_width_table(
        col_count=col_count,
        row_width=row_width,
        multicolumn_span=mc_span,
    )
    if wide_by_density:
        recommended_env = "table*"
    elif expected_wide is False:
        recommended_env = "table"
    else:
        recommended_env = env_name or "table"

    payload["deterministic_evidence"] = {
        "env_name": env_name,
        "col_spec": col_spec,
        "col_count": col_count,
        "row_width": row_width,
        "multicolumn_span": mc_span,
        "font_commands": font_commands,
        "strongest_font_command": strongest_font,
        "has_resizebox": has_resize,
        "has_adjustbox": has_adjust,
        "wide_by_density": wide_by_density,
        "expected_wide": expected_wide,
    }
    font_policy = _table_font_policy(
        col_count=col_count,
        row_width=row_width,
        multicolumn_span=mc_span,
        env_name=env_name,
        expected_wide=expected_wide,
    )
    payload["deterministic_evidence"]["font_policy"] = font_policy["evidence"]
    recommended_font_commands = list(font_commands)
    if not font_commands and font_policy["recommended_commands"]:
        recommended_font_commands = list(font_policy["recommended_commands"])
    elif strongest_font in {"\\scriptsize", "\\tiny"} and not font_policy["scriptsize_justified"]:
        recommended_font_commands = list(font_policy["recommended_commands"])
    payload["span_decision"] = {
        "current_env": env_name,
        "recommended_env": recommended_env,
        "confidence": 0.88 if recommended_env != env_name else 0.7,
        "reason": (
            "table is expected wide or dense enough for double-column layout"
            if recommended_env == "table*" else "table fits single-column policy"
        ),
    }
    payload["typography_decision"] = {
        "current_commands": font_commands,
        "recommended_commands": recommended_font_commands,
        "confidence": 0.8,
        "exception_reason": font_policy["reason"],
        "density_class": font_policy["density_class"],
        "scriptsize_justified": font_policy["scriptsize_justified"],
    }

    if recommended_env == "table*" and env_name == "table":
        _append_table_issue(
            payload,
            issue_type="wrong_column_span",
            severity="blocking",
            message=f"Table '{label}' should use table* based on deterministic width evidence.",
            evidence=payload["deterministic_evidence"],
            confidence=0.88,
        )
    if (
        expected_wide is False
        and env_name == "table*"
        and not wide_by_density
        and col_count <= 3
        and row_width < _RESIZEBOX_MIN_CONTENT_WIDTH
    ):
        _append_table_issue(
            payload,
            issue_type="wrong_column_span",
            severity="blocking",
            message=f"Table '{label}' should not span both columns based on deterministic width evidence.",
            evidence=payload["deterministic_evidence"],
            confidence=0.86,
        )
    if env_name == "table" and "\\textwidth" in body:
        _append_table_issue(
            payload,
            issue_type="single_column_textwidth",
            severity="blocking",
            message=f"Table '{label}' is single-column but uses text-width sizing.",
            evidence={"env_name": env_name},
            confidence=0.9,
        )
    if recommended_env == "table*" and has_resize and not font_commands:
        _append_table_issue(
            payload,
            issue_type="wide_table_missing_font_policy",
            severity="warning",
            message=f"Wide table '{label}' uses scaling without an explicit font policy.",
            evidence=payload["deterministic_evidence"],
            confidence=0.7,
        )
    if (
        env_name == "table*"
        and _has_forced_textwidth_resizebox(body)
        and not wide_by_density
        and col_count < _TABLE_STAR_RESIZEBOX_MIN_COLS
        and row_width < _TABLE_STAR_RESIZEBOX_MIN_CONTENT_WIDTH
    ):
        _append_table_issue(
            payload,
            issue_type="low_density_table_star_upscaled",
            severity="warning",
            message=(
                f"Wide table '{label}' is low-density but is forced to "
                "\\textwidth, which can make its font much larger than other tables."
            ),
            evidence=payload["deterministic_evidence"],
            confidence=0.82,
            actionability="repairable_formatting",
        )
    if strongest_font in {"\\scriptsize", "\\tiny"} and not font_policy["scriptsize_justified"]:
        _append_table_issue(
            payload,
            issue_type="scriptsize_without_density_justification",
            severity="warning",
            message=(
                f"Table '{label}' uses {strongest_font} although density evidence "
                "does not justify scriptsize-level shrinkage."
            ),
            evidence={
                **payload["deterministic_evidence"],
                "font_policy": font_policy,
            },
            confidence=0.84,
            actionability="repairable_formatting",
        )

    payload["final_action"] = (
        "applied_formatting"
        if payload.get("actionability") == "repairable_formatting"
        else "no_action"
    )
    return payload


def collect_table_layout_reviews(
    generated_sections: Dict[str, str],
    *,
    paper_plan: Any = None,
    tables: Optional[List[Any]] = None,
) -> List[Dict[str, Any]]:
    """Collect deterministic table layout reviews for generated section content."""
    wide_ids = {
        str(getattr(tbl, "id", ""))
        for tbl in (tables or [])
        if getattr(tbl, "wide", False) and getattr(tbl, "id", None)
    }
    if paper_plan is not None:
        for section in getattr(paper_plan, "sections", []) or []:
            for placement in getattr(section, "tables", []) or []:
                table_id = str(getattr(placement, "table_id", "") or "")
                if table_id and getattr(placement, "is_wide", False):
                    wide_ids.add(table_id)

    block_re = re.compile(
        r"\\begin\{table\*?\}(?:\[[^\]]*\])?.*?\\end\{table\*?\}",
        re.DOTALL,
    )
    reviews: List[Dict[str, Any]] = []
    for section_type, content in (generated_sections or {}).items():
        for match in block_re.finditer(content or ""):
            table_latex = match.group(0)
            label = _extract_table_label(table_latex)
            reviews.append(
                analyze_table_latex_contract(
                    table_latex,
                    table_id=label,
                    section_type=section_type,
                    expected_wide=(label in wide_ids) if label else None,
                )
            )
    return reviews


def collect_table_layout_review_bundle(
    generated_sections: Dict[str, str],
    *,
    paper_plan: Any = None,
    tables: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """Collect per-table reviews plus conservative paper-level table findings."""
    reviews = collect_table_layout_reviews(
        generated_sections,
        paper_plan=paper_plan,
        tables=tables,
    )
    paper_level_findings: List[Dict[str, Any]] = []
    comparable = []
    for review in reviews:
        evidence = review.get("deterministic_evidence") or {}
        typo = review.get("typography_decision") or {}
        commands = typo.get("current_commands") or []
        strongest = _strongest_table_font_command(commands)
        comparable.append(
            {
                "table_id": review.get("table_id", ""),
                "section_type": review.get("section_type", ""),
                "font_command": strongest,
                "font_rank": _table_font_rank(strongest),
                "density_class": typo.get("density_class", ""),
                "scriptsize_justified": bool(typo.get("scriptsize_justified")),
                "col_count": evidence.get("col_count", 0),
                "row_width": evidence.get("row_width", 0),
            }
        )

    if len(comparable) >= 2:
        max_item = max(comparable, key=lambda item: item["font_rank"])
        min_item = min(comparable, key=lambda item: item["font_rank"])
        rank_gap = int(max_item["font_rank"]) - int(min_item["font_rank"])
        if rank_gap >= 2 and not max_item["scriptsize_justified"]:
            paper_level_findings.append(
                {
                    "type": "table_font_inconsistent",
                    "severity": "warning",
                    "message": (
                        "Tables use visibly different font-size tiers without "
                        "density evidence justifying the smallest table font."
                    ),
                    "evidence": {
                        "max_shrink_table": max_item,
                        "largest_font_table": min_item,
                        "font_rank_gap": rank_gap,
                    },
                    "actionability": "repairable_formatting",
                    "restructure_candidate": True,
                    "restructure_rationale": (
                        "Consider schema restructuring only if formatting-only "
                        "normalization cannot avoid the font-size gap and core "
                        "data semantics can be proven unchanged."
                    ),
                }
            )

    table_star_re = re.compile(
        r"\\begin\{table\*\}(?:\[[^\]]*\])?.*?\\end\{table\*\}",
        re.DOTALL,
    )
    for section_type, content in (generated_sections or {}).items():
        matches = list(table_star_re.finditer(content or ""))
        if len(matches) < 2:
            continue
        current_cluster: List[re.Match[str]] = [matches[0]]

        def _emit_cluster(cluster: List[re.Match[str]]) -> None:
            if len(cluster) < 2:
                return
            ids = [_extract_table_label(item.group(0)) for item in cluster]
            paper_level_findings.append(
                {
                    "type": "table_float_page_risk",
                    "severity": "warning",
                    "message": (
                        "Multiple full-width table* floats are adjacent in one "
                        "section; LaTeX may create a mostly blank float-only page."
                    ),
                    "evidence": {
                        "section_type": section_type,
                        "table_ids": [tid for tid in ids if tid],
                        "cluster_size": len(cluster),
                    },
                    "actionability": "repairable_formatting",
                    "restructure_candidate": False,
                }
            )

        for match in matches[1:]:
            between = (content or "")[current_cluster[-1].end():match.start()]
            if between.strip():
                _emit_cluster(current_cluster)
                current_cluster = [match]
            else:
                current_cluster.append(match)
        _emit_cluster(current_cluster)

    status = "empty"
    if reviews:
        status = "needs_repair" if any(
            issue.get("severity") == "blocking"
            for review in reviews
            for issue in (review.get("issues") or [])
        ) else "ok"
    return {
        "status": status,
        "reviews": reviews,
        "paper_level_findings": paper_level_findings,
    }


def validate_table_layout_contract(
    generated_sections: Dict[str, str],
    paper_plan: Any = None,
    tables: Optional[List[Any]] = None,
) -> List[str]:
    """Return blocking deterministic table layout errors."""
    errors: List[str] = []
    for review in collect_table_layout_reviews(
        generated_sections,
        paper_plan=paper_plan,
        tables=tables,
    ):
        for issue in review.get("issues", []) or []:
            if issue.get("severity") == "blocking":
                errors.append(issue.get("message", "Blocking table layout issue"))
    return errors


def table_restructure_rejected_payload(
    *,
    table_id: str,
    section_type: str = "",
    rationale: str = "",
    reason: str = "critic_rejected",
) -> Dict[str, Any]:
    """Record a terminal restructuring rejection for a table."""
    payload = _new_table_review_payload(
        table_id=table_id,
        section_type=section_type,
    )
    payload["actionability"] = "repairable_formatting"
    payload["restructure_candidate"] = False
    payload["restructure_rationale"] = rationale
    payload["final_action"] = "reverted_original"
    _append_table_issue(
        payload,
        issue_type=reason,
        severity="warning",
        message=(
            f"Restructuring for table '{table_id}' was rejected; "
            "use original table with formatting-only optimization."
        ),
        confidence=1.0,
        actionability="repairable_formatting",
    )
    return payload


class TableValidator:
    """
    Validate and auto-fix LLM-generated LaTeX table output.
    - **Description**:
        - Checks structural consistency (row/col counts, label, booktabs).
        - Auto-fixes missing labels and adds \\resizebox for wide tables.
    """

    @classmethod
    def validate(
        cls,
        latex: str,
        structure: TableStructure,
        expected_label: str,
    ) -> ValidationResult:
        """
        Validate LaTeX table output against expected structure.
        - **Args**:
            - `latex` (str): LLM-generated LaTeX.
            - `structure` (TableStructure): Expected structure from source data.
            - `expected_label` (str): Expected \\label value.
        - **Returns**:
            - `ValidationResult`: Errors and warnings.
        """
        result = ValidationResult()

        # Check label
        if f"\\label{{{expected_label}}}" not in latex:
            result.errors.append(
                f"Missing \\label{{{expected_label}}} in generated LaTeX."
            )

        # Check caption
        if "\\caption" not in latex:
            result.errors.append("Missing \\caption in generated LaTeX.")

        # Count data rows in the tabular (lines with \\)
        tabular_rows = cls._count_tabular_rows(latex)
        if structure.data_row_count > 0 and tabular_rows > 0:
            # Allow header row(s) + data rows; just check data portion
            # The first row after \toprule/\midrule is usually the header
            expected_min = max(1, structure.data_row_count - 1)
            if tabular_rows < expected_min:
                result.errors.append(
                    f"Row count mismatch: expected at least "
                    f"{structure.data_row_count} data rows, "
                    f"found {tabular_rows} total tabular rows."
                )

        # Check column count in tabular spec
        latex_col_count = cls._count_tabular_cols(latex)
        if (structure.col_count > 0 and latex_col_count > 0
                and abs(latex_col_count - structure.col_count) > 2):
            result.warnings.append(
                f"Column count mismatch: expected {structure.col_count}, "
                f"found {latex_col_count} in tabular spec."
            )

        # Check booktabs
        if "\\toprule" not in latex or "\\bottomrule" not in latex:
            result.warnings.append(
                "Missing booktabs commands (\\toprule/\\bottomrule). "
                "Consider using booktabs style."
            )

        return result

    @classmethod
    def auto_fix(
        cls,
        latex: str,
        structure: TableStructure,
        expected_label: str,
        column_format: str = "double",
    ) -> str:
        """
        Auto-fix common issues in LLM-generated LaTeX table.
        - **Args**:
            - `latex` (str): LLM-generated LaTeX.
            - `structure` (TableStructure): Expected structure.
            - `expected_label` (str): Label to ensure.
            - `column_format` (str): Template column format.
        - **Returns**:
            - `str`: Fixed LaTeX.
        """
        fixed = latex

        # Fix 1: Insert missing label
        if f"\\label{{{expected_label}}}" not in fixed:
            # Insert after \caption{...}
            caption_match = re.search(r'(\\caption\{[^}]*\})', fixed)
            if caption_match:
                insert_pos = caption_match.end()
                fixed = (
                    fixed[:insert_pos]
                    + f"\\label{{{expected_label}}}"
                    + fixed[insert_pos:]
                )
            else:
                # Insert before \end{table...}
                fixed = re.sub(
                    r'(\\end\{table\*?\})',
                    f"\\label{{{expected_label}}}\n\\1",
                    fixed,
                    count=1,
                )

        # Fix 2: Add a max-width wrapper for wide tables. Use adjustbox rather
        # than resizebox so narrow natural-width tables are not enlarged.
        is_wide = structure.estimated_width_class in ("wide", "very_wide")
        if (
            is_wide
            and column_format == "double"
            and "\\resizebox" not in fixed
            and "\\adjustbox" not in fixed
        ):
            # Determine target width
            if "table*" in fixed:
                target_width = "\\textwidth"
            else:
                target_width = "\\columnwidth"

            # Wrap tabular in adjustbox max-width guard
            tabular_pattern = re.compile(
                r'(\\begin\{tabular[*]?\}\{[^}]*\}.*?\\end\{tabular[*]?\})',
                re.DOTALL,
            )
            match = tabular_pattern.search(fixed)
            if match:
                original = match.group(0)
                wrapped = (
                    f"\\adjustbox{{max width={target_width},center}}{{\n"
                    f"{original}\n"
                    f"}}"
                )
                fixed = fixed[:match.start()] + wrapped + fixed[match.end():]

        return fixed

    @staticmethod
    def _count_tabular_rows(latex: str) -> int:
        """Count rows in tabular environment (lines ending with \\\\)."""
        tabular_match = re.search(
            r'\\begin\{tabular[*]?\}.*?(\\end\{tabular[*]?\})',
            latex, re.DOTALL,
        )
        if not tabular_match:
            return 0
        body = tabular_match.group(0)
        # Count lines with \\ (row terminators), excluding rule commands
        rows = re.findall(r'\\\\', body)
        return len(rows)

    @staticmethod
    def _count_tabular_cols(latex: str) -> int:
        """Count columns from tabular column spec like {lccc} or {lp{3cm}cc}."""
        col_spec = _extract_tabular_col_spec(latex)
        if not col_spec:
            return 0
        return _count_cols_from_spec(col_spec)


# ═══════════════════════════════════════════════════════════════════════════
# smart_promote_wide_tables — content-aware table layout optimization
# ═══════════════════════════════════════════════════════════════════════════

# Thresholds for smart promotion decisions
_PROMOTE_TO_TABLE_STAR_MIN_COLS = 9
_PROMOTE_TO_TABLE_STAR_MIN_CONTENT_WIDTH = 72
_RESIZEBOX_MIN_COLS = 4
_RESIZEBOX_MIN_CONTENT_WIDTH = 55
_MULTICOLUMN_WIDE_MIN_SPAN = 3
_FONT_SHRINK_MIN_COLS = 12
_TABLE_STAR_RESIZEBOX_MIN_COLS = 9
_TABLE_STAR_RESIZEBOX_MIN_CONTENT_WIDTH = 72


def _extract_tabular_col_spec(content: str) -> Optional[str]:
    """
    Extract the column spec from \\begin{tabular}{...}, handling nested braces.
    - **Description**:
        - Standard regex [^}]* fails for specs like p{3cm}. This function
          uses brace-depth counting to correctly extract the full spec.
    """
    match = re.search(r'\\begin\{tabular[*]?\}\{', content)
    if not match:
        return None

    start = match.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == '{':
            depth += 1
        elif content[i] == '}':
            depth -= 1
        i += 1

    if depth == 0:
        return content[start:i - 1]
    return None


def _count_cols_from_spec(col_spec: str) -> int:
    """
    Count columns from a LaTeX tabular column spec, handling p{width} etc.
    - **Description**:
        - Strips brace content (e.g. {3cm}) before counting column letters
          to avoid false positives from characters inside width specs.
    """
    stripped = re.sub(r'\{[^}]*\}', '', col_spec)
    return len(re.findall(r'[lcrpXm]', stripped, re.IGNORECASE))


def _has_forced_textwidth_resizebox(body: str) -> bool:
    return bool(re.search(r"\\resizebox\{\s*\\textwidth\s*\}\{!\}", body or ""))


def _normalize_forced_resizebox_to_adjustbox(body: str, width: str) -> str:
    """Convert exact-width resizebox wrappers into max-width adjustbox wrappers."""
    escaped_width = re.escape(width)
    return re.sub(
        rf"\\resizebox\{{\s*{escaped_width}\s*\}}\{{!\}}\{{\s*"
        r"(\\begin\{tabular[*]?\}\{[^}]*\}.*?\\end\{tabular[*]?\})"
        r"\s*\}",
        lambda m: (
            f"\\adjustbox{{max width={width},center}}{{\n"
            f"{m.group(1)}\n"
            f"}}"
        ),
        body or "",
        flags=re.DOTALL,
    )


def _estimate_max_tabular_row_width(body: str) -> int:
    """
    Estimate max raw text width across tabular rows (no booktabs required).
    - **Description**:
        - Scans lines between ``\\begin{tabular}`` and ``\\end{tabular}`` that
          look like data rows (contain ``&`` and row terminator ``\\\\``).
        - Complements ``_estimate_row_width`` for tables without ``\\toprule``.

    - **Args**:
        - `body` (str): Table environment body (may include caption, etc.).

    - **Returns**:
        - `int`: Maximum cleaned character width among detected rows.
    """
    tab_m = re.search(r'\\begin\{tabular[*]?\}\{[^}]*\}', body)
    if not tab_m:
        return 0
    rest = body[tab_m.end():]
    end_m = re.search(r'\\end\{tabular[*]?\}', rest)
    if not end_m:
        return 0
    chunk = rest[: end_m.start()]
    max_w = 0
    for line in chunk.split("\n"):
        stripped = line.strip()
        if "&" not in stripped or "\\\\" not in stripped:
            continue
        if stripped.startswith("%"):
            continue
        clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', stripped)
        clean = re.sub(r'\\[a-zA-Z]+', '', clean)
        clean = clean.replace("\\\\", "").replace("&", "").strip()
        max_w = max(max_w, len(clean))
    return max_w


def _max_multicolumn_span(body: str) -> int:
    """
    Return the largest N in ``\\multicolumn{N}{...}`` within the table body.
    - **Args**:
        - `body` (str): Table environment body.

    - **Returns**:
        - `int`: Maximum span, or 0 if none.
    """
    spans = []
    for m in re.finditer(r'\\multicolumn\{(\d+)\}', body):
        try:
            spans.append(int(m.group(1)))
        except ValueError:
            continue
    return max(spans) if spans else 0


def smart_promote_wide_tables(content: str) -> str:
    """
    Intelligently promote wide tables and add max-width guards for double-column layouts.
    - **Description**:
        - Replaces the naive column-count-only heuristic with a decision
          based on both column count and content width.
        - Applies three tiers of intervention:
          1. \\adjustbox max-width only — for moderately wide tables
          2. Promote to table* + \\adjustbox max-width — for very wide tables
          3. Add \\scriptsize — for extremely wide tables (12+ cols)
        - Normalizes exact-width \\resizebox wrappers to max-width \\adjustbox.

    - **Args**:
        - `content` (str): LaTeX content (may contain multiple table envs).

    - **Returns**:
        - `str`: Content with smart table promotions applied.
    """
    # Match both table and table* environments
    env_pattern = re.compile(
        r'(\\begin\{(table\*?)\})(.*?)(\\end\{\2\})',
        re.DOTALL,
    )

    def _process_table(m: re.Match) -> str:
        begin_tag = m.group(1)
        env_name = m.group(2)
        body = m.group(3)
        end_tag = m.group(4)

        # Extract column spec from tabular (handles nested braces like p{3cm})
        col_spec = _extract_tabular_col_spec(body)
        if col_spec is None:
            return m.group(0)

        col_count = _count_cols_from_spec(col_spec)

        # Estimate content width from first data row (booktabs) and any row
        content_width = _estimate_row_width(body)
        loose_width = _estimate_max_tabular_row_width(body)
        row_width = max(content_width, loose_width)
        mc_span = _max_multicolumn_span(body)
        font_policy = _table_font_policy(
            col_count=col_count,
            row_width=row_width,
            multicolumn_span=mc_span,
            env_name=env_name,
            expected_wide=(env_name == "table*"),
        )

        needs_promote = (
            _requires_full_width_table(
                col_count=col_count,
                row_width=row_width,
                multicolumn_span=mc_span,
            )
            and env_name == "table"
        )
        table_star_needs_resize = (
            col_count >= _TABLE_STAR_RESIZEBOX_MIN_COLS
            or row_width >= _TABLE_STAR_RESIZEBOX_MIN_CONTENT_WIDTH
        )
        single_column_needs_resize = (
            col_count >= _RESIZEBOX_MIN_COLS
            or row_width >= _RESIZEBOX_MIN_CONTENT_WIDTH
            or (mc_span >= _MULTICOLUMN_WIDE_MIN_SPAN and col_count >= 3)
        )
        needs_resize = (
            "\\resizebox" not in body
            and "\\adjustbox" not in body
            and (
                table_star_needs_resize
                if (needs_promote or env_name == "table*")
                else single_column_needs_resize
            )
        )
        existing_font_commands = _table_font_commands(body)
        preferred_font = str(font_policy.get("preferred_command") or "")
        needs_font_shrink = preferred_font == "\\scriptsize"
        needs_wide_font_policy = (
            (needs_promote or env_name == "table*")
            and bool(preferred_font)
            and not existing_font_commands
        )

        new_body = body

        # Tier 3: Add font size command for very wide tables
        if needs_font_shrink or needs_wide_font_policy:
            # Insert \scriptsize after \centering (or at start of body)
            centering_match = re.search(r'(\\centering\s*\n?)', new_body)
            if (
                centering_match
                and "\\scriptsize" not in new_body
                and "\\small" not in new_body
            ):
                insert_pos = centering_match.end()
                font_cmd = preferred_font or "\\small"
                new_body = (
                    new_body[:insert_pos]
                    + f"{font_cmd}\n"
                    + new_body[insert_pos:]
                )

        # Exact-width resizebox changes the table font size both directions.
        # Normalize it to max-width adjustbox so overflow is capped without
        # magnifying naturally narrower tables.
        new_body = _normalize_forced_resizebox_to_adjustbox(new_body, "\\textwidth")
        new_body = _normalize_forced_resizebox_to_adjustbox(new_body, "\\columnwidth")

        # Tier 1/2: Add max-width adjustbox around tabular
        if needs_resize:
            target_width = (
                "\\textwidth"
                if (needs_promote or env_name == "table*")
                else "\\columnwidth"
            )
            tabular_full = re.compile(
                r'(\\begin\{tabular[*]?\}\{[^}]*\}.*?\\end\{tabular[*]?\})',
                re.DOTALL,
            )
            tab_match = tabular_full.search(new_body)
            if tab_match:
                original = tab_match.group(0)
                wrapped = (
                    f"\\adjustbox{{max width={target_width},center}}{{\n"
                    f"{original}\n"
                    f"}}"
                )
                new_body = new_body[:tab_match.start()] + wrapped + new_body[tab_match.end():]

        # Tier 2: Promote table -> table*
        if needs_promote:
            return f"\\begin{{table*}}{new_body}\\end{{table*}}"

        return f"{begin_tag}{new_body}{end_tag}"

    return env_pattern.sub(_process_table, content)


def rebalance_adjacent_table_star_floats(content: str) -> str:
    """
    Demote safely single-column-capable tables from consecutive ``table*`` clusters.

    Consecutive full-width floats at a section tail often become a mostly blank
    float-only page in two-column templates. This keeps genuinely wide tables
    full-width, but lets moderate density tables flow in one column.
    """
    if "\\begin{table*}" not in (content or ""):
        return content

    block_re = re.compile(
        r"\\begin\{table\*\}(?:\[[^\]]*\])?.*?\\end\{table\*\}",
        re.DOTALL,
    )
    matches = list(block_re.finditer(content))
    if len(matches) < 2:
        return content

    demote_spans: List[Tuple[int, int]] = []
    cluster: List[re.Match[str]] = [matches[0]]

    def _is_only_spacing_between(left: re.Match[str], right: re.Match[str]) -> bool:
        return not content[left.end():right.start()].strip()

    def _flush_cluster(items: List[re.Match[str]]) -> None:
        if len(items) < 2:
            return
        for item in items:
            block = item.group(0)
            body_match = re.search(
                r"\\begin\{table\*\}(?:\[[^\]]*\])?(?P<body>.*?)\\end\{table\*\}",
                block,
                re.DOTALL,
            )
            body = body_match.group("body") if body_match else block
            col_spec = _extract_tabular_col_spec(body) or ""
            col_count = _count_cols_from_spec(col_spec) if col_spec else 0
            row_width = max(_estimate_row_width(body), _estimate_max_tabular_row_width(body))
            mc_span = _max_multicolumn_span(body)
            if not _requires_full_width_table(
                col_count=col_count,
                row_width=row_width,
                multicolumn_span=mc_span,
            ):
                demote_spans.append((item.start(), item.end()))

    for match in matches[1:]:
        if _is_only_spacing_between(cluster[-1], match):
            cluster.append(match)
        else:
            _flush_cluster(cluster)
            cluster = [match]
    _flush_cluster(cluster)

    if not demote_spans:
        return content

    def _demote(block: str) -> str:
        block = re.sub(r"\\begin\{table\*\}(\[[^\]]*\])?", r"\\begin{table}\1", block, count=1)
        block = block.replace("\\end{table*}", "\\end{table}", 1)
        block = block.replace("max width=\\textwidth", "max width=\\columnwidth")
        block = block.replace("\\resizebox{\\textwidth}", "\\resizebox{\\columnwidth}")
        return block

    rebuilt = []
    cursor = 0
    for start, end in demote_spans:
        rebuilt.append(content[cursor:start])
        rebuilt.append(_demote(content[start:end]))
        cursor = end
    rebuilt.append(content[cursor:])
    return "".join(rebuilt)


def add_adjustbox_safety(content: str) -> str:
    """
    Wrap each ``tabular`` in ``\\adjustbox{max width=...}`` when not already scaled.
    - **Description**:
        - For double-column papers, shrinks tables that would overflow the column.
        - Skips environments that already use ``\\resizebox`` or ``\\adjustbox``.
        - Requires ``\\usepackage{adjustbox}`` (auto-injected by Typesetter when missing).

    - **Args**:
        - `content` (str): LaTeX fragment (e.g. one section body).

    - **Returns**:
        - `str`: Content with optional ``adjustbox`` wrappers added.
    """
    env_pattern = re.compile(
        r'(\\begin\{(table\*?)\})(.*?)(\\end\{\2\})',
        re.DOTALL,
    )
    tabular_full = re.compile(
        r'(\\begin\{tabular[*]?\}\{[^}]*\}.*?\\end\{tabular[*]?\})',
        re.DOTALL,
    )

    def _wrap(m: re.Match[str]) -> str:
        begin_tag = m.group(1)
        env_name = m.group(2)
        body = m.group(3)
        end_tag = m.group(4)
        if "\\adjustbox" in body or "\\resizebox" in body:
            return m.group(0)
        tab_match = tabular_full.search(body)
        if not tab_match:
            return m.group(0)
        original = tab_match.group(0)
        width = "\\textwidth" if env_name == "table*" else "\\columnwidth"
        wrapped_tab = (
            f"\\adjustbox{{max width={width},center}}{{\n{original}\n}}"
        )
        new_body = body[: tab_match.start()] + wrapped_tab + body[tab_match.end() :]
        return f"{begin_tag}{new_body}{end_tag}"

    return env_pattern.sub(_wrap, content)


def _estimate_row_width(body: str) -> int:
    """
    Estimate the character width of the widest data row in the tabular.
    - **Description**:
        - Finds the first row after \\midrule (or \\toprule) and measures
          total character length of cell contents.
    """
    lines = body.split('\n')
    in_data = False
    max_width = 0

    for line in lines:
        stripped = line.strip()
        if '\\midrule' in stripped or '\\toprule' in stripped:
            in_data = True
            continue
        if '\\bottomrule' in stripped or '\\end{tabular' in stripped:
            break
        if in_data and '\\\\' in stripped:
            # Remove LaTeX commands for width estimation
            clean = re.sub(r'\\[a-zA-Z]+\{[^}]*\}', '', stripped)
            clean = re.sub(r'\\[a-zA-Z]+', '', clean)
            clean = clean.replace('\\\\', '').replace('&', '').strip()
            max_width = max(max_width, len(clean))

    return max_width


def _escape_latex_text(text: str) -> str:
    """
    Escape plain text for safe insertion into LaTeX text commands.
    - **Description**:
        - Escapes common LaTeX special characters in user-provided text.
        - Intended for metadata strings rendered in headings or prose.

    - **Args**:
        - `text` (str): Raw text.

    - **Returns**:
        - `escaped_text` (str): LaTeX-safe text.
    """
    raw = text or ""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in raw)


def _parse_table_rows(content: str) -> List[List[str]]:
    """
    Parse raw table content into rows.
    - **Description**:
        - Supports Markdown pipe tables and CSV text.
        - Skips Markdown separator rows like ``|---|---|``.
        - Returns normalized trimmed cells.

    - **Args**:
        - `content` (str): Raw table content.

    - **Returns**:
        - `rows` (List[List[str]]): Parsed rows.
    """
    raw = (content or "").strip()
    if not raw:
        return []

    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if lines and lines[0].startswith("|"):
        rows: List[List[str]] = []
        for line in lines:
            body = line.strip("|").strip()
            if re.match(r'^[\s\-:|]+$', body):
                continue
            rows.append([cell.strip() for cell in body.split("|")])
        return rows

    parsed_rows: List[List[str]] = []
    for row in csv.reader(io.StringIO(raw)):
        parsed_rows.append([cell.strip() for cell in row])
    return parsed_rows


def _build_table_latex_from_source(
    table_id: str,
    caption: str,
    content: str,
) -> str:
    """
    Build a deterministic LaTeX table from source content.
    - **Description**:
        - Converts parsed rows directly into a booktabs tabular.
        - Preserves row/column structure without LLM conversion.
        - Uses '-' for missing values.

    - **Args**:
        - `table_id` (str): Table label id.
        - `caption` (str): Raw caption text.
        - `content` (str): Raw table content.

    - **Returns**:
        - `table_latex` (str): Deterministic table LaTeX.
    """
    rows = _parse_table_rows(content)
    if not rows:
        raise ValueError(f"Cannot build table '{table_id}' from empty source content")

    col_count = max(len(row) for row in rows)
    normalized_rows: List[List[str]] = []
    for row in rows:
        padded = row + [""] * max(0, col_count - len(row))
        normalized_rows.append([_escape_latex_text(cell or "-") for cell in padded])

    header = normalized_rows[0]
    data_rows = normalized_rows[1:]
    col_spec = "l" + ("c" * (col_count - 1))
    safe_caption = _escape_latex_text(normalize_caption(caption) or table_id)

    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{{safe_caption}}}",
        f"\\label{{{table_id}}}",
        f"\\begin{{tabular}}{{{col_spec}}}",
        "\\toprule",
        " & ".join(header) + " \\\\",
        "\\midrule",
    ]
    for row in data_rows:
        lines.append(" & ".join(row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}"])
    return "\n".join(lines)


def build_table_preview_document(
    table_latex: str,
    column_format: str = "double",
    title: str = "Table Preview",
) -> str:
    """
    Build a standalone LaTeX document for single-table visual preview.
    - **Description**:
        - Wraps one table LaTeX block into a minimal compile-ready document.
        - Supports single/double-column preview mode via documentclass options.
        - Preserves the original table environment content as-is.

    - **Args**:
        - `table_latex` (str): Converted LaTeX table environment.
        - `column_format` (str): "single" or "double" layout preview mode.
        - `title` (str): Preview document title.

    - **Returns**:
        - `preview_tex` (str): Standalone .tex source for table-only preview.
    """
    clean_table = _strip_code_fences((table_latex or "").strip())
    if not clean_table:
        clean_table = (
            "\\begin{table}[htbp]\n"
            "\\centering\n"
            "\\caption{Table Preview}\n"
            "\\label{tab:preview}\n"
            "\\begin{tabular}{lc}\n"
            "\\toprule\n"
            "A & B \\\\\n"
            "\\bottomrule\n"
            "\\end{tabular}\n"
            "\\end{table}"
        )

    if "\\begin{table" not in clean_table:
        clean_table = (
            "\\begin{table}[htbp]\n"
            "\\centering\n"
            f"{clean_table}\n"
            "\\end{table}"
        )

    class_opts = "[twocolumn]" if column_format == "double" else ""
    safe_title = _escape_latex_text(title)
    return (
        f"\\documentclass{class_opts}{{article}}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{adjustbox}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\begin{document}\n"
        f"\\section*{{{safe_title}}}\n"
        f"{clean_table}\n"
        "\\end{document}\n"
    )


def build_section_table_preview_document(
    section_type: str,
    section_content: str,
    column_format: str = "double",
) -> str:
    """
    Build a compile-ready preview for actual post-normalization section content.

    Unlike the single-table preview path, this preserves all table environments in
    the section together so downstream checks can inspect interactions between
    multiple tables.
    """
    clean_content = _strip_code_fences((section_content or "").strip())
    safe_title = _escape_latex_text(f"Section Preview {section_type or 'section'}")
    class_opts = "[twocolumn]" if column_format == "double" else ""
    return (
        f"\\documentclass{class_opts}{{article}}\n"
        "\\usepackage[T1]{fontenc}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage{booktabs}\n"
        "\\usepackage{graphicx}\n"
        "\\usepackage{adjustbox}\n"
        "\\usepackage[margin=1in]{geometry}\n"
        "\\begin{document}\n"
        f"\\section*{{{safe_title}}}\n"
        f"{clean_content}\n"
        "\\end{document}\n"
    )


def build_section_table_preview_documents(
    section_contents: Dict[str, str],
    column_format: str = "double",
) -> Dict[str, str]:
    """Build section-joint preview documents for sections that contain tables."""
    previews: Dict[str, str] = {}
    for section_type, content in (section_contents or {}).items():
        if "\\begin{table" not in (content or ""):
            continue
        previews[section_type] = build_section_table_preview_document(
            section_type=section_type,
            section_content=content,
            column_format=column_format,
        )
    return previews


def build_table_preview_documents(
    tables: list,
    converted_tables: Dict[str, str],
    column_format: str = "double",
    allow_placeholder: bool = False,
    base_path: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build standalone table preview documents for converted metadata tables.
    - **Description**:
        - Creates one compile-ready LaTeX document per table ID.
        - Uses converted table LaTeX when available.
        - Falls back to a labeled placeholder table if conversion is missing.

    - **Args**:
        - `tables` (list): List of table specs (TableSpec-like objects).
        - `converted_tables` (Dict[str, str]): Mapping table_id -> converted table LaTeX.
        - `column_format` (str): "single" or "double" preview layout mode.
        - `allow_placeholder` (bool): Whether to allow placeholder table fallback.
        - `base_path` (str, optional): Base path for relative `table.file_path` loading.

    - **Returns**:
        - `preview_docs` (Dict[str, str]): Mapping table_id -> standalone preview tex.
    """
    preview_docs: Dict[str, str] = {}
    converted = converted_tables or {}

    for table in tables or []:
        table_id = getattr(table, "id", None) or ""
        if not table_id:
            continue

        table_latex = converted.get(table_id, "")
        if not table_latex:
            source_content = _read_table_content(table, base_path=base_path) or ""
            if source_content.strip():
                table_latex = _build_table_latex_from_source(
                    table_id=table_id,
                    caption=getattr(table, "caption", "") or table_id,
                    content=source_content,
                )
            elif allow_placeholder:
                caption = _escape_latex_text(
                    normalize_caption(getattr(table, "caption", "") or table_id),
                )
                table_latex = (
                    "\\begin{table}[htbp]\n"
                    "\\centering\n"
                    f"\\caption{{{caption}}}\n"
                    f"\\label{{{table_id}}}\n"
                    "\\begin{tabular}{lc}\n"
                    "\\toprule\n"
                    "Column & Value \\\\\n"
                    "\\bottomrule\n"
                    "\\end{tabular}\n"
                    "\\end{table}"
                )
            else:
                raise ValueError(
                    f"Missing converted table and source content for '{table_id}'",
                )

        preview_docs[table_id] = build_table_preview_document(
            table_latex=table_latex,
            column_format=column_format,
            title=f"Preview {table_id}",
        )

    return preview_docs


def _sanitize_table_preview_filename(table_id: str) -> str:
    """
    Convert a table id into a filesystem-safe filename stem.
    - **Description**:
        - Replaces unsupported filename characters with underscores.
        - Preserves alphanumeric, dot, underscore, and dash characters.

    - **Args**:
        - `table_id` (str): Table identifier such as "tab:results".

    - **Returns**:
        - `safe_name` (str): Safe filename stem.
    """
    raw = (table_id or "").strip()
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", raw) or "table_preview"
    suffix = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{cleaned}_{suffix}"


def _extract_latex_warnings_from_log(log_content: str) -> List[str]:
    """
    Extract warning messages from LaTeX log content.
    - **Description**:
        - Collects classic LaTeX warning forms.
        - De-duplicates while preserving message order.

    - **Args**:
        - `log_content` (str): Full log text.

    - **Returns**:
        - `warnings` (List[str]): Warning messages.
    """
    candidates: List[str] = []
    patterns = [
        r"LaTeX Warning:\s*(.*?)(?:\n|$)",
        r"Warning:\s*(.*?)(?:\n|$)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, log_content or ""):
            msg = (match or "").strip()
            if msg:
                candidates.append(msg)

    deduped: List[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _extract_latex_errors_from_log(log_content: str) -> List[str]:
    """
    Extract error messages from LaTeX log content.
    - **Description**:
        - Captures lines beginning with "!" as primary LaTeX errors.
        - Also captures generic "Error:" lines.

    - **Args**:
        - `log_content` (str): Full log text.

    - **Returns**:
        - `errors` (List[str]): Error messages.
    """
    candidates: List[str] = []
    for line in (log_content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("!"):
            msg = stripped[1:].strip()
            if msg:
                candidates.append(msg)
        elif "Error:" in stripped:
            msg = stripped.split("Error:", 1)[1].strip()
            if msg:
                candidates.append(msg)

    deduped: List[str] = []
    seen = set()
    for item in candidates:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def compile_table_preview_document(
    table_id: str,
    preview_tex: str,
    output_dir: str,
    max_passes: int = 2,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """
    Compile one standalone table preview document with pdflatex.
    - **Description**:
        - Writes preview tex into output_dir and runs pdflatex passes.
        - Returns a structured result with artifact paths and diagnostics.
        - Intended for table-only visual validation loops.

    - **Args**:
        - `table_id` (str): Table identifier.
        - `preview_tex` (str): Standalone LaTeX source.
        - `output_dir` (str): Directory for .tex/.pdf/.log artifacts.
        - `max_passes` (int): Number of pdflatex passes.
        - `timeout_seconds` (int): Timeout per pdflatex invocation.

    - **Returns**:
        - `result` (Dict[str, Any]): Compilation result details.
    """
    resolved_output_dir = os.path.abspath(output_dir)
    os.makedirs(resolved_output_dir, exist_ok=True)
    safe_name = _sanitize_table_preview_filename(table_id)
    tex_filename = f"{safe_name}.tex"
    tex_path = os.path.join(resolved_output_dir, tex_filename)
    pdf_path = os.path.join(resolved_output_dir, f"{safe_name}.pdf")
    log_path = os.path.join(resolved_output_dir, f"{safe_name}.log")

    result: Dict[str, Any] = {
        "table_id": table_id,
        "success": False,
        "tex_path": tex_path,
        "pdf_path": pdf_path,
        "log_path": log_path,
        "warnings": [],
        "errors": [],
        "attempts": 0,
    }

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(preview_tex or "")

    try:
        final_returncode = 0
        passes = max(1, int(max_passes or 1))
        for attempt in range(passes):
            result["attempts"] = attempt + 1
            proc = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-output-directory",
                    resolved_output_dir,
                    tex_filename,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                cwd=resolved_output_dir,
            )
            final_returncode = proc.returncode
            if proc.returncode != 0:
                break

        log_content = ""
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                log_content = f.read()
            result["warnings"] = _extract_latex_warnings_from_log(log_content)
            result["errors"] = _extract_latex_errors_from_log(log_content)

        if final_returncode != 0 and not result["errors"]:
            result["errors"].append("pdflatex exited with non-zero return code")

        result["success"] = os.path.exists(pdf_path) and final_returncode == 0
        return result
    except subprocess.TimeoutExpired:
        result["errors"].append("pdflatex timeout")
        return result
    except FileNotFoundError:
        result["errors"].append("pdflatex not found")
        return result
    except Exception as e:
        result["errors"].append(str(e))
        return result


def compile_table_preview_documents(
    preview_docs: Dict[str, str],
    output_dir: str,
    max_passes: int = 2,
    timeout_seconds: int = 60,
) -> Dict[str, Dict[str, Any]]:
    """
    Compile multiple standalone table preview documents.
    - **Description**:
        - Runs table preview compilation per table id.
        - Returns per-table structured outcomes for downstream checks.

    - **Args**:
        - `preview_docs` (Dict[str, str]): Table id to preview tex mapping.
        - `output_dir` (str): Root output directory for artifacts.
        - `max_passes` (int): Number of pdflatex passes per table.
        - `timeout_seconds` (int): Timeout per pdflatex call.

    - **Returns**:
        - `results` (Dict[str, Dict[str, Any]]): Table id to result mapping.
    """
    results: Dict[str, Dict[str, Any]] = {}
    os.makedirs(output_dir, exist_ok=True)

    for table_id, preview_tex in (preview_docs or {}).items():
        results[table_id] = compile_table_preview_document(
            table_id=table_id,
            preview_tex=preview_tex,
            output_dir=output_dir,
            max_passes=max_passes,
            timeout_seconds=timeout_seconds,
        )

    return results


def compile_section_table_preview_documents(
    section_preview_docs: Dict[str, str],
    output_dir: str,
    max_passes: int = 2,
    timeout_seconds: int = 60,
) -> Dict[str, Dict[str, Any]]:
    """Compile section-joint preview documents keyed by section type."""
    results: Dict[str, Dict[str, Any]] = {}
    os.makedirs(output_dir, exist_ok=True)
    for section_type, preview_tex in (section_preview_docs or {}).items():
        result = compile_table_preview_document(
            table_id=f"section:{section_type}",
            preview_tex=preview_tex,
            output_dir=output_dir,
            max_passes=max_passes,
            timeout_seconds=timeout_seconds,
        )
        result["section_type"] = section_type
        results[section_type] = result
    return results


def _read_table_content(
    table: "TableSpec",
    base_path: Optional[str] = None,
    fallback_base_path: Optional[str] = None,
) -> Optional[str]:
    """
    Read raw table content from file_path or inline content.
    - **Args**:
        - `table` (TableSpec): Table specification.
        - `base_path` (str, optional): Base path for resolving file_path.
    - **Returns**:
        - `str`: Raw table content, or None.
    """
    if table.file_path:
        resolved = resolve_asset_path(
            table.file_path,
            materials_root=base_path,
            fallback_base=fallback_base_path,
            require_within_root=bool(base_path),
        )
        file_path = resolved.resolved_path or table.file_path

        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                logger.info("table_converter.read_file path=%s", file_path)
                return content
            else:
                logger.warning(
                    "table_converter.file_not_found path=%s candidates=%s",
                    file_path,
                    resolved.candidates,
                )
                if table.content:
                    logger.info(
                        "table_converter.fallback_inline_content id=%s",
                        getattr(table, "id", "unknown"),
                    )
                    return table.content
        except Exception as e:
            logger.error(
                "table_converter.file_read_error path=%s error=%s",
                file_path, str(e),
            )
            if table.content:
                logger.info(
                    "table_converter.fallback_inline_after_error id=%s",
                    getattr(table, "id", "unknown"),
                )
                return table.content
    else:
        return table.content
    return None


def _strip_code_fences(text: str) -> str:
    """Remove markdown code block markers from LLM output."""
    if text.startswith("```"):
        lines = text.split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return '\n'.join(lines)
    return text


async def convert_table_to_latex(
    table: "TableSpec",
    llm_client: Any,
    model_name: str,
    base_path: Optional[str] = None,
    fallback_base_path: Optional[str] = None,
    column_format: str = "double",
) -> Optional[str]:
    """
    Convert a TableSpec to LaTeX format using LLM with enhanced pipeline.
    - **Description**:
        - Pre-analyzes table structure with TableAnalyzer.
        - Builds context-aware prompt via build_conversion_prompt.
        - Validates and auto-fixes LLM output via TableValidator.

    - **Args**:
        - `table` (TableSpec): Table specification.
        - `llm_client`: OpenAI-compatible async client.
        - `model_name` (str): Model to use for conversion.
        - `base_path` (str, optional): Base path for resolving file_path.
        - `column_format` (str): Template column format ("single" or "double").

    - **Returns**:
        - `str`: Complete LaTeX table code, or None if conversion fails.
    """
    if table.auto_generate:
        logger.warning(
            "table_converter.auto_generate_not_implemented id=%s", table.id,
        )
        return None

    content = _read_table_content(table, base_path, fallback_base_path)
    if not content:
        logger.warning("table_converter.no_content id=%s", table.id)
        return None

    # Phase 1: Structural analysis
    structure = TableAnalyzer.analyze(content)
    logger.info(
        "table_converter.analyzed id=%s cols=%d rows=%d width=%s multirow=%s",
        table.id, structure.col_count, structure.data_row_count,
        structure.estimated_width_class, structure.has_multirow_header,
    )

    # Phase 2: Build enhanced prompt
    prompt = build_conversion_prompt(
        label=table.id,
        caption=table.caption,
        content=content,
        structure=structure,
        column_format=column_format,
        return_max_tokens=False,
    )

    try:
        response = await llm_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert LaTeX typesetter specializing in "
                        "academic tables. Preserve ALL data exactly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        latex_content = response.choices[0].message.content.strip()
        latex_content = _strip_code_fences(latex_content)

        # Phase 3: Validate and auto-fix
        validation = TableValidator.validate(
            latex_content, structure, table.id,
        )
        if not validation.is_valid:
            logger.warning(
                "table_converter.validation_errors id=%s errors=%s",
                table.id, validation.errors,
            )
            latex_content = TableValidator.auto_fix(
                latex_content, structure, table.id, column_format,
            )

        if validation.warnings:
            logger.info(
                "table_converter.validation_warnings id=%s warnings=%s",
                table.id, validation.warnings,
            )

        logger.info(
            "table_converter.success id=%s length=%d",
            table.id, len(latex_content),
        )

        return latex_content

    except Exception as e:
        logger.error(
            "table_converter.llm_error id=%s error=%s",
            table.id, str(e),
        )
        return None


async def convert_tables(
    tables: list,
    llm_client: Any,
    model_name: str,
    base_path: Optional[str] = None,
    fallback_base_path: Optional[str] = None,
    column_format: str = "double",
) -> dict:
    """
    Convert multiple tables to LaTeX with enhanced pipeline.
    - **Args**:
        - `tables` (List[TableSpec]): List of table specifications.
        - `llm_client`: OpenAI-compatible async client.
        - `model_name` (str): Model to use.
        - `base_path` (str, optional): Base path for file resolution.
        - `column_format` (str): Template column format.
    - **Returns**:
        - `dict`: Mapping of table_id to LaTeX code.
    """
    converted = {}

    for table in tables:
        latex = await convert_table_to_latex(
            table=table,
            llm_client=llm_client,
            model_name=model_name,
            base_path=base_path,
            fallback_base_path=fallback_base_path,
            column_format=column_format,
        )
        if latex:
            converted[table.id] = latex

    logger.info(
        "table_converter.batch_complete total=%d converted=%d",
        len(tables), len(converted),
    )

    return converted


# =========================================================================
# Caption normalization
# =========================================================================

_CAPTION_PREFIX_RE = re.compile(
    r'^(?:Table|Figure|Tab\.|Fig\.|TABLE|FIGURE|FIG\.)\s*\d+[\.:]\s*',
    re.IGNORECASE,
)


def normalize_caption(caption: str) -> str:
    """
    Strip redundant numbering prefixes from captions.
    - **Description**:
        - LaTeX auto-generates "Table N." / "Figure N." via \\caption{}.
          If the source caption already contains such a prefix the rendered
          output will read "Table 1. Table 1. ...", causing duplication.
        - This function strips the leading prefix so \\caption{} produces
          the correct single-numbered caption.

    - **Args**:
        - `caption` (str): Raw caption text, possibly with numbering prefix.

    - **Returns**:
        - `str`: Caption with the redundant prefix removed.
    """
    if not caption:
        return ""
    return _CAPTION_PREFIX_RE.sub('', caption).strip()


# =========================================================================
# Float reference injection (Stage 3 of decomposed writer pipeline)
# =========================================================================

_FLOAT_MARKER_RE = re.compile(r'\[FLOAT:([^\]]+)\]')


def inject_float_refs(
    latex: str,
    figures_to_ref: List[str],
    tables_to_ref: List[str],
) -> str:
    """
    Replace [FLOAT:{id}] markers with proper LaTeX references.
    - **Description**:
        - Stage 3 of the decomposed writer pipeline.
        - Mechanically replaces markers placed by Stage 1 (core content).
        - Cleans up any orphan markers that don't match known IDs.

    - **Args**:
        - `latex` (str): LaTeX content with [FLOAT:...] markers.
        - `figures_to_ref` (List[str]): Figure IDs (e.g. "fig:arch").
        - `tables_to_ref` (List[str]): Table IDs (e.g. "tab:results").

    - **Returns**:
        - `str`: LaTeX with markers replaced by Table~\\ref / Figure~\\ref.
    """
    known_ids = set(figures_to_ref or []) | set(tables_to_ref or [])
    fig_set = set(figures_to_ref or [])
    table_set = set(tables_to_ref or [])

    def _ref_text(float_id: str) -> str:
        kind = "Figure" if float_id in fig_set else "Table"
        return f"{kind}~\\ref{{{float_id}}}"

    def _replace(m: re.Match) -> str:
        fid = m.group(1)
        if fid in known_ids:
            return _ref_text(fid)
        return ""

    def _has_explicit_ref(text: str, float_id: str) -> bool:
        return f"\\ref{{{float_id}}}" in text

    def _repair_dangling_slot(text: str, float_id: str) -> str:
        ref_text = _ref_text(float_id)

        patterns = [
            (
                re.compile(
                    r'(?P<prefix>\b(?:shown|illustrated|visualized|depicted|captured|'
                    r'reported|detailed|summarized|presented|compared|displayed|listed|'
                    r'tabulated)\s+in)(?P<suffix>[,.;:])',
                    re.IGNORECASE,
                ),
                lambda m: f"{m.group('prefix')} {ref_text}{m.group('suffix')}",
            ),
            (
                re.compile(
                    r'(?P<prefix>\bin)\s+'
                    r'(?=(?:demonstrate|demonstrates|show|shows|illustrate|illustrates|'
                    r'highlight|highlights|reveal|reveals|detail|details|compare|compares|'
                    r'capture|captures|present|presents)\b)',
                    re.IGNORECASE,
                ),
                lambda m: f"{m.group('prefix')} {ref_text} ",
            ),
        ]

        for pattern, replacement in patterns:
            updated, count = pattern.subn(replacement, text, count=1)
            if count:
                return updated
        return text

    result = _FLOAT_MARKER_RE.sub(_replace, latex)
    for float_id in list(fig_set) + list(table_set):
        if _has_explicit_ref(result, float_id):
            continue
        repaired = _repair_dangling_slot(result, float_id)
        if repaired != result:
            result = repaired
            continue
        suffix = "" if result.rstrip().endswith((".", "!", "?")) else "."
        joiner = "" if not result.strip() else " "
        result = f"{result.rstrip()}{suffix}{joiner}See {_ref_text(float_id)}."
    result = re.sub(r'\s{2,}', ' ', result)
    return result


# =========================================================================
# Direct-injection helpers (post-Writer processing)
# =========================================================================

def strip_writer_tables(content: str, known_table_ids: set) -> str:
    """
    Remove \\begin{table}...\\end{table} blocks whose \\label matches a known ID.
    - **Description**:
        - Under the direct-injection model the Writer is told NOT to create table
          environments, but may still do so.  This function defensively strips
          any Writer-generated table environments for tables that will be
          injected from the pre-converted pool.
        - Tables whose label is NOT in *known_table_ids* are preserved (the Writer
          may legitimately create ad-hoc tables not in the metadata).

    - **Args**:
        - `content` (str): Section LaTeX content from the Writer.
        - `known_table_ids` (set): Table IDs that will be injected later.

    - **Returns**:
        - `str`: Content with matching table environments removed.
    """
    if not known_table_ids:
        return content

    for tbl_id in known_table_ids:
        escaped_id = re.escape(tbl_id)
        for env in ("table*", "table"):
            esc_env = re.escape(env)
            pattern = re.compile(
                rf'\\begin{{{esc_env}}}.*?\\label{{{escaped_id}}}.*?\\end{{{esc_env}}}\s*',
                re.DOTALL,
            )
            content = pattern.sub('', content)

    return content.strip() if content.strip() else content


def inject_tables(
    content: str,
    section_plan,
    tables,
    converted_tables: dict,
) -> str:
    """
    Inject pre-converted table environments at the first \\ref location.
    - **Description**:
        - For each table assigned to this section (via section_plan), finds the
          first ``Table~\\ref{tab:id}`` in the content and inserts the full
          table environment after the enclosing sentence.
        - If no \\ref is found, appends the table at the end.
        - Skips tables already defined in the content.
        - Ensures every injected table has a \\label.

    - **Args**:
        - `content` (str): Section LaTeX content (post strip_writer_tables).
        - `section_plan`: Section plan with ``get_table_ids_to_define()``.
        - `tables` (list): Table specifications (TableSpec or SimpleNamespace).
        - `converted_tables` (dict): table_id -> LaTeX code.

    - **Returns**:
        - `str`: Content with tables injected.
    """
    tables_to_define = section_plan.get_table_ids_to_define()
    if not tables_to_define:
        return content

    table_map = {}
    for tbl in (tables or []):
        tbl_id = tbl.id if hasattr(tbl, "id") else tbl.get("id", "")
        if tbl_id:
            table_map[tbl_id] = tbl

    _converted = converted_tables or {}
    fallback_candidates = _table_fallback_insert_candidates(content)
    used_fallback_indices: set[int] = set()
    fallback_insertions: List[Tuple[int, int]] = []

    for tbl_id in tables_to_define:
        tbl = table_map.get(tbl_id)
        if not tbl:
            continue

        already_pattern = re.compile(
            rf'\\begin{{table\*?}}.*?\\label{{{re.escape(tbl_id)}}}.*?\\end{{table\*?}}',
            re.DOTALL,
        )
        if already_pattern.search(content):
            continue

        env_name = "table*" if getattr(tbl, "wide", False) else "table"

        if tbl_id in _converted:
            table_latex = _converted[tbl_id]
            if f"\\label{{{tbl_id}}}" not in table_latex:
                label_str = f"\\label{{{tbl_id}}}"
                table_latex = re.sub(
                    rf'(\\end{{{env_name}}})',
                    lambda m, ls=label_str: f"{ls}\n{m.group(1)}",
                    table_latex,
                )
        else:
            caption = normalize_caption(getattr(tbl, "caption", "") or tbl_id)
            table_latex = (
                f"\\begin{{{env_name}}}[htbp]\n"
                f"\\centering\n"
                f"\\caption{{{caption}}}\\label{{{tbl_id}}}\n"
                f"\\begin{{tabular}}{{lcc}}\n"
                f"\\hline\n"
                f"Column 1 & Column 2 & Column 3 \\\\\n"
                f"\\hline\n"
                f"-- & -- & -- \\\\\n"
                f"\\hline\n"
                f"\\end{{tabular}}\n"
                f"\\end{{{env_name}}}"
            )

        ref_pattern = re.compile(
            rf'(Table~?\\ref{{{re.escape(tbl_id)}}}[^.]*\.)',
        )
        match = ref_pattern.search(content)
        if match:
            insert_pos = match.end()
            content = content[:insert_pos] + "\n" + table_latex + "\n" + content[insert_pos:]
        else:
            fallback_choice = _choose_table_fallback_candidate(
                tbl_id=tbl_id,
                table=tbl,
                candidates=fallback_candidates,
                used_indices=used_fallback_indices,
            )
            if fallback_choice is not None:
                original_pos = fallback_candidates[fallback_choice][0]
                adjusted_pos = original_pos + sum(
                    length for pos, length in fallback_insertions if pos <= original_pos
                )
                insertion = "\n" + table_latex + "\n"
                content = content[:adjusted_pos] + insertion + content[adjusted_pos:]
                used_fallback_indices.add(fallback_choice)
                fallback_insertions.append((original_pos, len(insertion)))
            else:
                content = content + "\n" + table_latex + "\n"

    return content


def _table_fallback_insert_positions(content: str) -> List[int]:
    """Find prose paragraph ends for spreading tables when refs are absent."""
    return [pos for pos, _paragraph in _table_fallback_insert_candidates(content)]


def _table_fallback_insert_candidates(content: str) -> List[Tuple[int, str]]:
    """Find prose paragraphs that can host missing-ref table insertion."""
    positions: List[Tuple[int, str]] = []
    paragraph_pattern = re.compile(r'(?:^|\n\n)(.*?)(?=\n\n|$)', re.DOTALL)
    for match in paragraph_pattern.finditer(content):
        paragraph = match.group(1).strip()
        if not paragraph:
            continue
        if paragraph.startswith(("\\section", "\\subsection", "\\subsubsection")):
            continue
        if "\\begin{table" in paragraph:
            continue
        positions.append((match.end(1), paragraph))
    return positions


def _choose_table_fallback_candidate(
    tbl_id: str,
    table: Any,
    candidates: List[Tuple[int, str]],
    used_indices: set[int],
) -> Optional[int]:
    """Choose the best prose paragraph for a table without an explicit ref."""
    available = [idx for idx in range(len(candidates)) if idx not in used_indices]
    if not available:
        return None

    caption = getattr(table, "caption", "") or ""
    description = getattr(table, "description", "") or ""
    query_text = " ".join([tbl_id, caption, description])
    query_terms = _table_match_terms(query_text)
    if "overview" in query_terms:
        for idx in available:
            paragraph_terms = _table_match_terms(candidates[idx][1])
            if paragraph_terms & {"setup", "configuration", "benchmark", "benchmarks"}:
                return idx

    best_idx: Optional[int] = None
    best_score = 0
    for idx in available:
        paragraph_terms = _table_match_terms(candidates[idx][1])
        score = len(query_terms & paragraph_terms)
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx is not None and best_score > 0:
        return best_idx
    return available[0]


def _table_match_terms(text: str) -> set[str]:
    """Normalize text into coarse terms for table-to-paragraph matching."""
    terms = set(re.findall(r"[A-Za-z0-9]+", text.lower()))
    expanded = set(terms)
    for term in terms:
        if term in {"vqa", "vqav2", "ok", "okvqa", "gqa"}:
            expanded.add("question")
            expanded.add("answering")
        if term in {"caption", "captioning", "coco", "nocaps"}:
            expanded.add("generation")
            expanded.add("captioning")
        if term in {"retrieval", "flickr", "flickr30k"}:
            expanded.add("retrieval")
        if term in {"overview", "setup", "pre", "training", "pretraining"}:
            expanded.add("setup")
    return expanded
