from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EXTERNAL_TABLE_IMPORT_VERSION = "v3.0"
SUPPORTED_FORMATS = {"auto", "stata", "r", "python", "latex", "csv"}
CSV_FIELDS = [
    "term",
    "model_id",
    "coef",
    "std_error",
    "p_value",
    "t_stat",
    "nobs",
    "source_format",
    "source_line",
    "parse_confidence",
    "claimable",
    "import_warnings",
]
NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?P<censor>[<>])?\s*(?P<num>[+-]?(?:\d{1,3}(?:,\d{3})+|\d*\.\d+|\d+,\d+|\d+)(?:[eE][+-]?\d+)?|[+-]?\.[0-9]+)"
)


@dataclass
class ExternalTableIssue:
    code: str
    severity: str
    message: str
    path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "details": self.details,
        }


@dataclass
class ImportedModelRow:
    term: str
    model_id: str
    coef: float | None = None
    std_error: float | None = None
    p_value: float | None = None
    t_stat: float | None = None
    nobs: int | None = None
    source_format: str = "auto"
    source_line: str = ""
    parse_confidence: str = "medium"
    claimable: bool = True
    warnings: list[str] = field(default_factory=list)

    def to_csv_row(self) -> dict[str, str]:
        return {
            "term": self.term,
            "model_id": self.model_id,
            "coef": _format_number(self.coef),
            "std_error": _format_number(self.std_error),
            "p_value": _format_number(self.p_value),
            "t_stat": _format_number(self.t_stat),
            "nobs": str(self.nobs) if self.nobs is not None else "",
            "source_format": self.source_format,
            "source_line": self.source_line,
            "parse_confidence": self.parse_confidence,
            "claimable": str(self.claimable).lower(),
            "import_warnings": "; ".join(self.warnings),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "model_id": self.model_id,
            "coef": self.coef,
            "std_error": self.std_error,
            "p_value": self.p_value,
            "t_stat": self.t_stat,
            "nobs": self.nobs,
            "source_format": self.source_format,
            "source_line": self.source_line,
            "parse_confidence": self.parse_confidence,
            "claimable": self.claimable,
            "warnings": self.warnings,
        }


@dataclass
class ExternalTableImportResult:
    rows: list[ImportedModelRow]
    metadata: dict[str, Any]
    status: str = "passed"
    issues: list[ExternalTableIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(
        self,
        code: str,
        severity: str,
        message: str,
        *,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(ExternalTableIssue(code=code, severity=severity, message=message, path=path, details=details or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": EXTERNAL_TABLE_IMPORT_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "metadata": self.metadata,
            "rows": [row.to_dict() for row in self.rows],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def import_external_table(
    input_path: str | Path,
    *,
    source_format: str = "auto",
    model_id: str | None = None,
    include_intercept: bool = False,
) -> ExternalTableImportResult:
    path = Path(input_path)
    result = ExternalTableImportResult(
        rows=[],
        metadata={
            "version": EXTERNAL_TABLE_IMPORT_VERSION,
            "source_name": path.name,
            "source_sha256": _file_hash(path) if path.exists() else None,
            "requested_format": source_format,
            "detected_format": None,
            "model_id": model_id,
            "include_intercept": include_intercept,
            "skipped_rows": [],
        },
    )
    if source_format not in SUPPORTED_FORMATS:
        result.add_issue("unsupported_requested_format", "hard_block", f"Unsupported external table format `{source_format}`.", path=str(path))
        return result
    if not path.exists():
        result.add_issue("external_table_missing", "hard_block", f"External table file does not exist: {path}", path=str(path))
        return result
    text = _read_text(path, result)
    if result.has_hard_blocks:
        return result
    detected = _detect_format(path, text, source_format)
    result.metadata["detected_format"] = detected
    if detected == "latex":
        result.rows = _parse_latex_table(text, result, model_id=model_id, include_intercept=include_intercept)
    elif detected == "csv":
        result.rows = _parse_delimited_table(path, result, model_id=model_id, include_intercept=include_intercept)
    else:
        result.rows = _parse_text_table(text, result, source_format=detected, model_id=model_id, include_intercept=include_intercept)
    _apply_row_quality(result)
    _check_duplicates(result)
    if not result.rows:
        result.add_issue(
            "no_claimable_rows_imported",
            "hard_block",
            "No coefficient rows could be imported. The parser requires an identifiable coefficient table, not arbitrary prose or table paths.",
            path=str(path),
        )
    return result


def write_external_table_import(
    input_path: str | Path,
    *,
    out_dir: str | Path,
    source_format: str = "auto",
    model_id: str | None = None,
    include_intercept: bool = False,
) -> ExternalTableImportResult:
    result = import_external_table(
        input_path,
        source_format=source_format,
        model_id=model_id,
        include_intercept=include_intercept,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    _write_model_table(out_path / "model_table.csv", result.rows)
    (out_path / "model_metadata.json").write_text(json.dumps(_model_metadata(result), ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "external_table_import.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _read_text(path: Path, result: ExternalTableImportResult) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        result.add_issue("external_table_not_utf8", "hard_block", f"External table must be UTF-8 readable: {exc}", path=str(path))
        return ""


def _detect_format(path: Path, text: str, requested: str) -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix in {".tex", ".ltx"} or "\\begin{tabular" in text or ("&" in text and "\\\\" in text):
        return "latex"
    if suffix in {".csv", ".tsv"}:
        return "csv"
    lowered = text.lower()
    if "std. err" in lowered or "p>|" in lowered:
        return "stata" if "|" in text else "python"
    if "pr(>|" in lowered or "estimate" in lowered and "std. error" in lowered:
        return "r"
    if "coef" in lowered and "std err" in lowered:
        return "python"
    return "python"


def _parse_delimited_table(
    path: Path,
    result: ExternalTableImportResult,
    *,
    model_id: str | None,
    include_intercept: bool,
) -> list[ImportedModelRow]:
    try:
        sample = path.read_text(encoding="utf-8-sig")[:4096]
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
    except Exception:
        dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.excel
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle, dialect=dialect)]
    except Exception as exc:
        result.add_issue("external_table_csv_parse_failed", "hard_block", f"Could not parse delimited table: {exc}", path=str(path))
        return []
    imported: list[ImportedModelRow] = []
    for idx, raw in enumerate(rows, start=2):
        normalized = {_normalize_key(key): value for key, value in raw.items()}
        term = _first_present(normalized, ["term", "variable", "row", "label", "name"])
        if not term:
            result.metadata["skipped_rows"].append({"line": idx, "reason": "missing_term"})
            continue
        term = _clean_term(str(term))
        if _is_intercept(term) and not include_intercept:
            result.metadata["skipped_rows"].append({"line": idx, "term": term, "reason": "intercept_skipped"})
            continue
        coef = _parse_optional_number(_first_present(normalized, ["coef", "coefficient", "estimate", "effect"]))
        if coef is None:
            result.metadata["skipped_rows"].append({"line": idx, "term": term, "reason": "missing_coefficient"})
            continue
        p_value = _parse_p_value(_first_present(normalized, ["p_value", "pvalue", "p", "pr_t", "pr_z"]), result, line=idx)
        imported.append(
            ImportedModelRow(
                term=term,
                model_id=str(_first_present(normalized, ["model_id", "model", "spec", "spec_id"]) or model_id or "external_m1"),
                coef=coef,
                std_error=_parse_optional_number(_first_present(normalized, ["std_error", "standard_error", "se", "std_err"])),
                p_value=p_value,
                t_stat=_parse_optional_number(_first_present(normalized, ["t_stat", "t", "z", "z_stat"])),
                nobs=_parse_optional_int(_first_present(normalized, ["nobs", "n_obs", "n", "observations"])),
                source_format="csv",
                source_line=str(idx),
                parse_confidence="high",
            )
        )
    return imported


def _parse_text_table(
    text: str,
    result: ExternalTableImportResult,
    *,
    source_format: str,
    model_id: str | None,
    include_intercept: bool,
) -> list[ImportedModelRow]:
    lines = text.splitlines()
    imported: list[ImportedModelRow] = []
    active = False
    table_index = 1
    observed_rows_after_header = 0
    nobs = _extract_nobs(text)
    for line_no, raw_line in enumerate(lines, start=1):
        line = _normalize_text_line(raw_line)
        if not line.strip():
            if active and observed_rows_after_header:
                active = False
                table_index += 1
            continue
        if _is_text_header(line):
            active = True
            observed_rows_after_header = 0
            continue
        if _is_nobs_line(line):
            if active and observed_rows_after_header:
                active = False
                table_index += 1
            continue
        if not active or _is_separator(line):
            continue
        parsed = _parse_text_coef_line(line)
        if parsed is None:
            if observed_rows_after_header and not _looks_like_continuation(line):
                active = False
                table_index += 1
            continue
        term, numbers, censored_positions = parsed
        observed_rows_after_header += 1
        term = _clean_term(term)
        if _is_intercept(term) and not include_intercept:
            result.metadata["skipped_rows"].append({"line": line_no, "term": term, "reason": "intercept_skipped"})
            continue
        if not numbers:
            continue
        p_value = None
        if len(numbers) >= 4 and 3 not in censored_positions:
            p_value = numbers[3]
        elif len(numbers) >= 4:
            result.add_issue(
                "censored_p_value_not_exact",
                "flag_and_confirm",
                "A censored p-value such as <0.001 was found; the importer does not convert it into an exact p_value.",
                details={"line": line_no, "term": term},
            )
        row = ImportedModelRow(
            term=term,
            model_id=model_id or f"external_m{table_index}",
            coef=numbers[0],
            std_error=numbers[1] if len(numbers) > 1 else None,
            t_stat=numbers[2] if len(numbers) > 2 else None,
            p_value=p_value,
            nobs=nobs,
            source_format=source_format,
            source_line=str(line_no),
            parse_confidence="high" if source_format in {"stata", "r", "python"} else "medium",
        )
        imported.append(row)
    return imported


def _parse_latex_table(
    text: str,
    result: ExternalTableImportResult,
    *,
    model_id: str | None,
    include_intercept: bool,
) -> list[ImportedModelRow]:
    rows = _latex_rows(text)
    model_labels: list[str] = []
    coefficient_rows: list[tuple[int, str, list[str], list[str] | None]] = []
    nobs_by_column: dict[int, int] = {}
    idx = 0
    while idx < len(rows):
        cells = rows[idx]
        if not cells:
            idx += 1
            continue
        first = _clean_latex_cell(cells[0]).strip()
        if not model_labels and len(cells) > 1 and (not first or first.lower() in {"variable", "dependent variable"}):
            labels = [_clean_latex_cell(cell) for cell in cells[1:]]
            if any(labels):
                model_labels = labels
            idx += 1
            continue
        if _is_latex_n_row(first):
            for col_idx, cell in enumerate(cells[1:], start=1):
                value = _parse_optional_int(cell)
                if value is not None:
                    nobs_by_column[col_idx] = value
            idx += 1
            continue
        if first and len(cells) > 1 and any(_cell_has_number(cell) for cell in cells[1:]):
            se_cells: list[str] | None = None
            if idx + 1 < len(rows):
                maybe_se = rows[idx + 1]
                maybe_first = _clean_latex_cell(maybe_se[0]).strip() if maybe_se else ""
                if not maybe_first and any(_is_parenthetical_number_cell(cell) for cell in maybe_se[1:]):
                    se_cells = maybe_se[1:]
                    idx += 1
            coefficient_rows.append((idx + 1, first, cells[1:], se_cells))
        idx += 1
    imported: list[ImportedModelRow] = []
    max_models = max([len(items[2]) for items in coefficient_rows] + [len(model_labels), len(nobs_by_column), 1])
    if not model_labels:
        model_labels = [f"({i})" for i in range(1, max_models + 1)]
    for line_no, term, coef_cells, se_cells in coefficient_rows:
        term = _clean_term(term)
        if _is_intercept(term) and not include_intercept:
            result.metadata["skipped_rows"].append({"line": line_no, "term": term, "reason": "intercept_skipped"})
            continue
        for col_idx in range(1, max_models + 1):
            coef_cell = coef_cells[col_idx - 1] if col_idx - 1 < len(coef_cells) else ""
            coef = _parse_single_cell_number(coef_cell)
            if coef is None:
                continue
            se = None
            if se_cells and col_idx - 1 < len(se_cells):
                se = _parse_single_cell_number(se_cells[col_idx - 1])
            label = model_labels[col_idx - 1] if col_idx - 1 < len(model_labels) else f"({col_idx})"
            row = ImportedModelRow(
                term=term,
                model_id=model_id or _model_id_from_label(label, col_idx),
                coef=coef,
                std_error=se,
                nobs=nobs_by_column.get(col_idx),
                source_format="latex",
                source_line=str(line_no),
                parse_confidence="medium",
            )
            if _cell_has_stars(coef_cell):
                row.warnings.append("significance_stars_present_without_exact_p_value")
                result.add_issue(
                    "stars_without_exact_p_value",
                    "flag_and_confirm",
                    "LaTeX significance stars were detected, but exact p-values are not recoverable from stars alone.",
                    details={"line": line_no, "term": term, "model_id": row.model_id},
                )
            imported.append(row)
    return imported


def _is_text_header(line: str) -> bool:
    lowered = " ".join(line.lower().replace(".", " ").split())
    if "std err" in lowered and ("coef" in lowered or "coefficient" in lowered):
        return True
    if "std error" in lowered and "estimate" in lowered:
        return True
    if "p>|" in line.lower() and ("coef" in lowered or "coefficient" in lowered):
        return True
    return False


def _parse_text_coef_line(line: str) -> tuple[str, list[float], set[int]] | None:
    if "|" in line:
        left, right = line.split("|", 1)
        term = left.strip()
        body = right
    else:
        body = line
        match = NUMBER_RE.search(body)
        if not match:
            return None
        term = body[: match.start()].strip()
    if not term:
        return None
    tokens: list[float] = []
    censored_positions: set[int] = set()
    for idx, match in enumerate(NUMBER_RE.finditer(body)):
        parsed = _parse_number_match(match)
        if parsed is None:
            continue
        value, censored = parsed
        tokens.append(value)
        if censored:
            censored_positions.add(idx)
    return (term, tokens, censored_positions) if tokens else None


def _extract_nobs(text: str) -> int | None:
    patterns = [
        r"Number of obs\s*=\s*([0-9,]+)",
        r"No\.\s*Observations\s*:\s*([0-9,]+)",
        r"\bObservations\s*[:=]\s*([0-9,]+)",
        r"\bN\s*[:=]\s*([0-9,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return _parse_optional_int(match.group(1))
    return None


def _latex_rows(text: str) -> list[list[str]]:
    cleaned_lines: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"(?<!\\)%.*$", "", raw).strip()
        if not line:
            continue
        for command in ["\\toprule", "\\midrule", "\\bottomrule", "\\hline", "\\cline"]:
            if line.startswith(command):
                line = ""
                break
        if line:
            cleaned_lines.append(line)
    joined = "\n".join(cleaned_lines)
    joined = re.sub(r"\\begin\{tabular\*?\}(?:\{[^{}]*\}){1,2}", "", joined)
    joined = re.sub(r"\\end\{tabular\*?\}", "", joined)
    raw_rows = re.split(r"\\\\", joined)
    rows: list[list[str]] = []
    for raw_row in raw_rows:
        row = re.sub(r"\\begin\{tabular\*?\}(?:\{[^{}]*\}){1,2}", "", raw_row)
        row = re.sub(r"\\end\{tabular\*?\}", "", row)
        row = re.sub(r"\\(?:begin|end)\{[^}]+\}", "", row)
        row = re.sub(r"\\(?:toprule|midrule|bottomrule|hline|cline)(?:\{[^}]*\})?", "", row)
        row = row.strip()
        if not row or "&" not in row:
            continue
        rows.append([_clean_latex_cell(cell) for cell in row.split("&")])
    return rows


def _clean_latex_cell(cell: str) -> str:
    cell = cell.replace("\\%", "%")
    cell = cell.replace("\\_", "_")
    cell = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", cell)
    cell = re.sub(r"\\emph\{([^{}]*)\}", r"\1", cell)
    cell = re.sub(r"\\multicolumn\{[^{}]*\}\{[^{}]*\}\{([^{}]*)\}", r"\1", cell)
    cell = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?", "", cell)
    return cell.strip()


def _is_latex_n_row(label: str) -> bool:
    normalized = re.sub(r"[^a-z]+", " ", label.lower()).strip()
    return normalized in {"n", "obs", "observations", "number of observations", "no observations"}


def _cell_has_number(cell: str) -> bool:
    return NUMBER_RE.search(_strip_latex_cell_noise(cell)) is not None


def _is_parenthetical_number_cell(cell: str) -> bool:
    cleaned = _strip_latex_cell_noise(cell).strip()
    return cleaned.startswith("(") and cleaned.endswith(")") and NUMBER_RE.search(cleaned) is not None


def _parse_single_cell_number(cell: str) -> float | None:
    cleaned = _strip_latex_cell_noise(cell)
    matches = [match for match in NUMBER_RE.finditer(cleaned)]
    if len(matches) != 1:
        return None
    parsed = _parse_number_match(matches[0])
    return parsed[0] if parsed else None


def _strip_latex_cell_noise(cell: str) -> str:
    cell = _clean_latex_cell(cell)
    cell = cell.replace("*", "")
    cell = re.sub(r"\[[^\]]*\]", "", cell)
    return cell.strip()


def _cell_has_stars(cell: str) -> bool:
    return "*" in cell


def _model_id_from_label(label: str, idx: int) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", label).strip("_")
    if not cleaned or cleaned.isdigit():
        return f"m{idx}"
    return cleaned


def _apply_row_quality(result: ExternalTableImportResult) -> None:
    for row in result.rows:
        if row.std_error is None and row.p_value is None and row.t_stat is None:
            row.claimable = False
            row.parse_confidence = "low"
            row.warnings.append("coefficient_without_inference_statistics")
            result.add_issue(
                "coefficient_without_inference_statistics",
                "flag_and_confirm",
                "A coefficient was imported without standard error, t/z-statistic, or p-value; treat it as non-claimable until verified.",
                details={"term": row.term, "model_id": row.model_id, "source_line": row.source_line},
            )
        elif row.std_error is None:
            row.warnings.append("standard_error_missing")
            result.add_issue(
                "standard_error_missing",
                "flag_and_confirm",
                "A coefficient was imported without a standard error.",
                details={"term": row.term, "model_id": row.model_id, "source_line": row.source_line},
            )
        elif row.p_value is None:
            row.warnings.append("p_value_missing_or_not_exact")


def _check_duplicates(result: ExternalTableImportResult) -> None:
    seen: set[tuple[str, str]] = set()
    for row in result.rows:
        key = (row.term.lower(), row.model_id.lower())
        if key in seen:
            result.add_issue(
                "duplicate_term_model",
                "hard_block",
                "Duplicate term/model pairs were imported; panel or model identity is ambiguous.",
                details={"term": row.term, "model_id": row.model_id},
            )
        seen.add(key)


def _write_model_table(path: Path, rows: list[ImportedModelRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            if row.claimable:
                writer.writerow(row.to_csv_row())


def _model_metadata(result: ExternalTableImportResult) -> dict[str, Any]:
    models = sorted({row.model_id for row in result.rows if row.claimable})
    return {
        "version": EXTERNAL_TABLE_IMPORT_VERSION,
        "source_name": result.metadata.get("source_name"),
        "detected_format": result.metadata.get("detected_format"),
        "models": {
            model: {
                "label": model,
                "source": result.metadata.get("source_name"),
                "importer": "external_table_importer",
            }
            for model in models
        },
    }


def _author_report_text(result: ExternalTableImportResult) -> str:
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    flags = [issue for issue in result.issues if issue.severity == "flag_and_confirm"]
    claimable = [row for row in result.rows if row.claimable]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## External Table Import Status",
        "",
        f"- Status: `{result.status}`",
        f"- Source: `{result.metadata.get('source_name')}`",
        f"- Detected format: `{result.metadata.get('detected_format')}`",
        f"- Imported coefficient rows: `{len(result.rows)}`",
        f"- Claimable rows written to model_table.csv: `{len(claimable)}`",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Flag-And-Confirm Items", ""])
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in flags] if flags else ["- None."])
    lines.extend(["", "## Imported Rows", ""])
    if result.rows:
        for row in result.rows:
            status = "claimable" if row.claimable else "non-claimable"
            bits = [f"coef={_format_number(row.coef)}"]
            if row.std_error is not None:
                bits.append(f"se={_format_number(row.std_error)}")
            if row.p_value is not None:
                bits.append(f"p={_format_number(row.p_value)}")
            lines.append(f"- `{row.term}` / `{row.model_id}` ({status}): " + ", ".join(bits))
    else:
        lines.append("- None.")
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Fix the external table structure or provide a structured model_table.csv/json.")
    elif flags:
        lines.append("- Review flag-and-confirm items before treating imported rows as manuscript evidence.")
    else:
        lines.append("- Use `model_table.csv` with `econpaper evidence --model-table` or `econpaper write --model-table`.")
    return "\n".join(lines) + "\n"


def _normalize_text_line(line: str) -> str:
    return line.replace("−", "-").replace("–", "-").replace("—", "-")


def _normalize_key(key: str | None) -> str:
    key = str(key or "").strip().lower()
    key = key.replace(".", "_").replace(" ", "_").replace(">|", "")
    key = re.sub(r"[^a-z0-9_]+", "_", key)
    key = re.sub(r"_+", "_", key).strip("_")
    aliases = {
        "std_err": "std_error",
        "std_error": "std_error",
        "stderr": "std_error",
        "standard_error": "std_error",
        "estimate": "estimate",
        "pr_t": "pr_t",
        "pr_z": "pr_z",
        "p_t": "p_value",
        "p_z": "p_value",
    }
    return aliases.get(key, key)


def _first_present(row: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in {None, ""}:
            return value
    return None


def _parse_number_match(match: re.Match[str]) -> tuple[float, bool] | None:
    value = _parse_optional_number(match.group("num"))
    if value is None:
        return None
    return value, bool(match.group("censor"))


def _parse_optional_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"na", "n/a", "nan", "none", "."}:
        return None
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.strip("()[]{}")
    text = text.replace("*", "")
    text = re.sub(r"^[<>]\s*", "", text)
    if "," in text and "." not in text:
        if re.fullmatch(r"[+-]?\d{1,3}(,\d{3})+", text):
            text = text.replace(",", "")
        else:
            text = text.replace(",", ".")
    else:
        text = text.replace(",", "")
    if text.startswith("."):
        text = "0" + text
    if text.startswith("-."):
        text = "-0." + text[2:]
    try:
        return float(text)
    except ValueError:
        return None


def _parse_p_value(value: Any, result: ExternalTableImportResult, *, line: int) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.startswith("<") or text.startswith(">"):
        result.add_issue(
            "censored_p_value_not_exact",
            "flag_and_confirm",
            "A censored p-value was found; the importer does not convert it into an exact p_value.",
            details={"line": line, "value": text},
        )
        return None
    return _parse_optional_number(text)


def _parse_optional_int(value: Any) -> int | None:
    parsed = _parse_optional_number(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _format_number(value: float | int | None) -> str:
    if value is None:
        return ""
    return f"{float(value):.10g}"


def _clean_term(term: str) -> str:
    term = _clean_latex_cell(term)
    term = re.sub(r"\s+", " ", term.strip())
    return term.strip("`'\"")


def _is_intercept(term: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "", term.lower())
    return normalized in {"intercept", "constant", "const", "cons", "_cons"}


def _is_separator(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and set(stripped) <= {"-", "=", "_", "+", "|", " "}


def _is_nobs_line(line: str) -> bool:
    return _extract_nobs(line) is not None


def _looks_like_continuation(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("[") or stripped.startswith("(")


def _file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
