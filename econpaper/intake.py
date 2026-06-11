from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


AUTHOR_INPUT_NEEDED = "[AUTHOR_INPUT_NEEDED]"
INTAKE_VERSION = "v3.0"


@dataclass
class IntakeIssue:
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
class IntakeBuildResult:
    intake_profile: dict[str, Any]
    status: str = "passed"
    issues: list[IntakeIssue] = field(default_factory=list)
    field_sources: dict[str, str] = field(default_factory=dict)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(IntakeIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": INTAKE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "intake_profile": self.intake_profile,
            "issues": [issue.to_dict() for issue in self.issues],
            "field_sources": self.field_sources,
        }


def build_intake_profile(
    *,
    answers_path: str | Path | None = None,
    spec_path: str | Path | None = None,
    research_context_path: str | Path | None = None,
    literature_notes_path: str | Path | None = None,
    target_venue: str | None = None,
    preferred_contribution: str | None = None,
    project_title: str | None = None,
    field: str | None = None,
) -> IntakeBuildResult:
    result = IntakeBuildResult(intake_profile={})
    spec_payload = _load_structured_file(spec_path, result, source_name="author_spec") if spec_path else {}
    answer_payload = _load_structured_file(answers_path, result, source_name="interview_answers") if answers_path else {}
    payload = _deep_merge(spec_payload, answer_payload)
    cli_overrides = {
        "project": {
            "title_working": project_title,
            "field": field,
            "target_venue": target_venue,
        },
        "contribution_statement": preferred_contribution,
    }
    payload = _deep_merge(payload, _drop_none(cli_overrides))

    field_sources: dict[str, str] = {}
    missing: list[str] = []
    project = _project(payload, field_sources, missing)
    design = _author_declared_design(payload, field_sources, missing)
    timing = _treatment_timing(payload, field_sources, missing)
    institutional_context = _institutional_context(payload, field_sources, missing)
    contribution_statement = _string_field(
        payload,
        ["contribution_statement", "contribution", "preferred_contribution_sentence"],
        "contribution_statement",
        "one-sentence contribution statement",
        field_sources,
        missing,
    )
    research_motivation = _string_field(
        payload,
        ["research_motivation", "motivation"],
        "research_motivation",
        "research motivation",
        field_sources,
        missing,
    )
    magnitude_context = _outcome_magnitude_context(payload, field_sources, missing)
    notes = _notes_payload(
        research_context_path=research_context_path,
        literature_notes_path=literature_notes_path,
        result=result,
    )

    author_asserted_claims = _author_asserted_claims(payload, field_sources)
    profile = {
        "version": INTAKE_VERSION,
        "intake_profile_id": _profile_id(payload, notes),
        "project": project,
        "author_declared_design": design,
        "treatment_timing": timing,
        "institutional_context": institutional_context,
        "contribution_statement": contribution_statement,
        "research_motivation": research_motivation,
        "outcome_magnitude_context": magnitude_context,
        "missing_author_inputs": _dedupe(missing),
        "author_asserted_claims": author_asserted_claims,
        "author_provided_notes": notes,
        "field_sources": field_sources,
        "llm_suggested_prose": [],
    }
    result.intake_profile = profile
    result.field_sources = field_sources
    return result


def write_intake_profile(
    *,
    out_dir: str | Path,
    answers_path: str | Path | None = None,
    spec_path: str | Path | None = None,
    research_context_path: str | Path | None = None,
    literature_notes_path: str | Path | None = None,
    target_venue: str | None = None,
    preferred_contribution: str | None = None,
    project_title: str | None = None,
    field: str | None = None,
) -> IntakeBuildResult:
    result = build_intake_profile(
        answers_path=answers_path,
        spec_path=spec_path,
        research_context_path=research_context_path,
        literature_notes_path=literature_notes_path,
        target_venue=target_venue,
        preferred_contribution=preferred_contribution,
        project_title=project_title,
        field=field,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "intake_profile.json").write_text(
        json.dumps(result.intake_profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (internal / "intake_interview.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_path / "AUTHOR_REPORT.md").write_text(_author_report_text(result), encoding="utf-8")
    return result


def _load_structured_file(path: str | Path | None, result: IntakeBuildResult, *, source_name: str) -> dict[str, Any]:
    if path is None:
        return {}
    source = Path(path)
    if not source.exists():
        result.add_issue("missing_input_file", "hard_block", f"{source_name} file does not exist: {source}", str(source))
        return {}
    try:
        text = source.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        result.add_issue("input_not_utf8", "hard_block", f"{source_name} must be UTF-8 readable: {exc}", str(source))
        return {}
    if source.suffix.lower() in {".yaml", ".yml"}:
        payload = _load_yaml(text, result, source)
    else:
        try:
            payload = json.loads(text)
        except Exception as exc:
            result.add_issue("invalid_json", "hard_block", f"Could not parse {source_name} JSON: {exc}", str(source))
            return {}
    if not isinstance(payload, dict):
        result.add_issue("structured_input_not_object", "hard_block", f"{source_name} must contain an object.", str(source))
        return {}
    return payload


def _load_yaml(text: str, result: IntakeBuildResult, source: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        return _load_simple_yaml(text, result, source)
    try:
        payload = yaml.safe_load(text) or {}
    except Exception as exc:
        result.add_issue("invalid_yaml", "hard_block", f"Could not parse YAML: {exc}", str(source))
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_simple_yaml(text: str, result: IntakeBuildResult, source: Path) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            result.add_issue(
                "yaml_parser_unavailable",
                "hard_block",
                "PyYAML is unavailable and the fallback parser only accepts simple key: value lines.",
                str(source),
            )
            return {}
        key, value = line.split(":", 1)
        payload[key.strip()] = _parse_scalar(value.strip())
    return payload


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none", "~"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _project(payload: dict[str, Any], sources: dict[str, str], missing: list[str]) -> dict[str, str]:
    project_payload = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    return {
        "title_working": _nested_string(
            payload,
            project_payload,
            ["title_working", "title", "project_title"],
            "project.title_working",
            "working title",
            sources,
            missing,
        ),
        "field": _nested_string(payload, project_payload, ["field"], "project.field", "field", sources, missing),
        "target_venue": _nested_string(
            payload,
            project_payload,
            ["target_venue", "venue"],
            "project.target_venue",
            "target venue",
            sources,
            missing,
        ),
    }


def _author_declared_design(payload: dict[str, Any], sources: dict[str, str], missing: list[str]) -> dict[str, Any]:
    design_payload = _first_dict(payload, ["author_declared_design", "declared_design", "design"])
    design_type = _nested_string(
        payload,
        design_payload,
        ["design_type", "declared_design_type"],
        "author_declared_design.design_type",
        "declared design type",
        sources,
        missing,
    )
    declared_by_author = design_type != _needed("declared design type")
    sources["author_declared_design.declared_by_author"] = "derived_from_author_input"
    return {
        "design_type": design_type,
        "declared_by_author": declared_by_author,
        "estimand": _nested_string(
            payload,
            design_payload,
            ["estimand"],
            "author_declared_design.estimand",
            "estimand in author language",
            sources,
            missing,
        ),
        "unit_of_observation": _nested_string(
            payload,
            design_payload,
            ["unit_of_observation", "unit"],
            "author_declared_design.unit_of_observation",
            "unit of observation",
            sources,
            missing,
        ),
        "sample_scope": _nested_string(
            payload,
            design_payload,
            ["sample_scope", "sample"],
            "author_declared_design.sample_scope",
            "sample scope",
            sources,
            missing,
        ),
    }


def _treatment_timing(payload: dict[str, Any], sources: dict[str, str], missing: list[str]) -> dict[str, Any]:
    timing_payload = _first_dict(payload, ["treatment_timing", "timing", "treatment"])
    return {
        "treatment_name": _nested_string(
            payload,
            timing_payload,
            ["treatment_name", "treatment", "exposure", "shock"],
            "treatment_timing.treatment_name",
            "treatment/exposure/shock definition",
            sources,
            missing,
        ),
        "timing_type": _nested_string(
            payload,
            timing_payload,
            ["timing_type", "treatment_timing_type"],
            "treatment_timing.timing_type",
            "treatment timing type",
            sources,
            missing,
        ),
        "anticipation_window": _nested_optional_string(
            timing_payload,
            ["anticipation_window"],
            "treatment_timing.anticipation_window",
            "anticipation window",
            sources,
            missing,
        ),
        "event_time_unit": _nested_optional_string(
            timing_payload,
            ["event_time_unit"],
            "treatment_timing.event_time_unit",
            "event-time unit",
            sources,
            missing,
        ),
    }


def _institutional_context(payload: dict[str, Any], sources: dict[str, str], missing: list[str]) -> list[dict[str, str]]:
    raw = payload.get("institutional_context") or payload.get("institutional_background") or payload.get("context_timeline")
    if not raw:
        missing.append("institutional, historical, or regulatory context")
        sources["institutional_context"] = "author_input_needed"
        return [
            {
                "fact": _needed("institutional, historical, or regulatory context"),
                "source": "author_input_needed",
                "confidence": "needs_source",
            }
        ]
    entries = raw if isinstance(raw, list) else [raw]
    normalized: list[dict[str, str]] = []
    for entry in entries:
        if isinstance(entry, str):
            normalized.append({"fact": entry, "source": "author", "confidence": "author_provided"})
        elif isinstance(entry, dict):
            fact = str(entry.get("fact") or entry.get("text") or "").strip()
            if not fact:
                continue
            normalized.append(
                {
                    "fact": fact,
                    "source": str(entry.get("source") or "author"),
                    "confidence": _confidence(entry.get("confidence")),
                }
            )
    if not normalized:
        missing.append("institutional, historical, or regulatory context")
        sources["institutional_context"] = "author_input_needed"
        return [
            {
                "fact": _needed("institutional, historical, or regulatory context"),
                "source": "author_input_needed",
                "confidence": "needs_source",
            }
        ]
    sources["institutional_context"] = "author_provided"
    return normalized


def _confidence(value: Any) -> str:
    if value in {"author_provided", "needs_source", "external_note"}:
        return str(value)
    return "author_provided"


def _outcome_magnitude_context(
    payload: dict[str, Any],
    sources: dict[str, str],
    missing: list[str],
) -> list[dict[str, Any]]:
    raw = (
        payload.get("outcome_magnitude_context")
        or payload.get("magnitude_context")
        or payload.get("outcomes")
        or payload.get("outcome_variables")
    )
    if not raw:
        missing.append("outcome magnitude context: units, mean, standard deviation, or benchmark")
        sources["outcome_magnitude_context"] = "author_input_needed"
        return []
    entries = raw if isinstance(raw, list) else [raw]
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        variable = str(entry.get("variable") or entry.get("name") or "").strip()
        if not variable:
            variable = _needed("outcome variable name")
            missing.append("outcome variable name")
        unit = str(entry.get("unit") or "").strip()
        if not unit:
            unit = _needed(f"unit for {variable}")
            missing.append(f"unit for {variable}")
        mean = _optional_number(entry.get("mean"))
        sd = _optional_number(entry.get("sd") or entry.get("standard_deviation"))
        if mean is None:
            missing.append(f"mean for {variable}")
        if sd is None:
            missing.append(f"standard deviation for {variable}")
        normalized.append(
            {
                "variable": variable,
                "unit": unit,
                "mean": mean,
                "sd": sd,
                "meaningful_benchmark": entry.get("meaningful_benchmark") or entry.get("benchmark"),
            }
        )
    sources["outcome_magnitude_context"] = "author_provided" if normalized else "author_input_needed"
    return normalized


def _notes_payload(
    *,
    research_context_path: str | Path | None,
    literature_notes_path: str | Path | None,
    result: IntakeBuildResult,
) -> dict[str, Any]:
    notes: dict[str, Any] = {}
    if research_context_path:
        notes["research_context"] = _note_entry(Path(research_context_path), result)
    if literature_notes_path:
        notes["literature_notes"] = _note_entry(Path(literature_notes_path), result)
    return notes


def _note_entry(path: Path, result: IntakeBuildResult) -> dict[str, Any]:
    if not path.exists():
        result.add_issue("missing_note_file", "hard_block", f"Note file does not exist: {path}", str(path))
        return {"path": str(path), "status": "missing"}
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        result.add_issue("note_not_utf8", "hard_block", f"Note file must be UTF-8 readable: {exc}", str(path))
        return {"path": str(path), "status": "not_utf8"}
    return {
        "path": str(path),
        "status": "author_provided",
        "character_count": len(text),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _author_asserted_claims(payload: dict[str, Any], sources: dict[str, str]) -> list[dict[str, Any]]:
    raw = payload.get("author_asserted_claims") or payload.get("author_asserts") or []
    entries = raw if isinstance(raw, list) else [raw]
    claims: list[dict[str, Any]] = []
    for idx, entry in enumerate(entries, start=1):
        if isinstance(entry, str):
            claim = entry.strip()
            reason = ""
            original_status = "author_supplied_without_gate"
        elif isinstance(entry, dict):
            claim = str(entry.get("claim") or entry.get("text") or "").strip()
            reason = str(entry.get("reason") or "").strip()
            original_status = str(entry.get("original_status") or "author_supplied_without_gate").strip()
        else:
            continue
        if not claim:
            continue
        claims.append(
            {
                "claim_id": f"author_asserted_{idx:03d}",
                "claim": claim,
                "original_status": original_status,
                "author_reason": reason,
                "source": "author",
            }
        )
    if claims:
        sources["author_asserted_claims"] = "author_provided"
    return claims


def _string_field(
    payload: dict[str, Any],
    keys: list[str],
    field_name: str,
    missing_label: str,
    sources: dict[str, str],
    missing: list[str],
) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            sources[field_name] = "author_provided"
            return value.strip()
    missing.append(missing_label)
    sources[field_name] = "author_input_needed"
    return _needed(missing_label)


def _nested_string(
    payload: dict[str, Any],
    nested: dict[str, Any],
    keys: list[str],
    field_name: str,
    missing_label: str,
    sources: dict[str, str],
    missing: list[str],
) -> str:
    for key in keys:
        value = nested.get(key)
        if isinstance(value, str) and value.strip():
            sources[field_name] = "author_provided"
            return value.strip()
        root_value = payload.get(key)
        if isinstance(root_value, str) and root_value.strip():
            sources[field_name] = "author_provided"
            return root_value.strip()
    missing.append(missing_label)
    sources[field_name] = "author_input_needed"
    return _needed(missing_label)


def _nested_optional_string(
    nested: dict[str, Any],
    keys: list[str],
    field_name: str,
    missing_label: str,
    sources: dict[str, str],
    missing: list[str],
) -> str | None:
    for key in keys:
        value = nested.get(key)
        if isinstance(value, str) and value.strip():
            sources[field_name] = "author_provided"
            return value.strip()
    missing.append(missing_label)
    sources[field_name] = "author_input_needed"
    return None


def _first_dict(payload: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _optional_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _drop_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _drop_none(item) for key, item in value.items() if item is not None and _drop_none(item) != {}}
    return value


def _profile_id(payload: dict[str, Any], notes: dict[str, Any]) -> str:
    encoded = json.dumps({"payload": payload, "notes": notes}, ensure_ascii=False, sort_keys=True)
    return "intake_" + hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:12]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _needed(label: str) -> str:
    return f"{AUTHOR_INPUT_NEEDED}: {label}"


def _author_report_text(result: IntakeBuildResult) -> str:
    profile = result.intake_profile
    missing = profile.get("missing_author_inputs", [])
    lines = [
        "# AUTHOR_REPORT",
        "",
        "## Intake Status",
        "",
        f"- Status: `{result.status}`",
        f"- Intake profile: `{profile.get('intake_profile_id', '<missing>')}`",
        f"- Missing author inputs: `{len(missing)}`",
        "",
        "## Author-Provided Facts",
        "",
    ]
    provided = [field for field, source in result.field_sources.items() if source == "author_provided"]
    lines.extend([f"- `{field}`" for field in sorted(provided)] if provided else ["- None yet."])
    lines.extend(["", "## Missing Author Inputs", ""])
    lines.extend([f"- {item}" for item in missing] if missing else ["- None."])
    assertions = profile.get("author_asserted_claims", [])
    lines.extend(["", "## Author-Asserted Claims", ""])
    if assertions:
        for item in assertions:
            reason = item.get("author_reason") or "No reason supplied yet."
            lines.append(f"- `{item['claim_id']}` {item['claim']} Original status: `{item['original_status']}`. Reason: {reason}")
    else:
        lines.append("- None.")
    lines.extend(["", "## LLM-Suggested Prose", "", "- None. Intake does not invent institutional, regulatory, or contribution facts."])
    if result.issues:
        lines.extend(["", "## Intake Issues", ""])
        for issue in result.issues:
            lines.append(f"- `{issue.code}` ({issue.severity}): {issue.message}")
    lines.extend(["", "## Next Best Actions", ""])
    if missing:
        lines.append("- Fill the missing author inputs before design profiling and section writing.")
    else:
        lines.append("- Continue to design profiling and evidence-ledger construction.")
    return "\n".join(lines) + "\n"
