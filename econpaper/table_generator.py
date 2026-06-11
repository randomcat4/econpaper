from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


TABLE_GENERATION_VERSION = "v3.0"


@dataclass
class TableGenerationIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
        }


@dataclass
class TableGenerationResult:
    latex: str
    markdown: str
    audit: dict[str, Any]
    status: str = "passed"
    issues: list[TableGenerationIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(TableGenerationIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TABLE_GENERATION_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "audit": self.audit,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def generate_publication_table(
    *,
    evidence_ledger_path: str | Path,
    variable_labels_path: str | Path | None = None,
    model_metadata_path: str | Path | None = None,
    caption: str = "Main Results",
    label: str = "tab:main_results",
    star_policy: str = "conventional",
) -> TableGenerationResult:
    result = TableGenerationResult(
        latex="",
        markdown="",
        audit={
            "version": TABLE_GENERATION_VERSION,
            "evidence_ledger_path": str(evidence_ledger_path),
            "displayed_cells": [],
            "star_policy": star_policy,
            "caption": caption,
            "label": label,
        },
    )
    ledger = _load_json(Path(evidence_ledger_path), result, "evidence_ledger")
    labels = _load_labels(Path(variable_labels_path), result) if variable_labels_path else {}
    metadata = _load_metadata(Path(model_metadata_path), result) if model_metadata_path else {}
    if star_policy not in {"conventional", "none"}:
        result.add_issue("unknown_star_policy", "hard_block", f"Unknown star policy `{star_policy}`.")
        star_policy = "none"

    table = _table_from_ledger(ledger, labels, metadata, star_policy, result)
    if not table["models"] or not table["variables"]:
        result.add_issue(
            "no_model_table_evidence",
            "hard_block",
            "No model-table coefficient evidence was available for publication-table generation.",
            str(evidence_ledger_path),
        )
        return result
    result.latex = _render_latex(table, caption, label, star_policy)
    result.markdown = _render_markdown(table, star_policy)
    result.audit["models"] = table["models"]
    result.audit["variables"] = table["variables"]
    result.audit["notes"] = table["notes"]
    return result


def write_publication_table(
    *,
    evidence_ledger_path: str | Path,
    out_dir: str | Path,
    variable_labels_path: str | Path | None = None,
    model_metadata_path: str | Path | None = None,
    caption: str = "Main Results",
    label: str = "tab:main_results",
    star_policy: str = "conventional",
    table_name: str = "table_main",
) -> TableGenerationResult:
    result = generate_publication_table(
        evidence_ledger_path=evidence_ledger_path,
        variable_labels_path=variable_labels_path,
        model_metadata_path=model_metadata_path,
        caption=caption,
        label=label,
        star_policy=star_policy,
    )
    out_path = Path(out_dir)
    table_dir = out_path / "tables"
    internal = out_path / "reports" / "internal"
    table_dir.mkdir(parents=True, exist_ok=True)
    internal.mkdir(parents=True, exist_ok=True)
    (table_dir / f"{table_name}.tex").write_text(result.latex, encoding="utf-8")
    (table_dir / f"{table_name}.md").write_text(result.markdown, encoding="utf-8")
    (internal / "table_generation.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_json(path: Path, result: TableGenerationResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}", str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label}: {exc}", str(path))
        return {}
    if not isinstance(payload, dict):
        result.add_issue(f"{label}_not_object", "hard_block", f"{label} must be a JSON object.", str(path))
        return {}
    return payload


def _load_labels(path: Path, result: TableGenerationResult) -> dict[str, str]:
    payload = _load_json(path, result, "variable_labels")
    raw = payload.get("labels", payload)
    if not isinstance(raw, dict):
        result.add_issue("variable_labels_invalid_shape", "hard_block", "Variable labels must be a JSON object.", str(path))
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _load_metadata(path: Path, result: TableGenerationResult) -> dict[str, Any]:
    payload = _load_json(path, result, "model_metadata")
    return payload.get("models", payload) if isinstance(payload.get("models", payload), dict) else {}


def _table_from_ledger(
    ledger: dict[str, Any],
    labels: dict[str, str],
    metadata: dict[str, Any],
    star_policy: str,
    result: TableGenerationResult,
) -> dict[str, Any]:
    artifacts = {item.get("artifact_id"): item for item in ledger.get("artifacts", []) if isinstance(item, dict)}
    cells: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    model_order: list[str] = []
    variable_order: list[str] = []
    for item in ledger.get("evidence_items", []):
        if not isinstance(item, dict):
            continue
        artifact = artifacts.get(item.get("artifact_id"), {})
        if artifact.get("artifact_type") != "model_table":
            continue
        display_type = item.get("display_type")
        if display_type not in {"coefficient", "standard_error", "p_value", "n"}:
            continue
        model = str(item.get("model_id") or "model")
        variable = str(item.get("variable") or item.get("row") or "term")
        if model not in model_order:
            model_order.append(model)
        if variable not in variable_order and display_type != "n":
            variable_order.append(variable)
        cells.setdefault((variable, model), {})[str(display_type)] = item

    table_models = [_model_label(model, metadata.get(model), idx) for idx, model in enumerate(model_order, start=1)]
    notes = _table_notes(model_order, metadata, star_policy)
    table = {
        "models": model_order,
        "model_labels": table_models,
        "variables": variable_order,
        "variable_labels": {variable: labels.get(variable, _humanize(variable)) for variable in variable_order},
        "cells": cells,
        "metadata": metadata,
        "notes": notes,
    }
    for variable in variable_order:
        for model in model_order:
            group = cells.get((variable, model), {})
            coef = group.get("coefficient")
            if not coef:
                continue
            rendered = _format_coef(coef.get("value"), group.get("p_value", {}).get("value"), star_policy)
            result.audit["displayed_cells"].append(
                {
                    "kind": "coefficient",
                    "variable": variable,
                    "model_id": model,
                    "evidence_id": coef.get("evidence_id"),
                    "rendered": rendered,
                }
            )
            se = group.get("standard_error")
            if se:
                result.audit["displayed_cells"].append(
                    {
                        "kind": "standard_error",
                        "variable": variable,
                        "model_id": model,
                        "evidence_id": se.get("evidence_id"),
                        "rendered": f"({_format_decimal(se.get('value'))})",
                    }
                )
    for model in model_order:
        n_item = _first_n_for_model(cells, model)
        if n_item:
            result.audit["displayed_cells"].append(
                {
                    "kind": "n",
                    "variable": "Observations",
                    "model_id": model,
                    "evidence_id": n_item.get("evidence_id"),
                    "rendered": _format_n(n_item.get("value")),
                }
            )
    return table


def _model_label(model_id: str, metadata: Any, idx: int) -> str:
    if isinstance(metadata, dict) and metadata.get("label"):
        return str(metadata["label"])
    return f"({idx})"


def _table_notes(model_order: list[str], metadata: dict[str, Any], star_policy: str) -> list[str]:
    notes = ["Standard errors are shown in parentheses."]
    if star_policy == "conventional":
        notes.append("* p<0.10, ** p<0.05, *** p<0.01.")
    else:
        notes.append("No significance stars are displayed.")
    clusters = sorted(
        {
            str((metadata.get(model) or {}).get("cluster"))
            for model in model_order
            if isinstance(metadata.get(model), dict) and (metadata.get(model) or {}).get("cluster")
        }
    )
    if clusters:
        notes.append("Standard errors are clustered by " + ", ".join(clusters) + ".")
    notes.append("All displayed numeric cells map to evidence_ledger evidence_id values.")
    return notes


def _render_latex(table: dict[str, Any], caption: str, label: str, star_policy: str) -> str:
    align = "l" + "c" * len(table["models"])
    lines = [
        "\\begin{table}[!htbp]\\centering",
        f"\\caption{{{_latex_escape(caption)}}}",
        f"\\label{{{_latex_label(label)}}}",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & " + " & ".join(_latex_escape(label) for label in table["model_labels"]) + " \\\\",
        "\\midrule",
    ]
    for variable in table["variables"]:
        label_text = table["variable_labels"][variable]
        coef_cells = []
        se_cells = []
        for model in table["models"]:
            group = table["cells"].get((variable, model), {})
            coef_cells.append(_format_coef((group.get("coefficient") or {}).get("value"), (group.get("p_value") or {}).get("value"), star_policy))
            se = group.get("standard_error")
            se_cells.append(f"({_format_decimal(se.get('value'))})" if se else "")
        lines.append(_latex_escape(label_text) + " & " + " & ".join(coef_cells) + " \\\\")
        lines.append(" & " + " & ".join(se_cells) + " \\\\")
    n_row = [_format_n((_first_n_for_model(table["cells"], model) or {}).get("value")) for model in table["models"]]
    if any(n_row):
        lines.extend(["\\midrule", "Observations & " + " & ".join(n_row) + " \\\\"])
    fe_row = _fixed_effects_row(table["models"], table["metadata"])
    if fe_row:
        lines.append("Fixed effects & " + " & ".join(_latex_escape(value) for value in fe_row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\begin{minipage}{0.95\\linewidth}", "\\footnotesize"])
    lines.append("Notes: " + " ".join(_latex_escape(note) for note in table["notes"]))
    lines.extend(["\\end{minipage}", "\\end{table}", ""])
    return "\n".join(lines)


def _render_markdown(table: dict[str, Any], star_policy: str) -> str:
    headers = ["Variable", *table["model_labels"]]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for variable in table["variables"]:
        coef_cells = []
        se_cells = []
        for model in table["models"]:
            group = table["cells"].get((variable, model), {})
            coef_cells.append(_format_coef((group.get("coefficient") or {}).get("value"), (group.get("p_value") or {}).get("value"), star_policy))
            se = group.get("standard_error")
            se_cells.append(f"({_format_decimal(se.get('value'))})" if se else "")
        lines.append("| " + " | ".join([table["variable_labels"][variable], *coef_cells]) + " |")
        lines.append("| " + " | ".join(["", *se_cells]) + " |")
    n_row = [_format_n((_first_n_for_model(table["cells"], model) or {}).get("value")) for model in table["models"]]
    if any(n_row):
        lines.append("| " + " | ".join(["Observations", *n_row]) + " |")
    fe_row = _fixed_effects_row(table["models"], table["metadata"])
    if fe_row:
        lines.append("| " + " | ".join(["Fixed effects", *fe_row]) + " |")
    lines.extend(["", "Notes: " + " ".join(table["notes"]), ""])
    return "\n".join(lines)


def _first_n_for_model(cells: dict[tuple[str, str], dict[str, dict[str, Any]]], model: str) -> dict[str, Any] | None:
    for (_variable, model_id), group in cells.items():
        if model_id == model and group.get("n"):
            return group["n"]
    return None


def _fixed_effects_row(models: list[str], metadata: dict[str, Any]) -> list[str]:
    values: list[str] = []
    any_present = False
    for model in models:
        item = metadata.get(model) if isinstance(metadata.get(model), dict) else {}
        value = str(item.get("fixed_effects") or item.get("fixed_effect") or "")
        if value:
            any_present = True
        values.append(value or "")
    return values if any_present else []


def _format_coef(value: Any, p_value: Any, star_policy: str) -> str:
    if value is None:
        return ""
    stars = _stars(p_value) if star_policy == "conventional" else ""
    return _format_decimal(value) + stars


def _format_decimal(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except Exception:
        return ""


def _format_n(value: Any) -> str:
    if value is None:
        return ""
    try:
        return f"{int(round(float(value))):,}"
    except Exception:
        return ""


def _stars(p_value: Any) -> str:
    try:
        p = float(p_value)
    except Exception:
        return ""
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "**"
    if p < 0.10:
        return "*"
    return ""


def _humanize(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("_", " ")).strip().title()


def _latex_escape(value: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
    }
    return "".join(replacements.get(char, char) for char in str(value))


def _latex_label(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9:_.-]+", "_", str(value))


def _author_report_text(result: TableGenerationResult) -> str:
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Table Generation Status",
        "",
        f"- Status: `{result.status}`",
        f"- Displayed cells: `{len(result.audit.get('displayed_cells', []))}`",
        f"- Star policy: `{result.audit.get('star_policy')}`",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Provenance", ""])
    if result.audit.get("displayed_cells"):
        for cell in result.audit["displayed_cells"]:
            lines.append(f"- `{cell['kind']}` `{cell['model_id']}` `{cell['variable']}` -> `{cell['evidence_id']}`")
    else:
        lines.append("- No displayed cells.")
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Build or repair the evidence ledger before publication table generation.")
    else:
        lines.append("- Continue to claim-ledger gates and section writing.")
    return "\n".join(lines) + "\n"
