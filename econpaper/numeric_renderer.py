from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .linting import extract_numeric_uses


NUMERIC_RENDERING_VERSION = "v3.0"
PLACEHOLDER_RE = re.compile(r"\{\{\s*(?P<kind>[A-Za-z_]+)\s*:\s*(?P<slot>[^}]+?)\s*\}\}")

KIND_TO_DISPLAY_TYPE = {
    "coef": "coefficient",
    "coefficient": "coefficient",
    "se": "standard_error",
    "std_error": "standard_error",
    "pvalue": "p_value",
    "p_value": "p_value",
    "n": "n",
    "percent": "percent",
    "percentage": "percent",
    "pp": "percentage_point",
    "percentage_point": "percentage_point",
}


@dataclass
class NumericRenderingIssue:
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
class NumericRenderingResult:
    rendered_text: str
    audit: dict[str, Any]
    status: str = "passed"
    issues: list[NumericRenderingIssue] = field(default_factory=list)

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
        self.issues.append(
            NumericRenderingIssue(
                code=code,
                severity=severity,
                message=message,
                path=path,
                details=details or {},
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": NUMERIC_RENDERING_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "audit": self.audit,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def render_numeric_template(
    template_path: str | Path,
    *,
    evidence_ledger_path: str | Path,
    slots_path: str | Path | None = None,
    allow_raw_numbers: bool = False,
) -> NumericRenderingResult:
    template = Path(template_path)
    result = NumericRenderingResult(
        rendered_text="",
        audit={
            "version": NUMERIC_RENDERING_VERSION,
            "template_path": str(template),
            "evidence_ledger_path": str(evidence_ledger_path),
            "slots_path": str(slots_path) if slots_path else None,
            "resolved_slots": [],
            "unresolved_placeholders": [],
            "raw_numeric_uses": [],
        },
    )
    text = _read_text(template, result)
    ledger = _load_json(Path(evidence_ledger_path), result, "evidence_ledger")
    slots = _load_slots(Path(slots_path), result) if slots_path else {}
    evidence_by_id = _evidence_by_id(ledger)

    if not allow_raw_numbers:
        _check_raw_numbers(text, result)

    rendered_parts: list[str] = []
    cursor = 0
    for match in PLACEHOLDER_RE.finditer(text):
        rendered_parts.append(text[cursor : match.start()])
        replacement = _resolve_placeholder(match, slots, evidence_by_id, ledger, result)
        rendered_parts.append(replacement if replacement is not None else match.group(0))
        cursor = match.end()
    rendered_parts.append(text[cursor:])
    result.rendered_text = "".join(rendered_parts)
    return result


def write_numeric_rendering(
    template_path: str | Path,
    *,
    evidence_ledger_path: str | Path,
    out_dir: str | Path,
    slots_path: str | Path | None = None,
    allow_raw_numbers: bool = False,
) -> NumericRenderingResult:
    result = render_numeric_template(
        template_path,
        evidence_ledger_path=evidence_ledger_path,
        slots_path=slots_path,
        allow_raw_numbers=allow_raw_numbers,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    suffix = Path(template_path).suffix or ".md"
    rendered_name = "rendered" + suffix
    (out_path / rendered_name).write_text(result.rendered_text, encoding="utf-8")
    (internal / "numeric_rendering.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _read_text(path: Path, result: NumericRenderingResult) -> str:
    if not path.exists():
        result.add_issue("template_missing", "hard_block", f"Template does not exist: {path}", path=str(path))
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        result.add_issue("template_not_utf8", "hard_block", f"Template must be UTF-8 readable: {exc}", path=str(path))
        return ""


def _load_json(path: Path, result: NumericRenderingResult, label: str) -> dict[str, Any]:
    if not path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"{label} file does not exist: {path}", path=str(path))
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        result.add_issue(f"{label}_invalid_json", "hard_block", f"Could not parse {label} JSON: {exc}", path=str(path))
        return {}
    if not isinstance(payload, dict):
        result.add_issue(f"{label}_not_object", "hard_block", f"{label} JSON must be an object.", path=str(path))
        return {}
    return payload


def _load_slots(path: Path, result: NumericRenderingResult) -> dict[str, dict[str, Any]]:
    payload = _load_json(path, result, "slots")
    raw_slots = payload.get("slots", payload)
    slots: dict[str, dict[str, Any]] = {}
    if isinstance(raw_slots, dict):
        for key, value in raw_slots.items():
            if isinstance(value, str):
                slots[str(key)] = {"evidence_id": value}
            elif isinstance(value, dict):
                slots[str(key)] = value
    elif isinstance(raw_slots, list):
        for item in raw_slots:
            if not isinstance(item, dict):
                continue
            key = item.get("slot") or item.get("name") or item.get("placeholder")
            if key:
                slots[str(key)] = item
    else:
        result.add_issue("slots_invalid_shape", "hard_block", "slots JSON must be an object or list.", path=str(path))
    return slots


def _evidence_by_id(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = ledger.get("evidence_items", []) if isinstance(ledger, dict) else []
    return {str(item.get("evidence_id")): item for item in items if isinstance(item, dict) and item.get("evidence_id")}


def _check_raw_numbers(text: str, result: NumericRenderingResult) -> None:
    masked = PLACEHOLDER_RE.sub("", text)
    numeric_uses = extract_numeric_uses(masked)
    result.audit["raw_numeric_uses"] = [use.to_dict() for use in numeric_uses]
    for use in numeric_uses:
        result.add_issue(
            "raw_numeric_text",
            "hard_block",
            "Numeric renderer templates must use placeholders instead of raw numeric prose.",
            path=str(result.audit["template_path"]),
            details=use.to_dict(),
        )


def _resolve_placeholder(
    match: re.Match[str],
    slots: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
    ledger: dict[str, Any],
    result: NumericRenderingResult,
) -> str | None:
    kind = match.group("kind").strip().lower()
    slot_id = match.group("slot").strip()
    slot_key = f"{kind}:{slot_id}"
    slot = slots.get(slot_key) or slots.get(slot_id) or {}
    if not slot and slot_id in evidence_by_id:
        slot = {"evidence_id": slot_id}
    if kind == "magnitude":
        return _resolve_magnitude(slot_key, slot_id, slot, evidence_by_id, ledger, result)
    expected_display = KIND_TO_DISPLAY_TYPE.get(kind)
    if not expected_display:
        result.add_issue(
            "unknown_numeric_placeholder_kind",
            "hard_block",
            f"Unknown numeric placeholder kind `{kind}`.",
            details={"placeholder": match.group(0)},
        )
        result.audit["unresolved_placeholders"].append(match.group(0))
        return None
    evidence_id = str(slot.get("evidence_id") or "")
    evidence = evidence_by_id.get(evidence_id)
    if not evidence:
        result.add_issue(
            "unresolved_numeric_placeholder",
            "hard_block",
            f"Could not resolve placeholder `{match.group(0)}` to an evidence item.",
            details={"placeholder": match.group(0), "slot_key": slot_key, "slot": slot},
        )
        result.audit["unresolved_placeholders"].append(match.group(0))
        return None
    actual_display = evidence.get("display_type")
    if actual_display != expected_display:
        result.add_issue(
            "slot_statistic_mismatch",
            "hard_block",
            f"Placeholder `{match.group(0)}` expected `{expected_display}` but evidence item has `{actual_display}`.",
            details={"placeholder": match.group(0), "evidence_id": evidence_id},
        )
        result.audit["unresolved_placeholders"].append(match.group(0))
        return None
    value = _coerce_number(evidence.get("value"))
    if value is None:
        result.add_issue(
            "evidence_value_not_numeric",
            "hard_block",
            f"Evidence item `{evidence_id}` does not contain a numeric value.",
            details={"placeholder": match.group(0), "evidence_id": evidence_id},
        )
        result.audit["unresolved_placeholders"].append(match.group(0))
        return None
    rendered = _format_value(kind, value)
    result.audit["resolved_slots"].append(
        {
            "placeholder": match.group(0),
            "slot_key": slot_key,
            "evidence_id": evidence_id,
            "raw_value": evidence.get("value"),
            "rendered": rendered,
            "display_type": expected_display,
        }
    )
    return rendered


def _resolve_magnitude(
    slot_key: str,
    slot_id: str,
    slot: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
    ledger: dict[str, Any],
    result: NumericRenderingResult,
) -> str | None:
    evidence_id = str(slot.get("coefficient_evidence_id") or slot.get("evidence_id") or "")
    evidence = evidence_by_id.get(evidence_id)
    variable = str(slot.get("variable") or (evidence or {}).get("variable") or slot_id)
    kind = str(slot.get("kind") or "sd_units")
    coefficient = _coerce_number((evidence or {}).get("value"))
    semantics = (ledger.get("variable_semantics") or {}).get(variable, {}) if isinstance(ledger, dict) else {}
    if evidence is None or coefficient is None:
        result.add_issue(
            "unresolved_magnitude_placeholder",
            "hard_block",
            f"Could not resolve magnitude slot `{slot_key}` to a coefficient evidence item.",
            details={"slot": slot},
        )
        result.audit["unresolved_placeholders"].append(f"{{{{{slot_key}}}}}")
        return None
    if kind == "sd_units":
        sd = _coerce_number(semantics.get("sd"))
        if sd in {None, 0}:
            result.add_issue(
                "magnitude_sd_missing",
                "hard_block",
                f"Magnitude slot `{slot_key}` needs a nonzero standard deviation for `{variable}`.",
                details={"variable": variable, "semantics": semantics},
            )
            result.audit["unresolved_placeholders"].append(f"{{{{{slot_key}}}}}")
            return None
        rendered = f"{coefficient / sd:.2f} standard deviations"
    elif kind == "mean_percent":
        mean = _coerce_number(semantics.get("mean"))
        if mean in {None, 0}:
            result.add_issue(
                "magnitude_mean_missing",
                "hard_block",
                f"Magnitude slot `{slot_key}` needs a nonzero mean for `{variable}`.",
                details={"variable": variable, "semantics": semantics},
            )
            result.audit["unresolved_placeholders"].append(f"{{{{{slot_key}}}}}")
            return None
        rendered = f"{coefficient / mean * 100:.1f}% of the mean"
    else:
        result.add_issue(
            "unknown_magnitude_kind",
            "hard_block",
            f"Unknown magnitude kind `{kind}`.",
            details={"slot": slot},
        )
        result.audit["unresolved_placeholders"].append(f"{{{{{slot_key}}}}}")
        return None
    result.audit["resolved_slots"].append(
        {
            "placeholder": f"{{{{{slot_key}}}}}",
            "slot_key": slot_key,
            "evidence_id": evidence_id,
            "raw_value": evidence.get("value"),
            "rendered": rendered,
            "display_type": "magnitude",
            "magnitude_kind": kind,
            "variable": variable,
        }
    )
    return rendered


def _coerce_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", "").replace("%", ""))
        except ValueError:
            return None
    return None


def _format_value(kind: str, value: float) -> str:
    if kind in {"coef", "coefficient", "se", "std_error"}:
        return f"{value:.3f}"
    if kind in {"pvalue", "p_value"}:
        if value < 0.001:
            return "<0.001"
        return f"{value:.3f}"
    if kind == "n":
        return f"{int(round(value)):,}"
    if kind in {"percent", "percentage"}:
        return f"{value:.1f}%"
    if kind in {"pp", "percentage_point"}:
        return f"{value:.1f} percentage points"
    return f"{value}"


def _author_report_text(result: NumericRenderingResult) -> str:
    hard_blocks = [issue for issue in result.issues if issue.severity == "hard_block"]
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Numeric Rendering Status",
        "",
        f"- Status: `{result.status}`",
        f"- Resolved slots: `{len(result.audit.get('resolved_slots', []))}`",
        f"- Unresolved placeholders: `{len(result.audit.get('unresolved_placeholders', []))}`",
        f"- Raw numeric uses in template: `{len(result.audit.get('raw_numeric_uses', []))}`",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    lines.extend([f"- `{issue.code}`: {issue.message}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Rendered Slots", ""])
    if result.audit.get("resolved_slots"):
        for item in result.audit["resolved_slots"]:
            lines.append(f"- `{item['placeholder']}` -> `{item['rendered']}` from `{item['evidence_id']}`")
    else:
        lines.append("- None.")
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Replace raw numeric prose with placeholders and add slot mappings for unresolved placeholders.")
    else:
        lines.append("- Continue to publication tables and claim-ledger gates.")
    return "\n".join(lines) + "\n"
