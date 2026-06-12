from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .claim_ledger import write_claim_ledger
from .coherence import write_global_coherence
from .compile_pack import compile_pack
from .design_profiler import write_design_profile
from .evidence import write_evidence_ledger
from .linting import parse_bibtex_keys
from .numeric_renderer import render_numeric_template
from .release_gate import write_release_gate
from .run_validation import write_run_validation
from .section_writer import write_sections
from .table_generator import write_publication_table
from .tiering import TieringResult, write_pack_metrics
from .venue import resolve_venue


WRITE_VERSION = "v3.0"


@dataclass
class WritePackIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class WritePackResult:
    manifest: dict[str, Any]
    status: str = "passed"
    issues: list[WritePackIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(WritePackIssue(code=code, severity=severity, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": WRITE_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "manifest": self.manifest,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def write_manuscript_pack(
    *,
    run_dir: str | Path,
    intake_profile_path: str | Path,
    refs_path: str | Path,
    out_dir: str | Path,
    venue: str | None = None,
    latex_command: str = "auto",
    model_table_paths: list[str | Path] | None = None,
    mode: str = "draft",
    human_eval_path: str | Path | None = None,
) -> WritePackResult:
    if mode not in {"draft", "strict"}:
        raise ValueError("write mode must be 'draft' or 'strict'")
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    profile = resolve_venue(venue)
    result = WritePackResult(
        manifest={
            "version": WRITE_VERSION,
            "venue": profile.to_dict(),
            "mode": mode,
            "outputs": {},
            "steps": [],
        }
    )

    source_intake_profile = Path(intake_profile_path)
    _copy_input(source_intake_profile, out_path / "intake_profile.json", result, "intake_profile")
    bibliography = out_path / "bibliography"
    bibliography.mkdir(exist_ok=True)
    copied_refs = _copy_input(refs_path, bibliography / "refs.bib", result, "refs_bib")

    run_validation = write_run_validation(run_dir, out_path)
    result.manifest["steps"].append({"name": "validate_run", "status": run_validation.status})
    minimal_gate = _write_minimal_intake_gate(out_path / "intake_profile.json", run_validation.to_dict(), internal)
    result.manifest["steps"].append({"name": "minimal_intake_gate", "status": minimal_gate["status"]})
    if minimal_gate["has_hard_blocks"]:
        for issue in minimal_gate["issues"]:
            result.add_issue(str(issue["code"]), "hard_block", str(issue["message"]))
        result.manifest["outputs"] = {
            "AUTHOR_REPORT.md": str(out_path / "AUTHOR_REPORT.md"),
            "reports_internal": str(internal),
        }
        _append_minimal_gate_author_report(out_path, minimal_gate, result=result)
        (internal / "write_pack_manifest.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    evidence = write_evidence_ledger(
        run_dir=run_dir,
        out_dir=out_path,
        intake_profile_path=out_path / "intake_profile.json",
        model_table_paths=model_table_paths,
    )
    result.manifest["steps"].append({"name": "evidence", "status": evidence.status})
    design = write_design_profile(
        intake_profile_path=out_path / "intake_profile.json",
        evidence_ledger_path=out_path / "evidence_ledger.json",
        run_validation_path=internal / "run_validation.json",
        out_dir=out_path,
    )
    result.manifest["steps"].append({"name": "design", "status": design.status})
    citation_index = _write_citation_reports(copied_refs, internal, result, intake_profile_path=source_intake_profile)
    claims = write_claim_ledger(
        evidence_ledger_path=out_path / "evidence_ledger.json",
        intake_profile_path=out_path / "intake_profile.json",
        citation_safety_report_path=internal / "citation_safety_report.json",
        design_profile_path=out_path / "design_profile.json",
        run_validation_path=internal / "run_validation.json",
        out_dir=out_path,
    )
    result.manifest["steps"].append({"name": "claims", "status": claims.status})
    table = write_publication_table(
        evidence_ledger_path=out_path / "evidence_ledger.json",
        out_dir=out_path,
        star_policy=profile.star_policy,
    )
    result.manifest["steps"].append({"name": "tables", "status": table.status})
    sections = write_sections(
        claim_ledger_path=out_path / "claim_ledger.json",
        intake_profile_path=out_path / "intake_profile.json",
        citation_index_path=citation_index,
        table_path=out_path / "tables" / "table_main.tex",
        out_dir=out_path,
    )
    result.manifest["steps"].append({"name": "sections", "status": sections.status})
    numeric_sections_status = _render_numeric_sections(out_path, result)
    result.manifest["steps"].append({"name": "render_numeric_sections", "status": numeric_sections_status})
    coherence = write_global_coherence(
        sections_dir=out_path / "sections",
        claim_ledger_path=out_path / "claim_ledger.json",
        table_paths=[out_path / "tables" / "table_main.tex"],
        out_dir=out_path,
    )
    result.manifest["steps"].append({"name": "coherence", "status": coherence.status})
    compiled = compile_pack(out_path, venue=profile.venue_id, latex_command=latex_command)
    result.manifest["steps"].append({"name": "compile", "status": compiled.status})
    tiering = write_pack_metrics(out_path)
    result.manifest["steps"].append({"name": "tier_metrics", "status": tiering.status, "draft_tier": tiering.draft_tier})
    result.manifest["draft_tier"] = tiering.draft_tier
    result.manifest["outputs"] = {
        "AUTHOR_REPORT.md": str(out_path / "AUTHOR_REPORT.md"),
        "main.md": str(out_path / "main.md"),
        "main.tex": str(out_path / "main.tex"),
        "main.pdf": str(out_path / "main.pdf") if (out_path / "main.pdf").exists() else None,
        "sections": str(out_path / "sections"),
        "tables": str(out_path / "tables"),
        "reports_internal": str(internal),
    }
    if mode == "strict" and tiering.draft_tier != "A":
        result.add_issue(
            "draft_tier_below_strict_target",
            "hard_block",
            f"Strict mode requires Tier A; current pack is Tier {tiering.draft_tier}.",
        )
    if mode == "strict":
        release = write_release_gate(
            pack_dir=out_path,
            human_eval_path=human_eval_path,
            out_dir=out_path / "release_gate",
        )
        result.manifest["steps"].append({"name": "release_gate", "status": release.status})
        result.manifest["outputs"]["release_gate"] = str(out_path / "release_gate")
        for finding in release.findings:
            if finding.tier == "hard_block":
                result.add_issue(f"release_gate_{finding.code}", "hard_block", finding.message)
    if run_validation.status == "failed" or claims.has_hard_blocks or coherence.has_hard_blocks:
        result.add_issue("pack_has_unresolved_gates", "hard_block", "Manuscript pack was produced, but unresolved hard gates remain.")
    _append_tier_author_report(out_path, tiering, mode=mode, result=result)
    (internal / "write_pack_manifest.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _copy_input(source: str | Path, target: Path, result: WritePackResult, label: str) -> Path:
    source_path = Path(source)
    if not source_path.exists():
        result.add_issue(f"{label}_missing", "hard_block", f"Input file does not exist: {source_path}")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    return target


def _write_citation_reports(
    refs_path: Path,
    internal: Path,
    result: WritePackResult,
    *,
    intake_profile_path: Path,
) -> Path:
    keys: list[str] = []
    if refs_path.exists():
        keys = sorted(parse_bibtex_keys(refs_path.read_text(encoding="utf-8")))
    intake = _load_json_for_gate(intake_profile_path)
    note_report = _verified_literature_note_entries(intake, keys, base_dir=intake_profile_path.parent)
    citation_index = {
        "version": WRITE_VERSION,
        "refs_bib_present": refs_path.exists(),
        "citekeys": keys,
        "citation_uses": [],
        "external_notes_used": note_report["external_notes_used"],
        "literature_note_entries": note_report["literature_note_entries"],
    }
    citation_safety = {
        "version": WRITE_VERSION,
        "refs_bib_present": refs_path.exists(),
        "citekeys": keys,
        "missing_citekeys": [],
        "cite_needed": [],
        "external_notes_used": note_report["external_notes_used"],
        "findings": note_report["findings"],
    }
    if not refs_path.exists():
        result.add_issue("refs_bib_missing", "hard_block", "refs.bib is required for generation mode.")
    path = internal / "citation_index.json"
    path.write_text(json.dumps(citation_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "citation_safety_report.json").write_text(json.dumps(citation_safety, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _verified_literature_note_entries(intake: dict[str, Any], citekeys: list[str], *, base_dir: Path) -> dict[str, Any]:
    report = {"external_notes_used": [], "literature_note_entries": [], "findings": []}
    notes = intake.get("author_provided_notes") if isinstance(intake.get("author_provided_notes"), dict) else {}
    meta = notes.get("literature_notes") if isinstance(notes.get("literature_notes"), dict) else None
    if not meta:
        return report
    if meta.get("status") != "author_provided":
        report["findings"].append({"code": "literature_note_not_author_provided", "severity": "flag_and_confirm"})
        return report
    path_value = meta.get("path")
    if not path_value:
        report["findings"].append({"code": "literature_note_path_missing", "severity": "flag_and_confirm"})
        return report
    note_path = Path(str(path_value))
    if not note_path.is_absolute():
        note_path = (base_dir / note_path).resolve()
    if not note_path.exists() or not note_path.is_file():
        report["findings"].append({"code": "literature_note_file_missing", "severity": "flag_and_confirm", "path": str(note_path)})
        return report
    try:
        text = note_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        report["findings"].append({"code": "literature_note_not_utf8", "severity": "flag_and_confirm", "path": str(note_path)})
        return report
    sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected_sha = str(meta.get("sha256") or "")
    if expected_sha and sha != expected_sha:
        report["findings"].append({"code": "literature_note_hash_mismatch", "severity": "flag_and_confirm", "path": str(note_path)})
        return report
    entries = _parse_literature_note_entries(text, citekeys)
    if not entries:
        report["findings"].append(
            {
                "code": "literature_note_no_known_citekey_entries",
                "severity": "flag_and_confirm",
                "path": str(note_path),
            }
        )
        return report
    note_id = "litnote_" + sha[:12]
    for idx, entry in enumerate(entries, start=1):
        entry_id = f"{note_id}_{idx:02d}"
        item = {
            "note_id": entry_id,
            "citekey": entry["citekey"],
            "note": entry["note"],
            "sha256": sha,
            "character_count": len(text),
        }
        report["literature_note_entries"].append(item)
        report["external_notes_used"].append(
            {
                "note_id": entry_id,
                "citekey": entry["citekey"],
                "sha256": sha,
            }
        )
    return report


def _parse_literature_note_entries(text: str, citekeys: list[str]) -> list[dict[str, str]]:
    known = set(citekeys)
    entries: list[dict[str, str]] = []
    pattern = re.compile(r"^\s*(?:[-*]\s*)?\[?@?(?P<key>[A-Za-z0-9_:\-]+)\]?\s*[:\-]\s*(?P<note>.+?)\s*$")
    for raw in text.splitlines():
        match = pattern.match(raw)
        if not match:
            continue
        key = match.group("key")
        note = match.group("note").strip()
        if key not in known or not note:
            continue
        entries.append({"citekey": key, "note": note})
    return entries


def _render_numeric_sections(out_path: Path, result: WritePackResult) -> str:
    sections_dir = out_path / "sections"
    internal = out_path / "reports" / "internal"
    audit: dict[str, Any] = {
        "version": WRITE_VERSION,
        "status": "passed",
        "sections": [],
    }
    evidence_ledger = out_path / "evidence_ledger.json"
    slots = out_path / "slots.json"
    if not sections_dir.exists():
        result.add_issue("sections_missing_for_numeric_rendering", "hard_block", "Cannot render numeric placeholders because sections directory is missing.")
        audit["status"] = "failed"
        (internal / "numeric_rendering_sections.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        return "failed"
    for path in sorted(sections_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "{{" not in text:
            audit["sections"].append({"path": str(path), "status": "skipped", "reason": "no_numeric_placeholders"})
            continue
        rendered = render_numeric_template(
            path,
            evidence_ledger_path=evidence_ledger,
            slots_path=slots,
            allow_raw_numbers=True,
        )
        entry = rendered.to_dict()
        entry["path"] = str(path)
        audit["sections"].append(entry)
        if rendered.has_hard_blocks:
            audit["status"] = "failed"
            result.add_issue(
                "section_numeric_rendering_failed",
                "hard_block",
                f"Numeric placeholders could not be rendered in {path.name}.",
            )
            continue
        path.write_text(rendered.rendered_text, encoding="utf-8")
    (internal / "numeric_rendering_sections.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(audit["status"])


def _write_minimal_intake_gate(intake_path: Path, run_validation: dict[str, Any], internal: Path) -> dict[str, Any]:
    payload = _load_json_for_gate(intake_path)
    issues = _minimal_intake_issues(payload, run_validation, intake_path)
    report = {
        "version": WRITE_VERSION,
        "status": "failed" if issues else "passed",
        "has_hard_blocks": bool(issues),
        "required": {
            "design_checklist": ["estimator", "fixed_effects", "cluster_statement"],
            "variable_registry_roles": ["outcome", "treatment/exposure/shock"],
            "provenance_tags": ["field_sources", "run data_provenance=author_supplied"],
        },
        "issues": issues,
    }
    (internal / "minimal_intake_gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _minimal_intake_issues(intake: dict[str, Any], run_validation: dict[str, Any], intake_path: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if not intake:
        return [
            _gate_issue(
                "minimal_intake_missing",
                "Minimal author intake is required before manuscript writing.",
                intake_path,
            )
        ]
    design = intake.get("author_declared_design") if isinstance(intake.get("author_declared_design"), dict) else {}
    if not _present(design.get("estimator")):
        issues.append(_gate_issue("minimal_design_estimator_missing", "Author-declared design must name the estimator.", intake_path))
    if not _present(design.get("fixed_effects")):
        issues.append(_gate_issue("minimal_design_fixed_effects_missing", "Author-declared design must state fixed effects, even if the statement is 'none'.", intake_path))
    if not _present(design.get("cluster_statement")):
        issues.append(_gate_issue("minimal_design_cluster_missing", "Author-declared design must state the clustering level, even if the statement is 'none'.", intake_path))

    registry = _registry_entries(intake)
    if not registry:
        issues.append(_gate_issue("variable_registry_missing", "Intake must include a variable_registry with roles before numeric prose can be written.", intake_path))
    roles = _registry_roles(registry)
    if not (roles & {"outcome", "dependent_variable", "dv", "y"}):
        issues.append(_gate_issue("variable_registry_outcome_missing", "Variable registry must mark at least one outcome variable.", intake_path))
    if not (roles & {"treatment", "exposure", "shock", "policy", "treated", "treat"}):
        issues.append(_gate_issue("variable_registry_treatment_missing", "Variable registry must mark at least one treatment/exposure/shock variable.", intake_path))
    registered = {entry["name"] for entry in registry if _present(entry.get("name"))}
    outcome_role_names = {entry["name"] for entry in registry if _role_tokens(entry.get("role")) & {"outcome", "dependent_variable", "dv", "y"}}
    for variable in _declared_outcome_variables(intake):
        if variable not in registered or variable not in outcome_role_names:
            issues.append(_gate_issue("outcome_variable_role_missing", f"Outcome `{variable}` must be registered with role=outcome.", intake_path))
    treatment_variable = _treatment_variable(intake)
    if treatment_variable and treatment_variable not in registered:
        issues.append(_gate_issue("treatment_variable_role_missing", f"Treatment variable `{treatment_variable}` must appear in variable_registry.", intake_path))

    field_sources = intake.get("field_sources") if isinstance(intake.get("field_sources"), dict) else {}
    if not field_sources:
        issues.append(_gate_issue("intake_provenance_tags_missing", "Intake must include field_sources provenance tags for author-provided facts.", intake_path))
    for key in [
        "author_declared_design.design_type",
        "author_declared_design.estimator",
        "author_declared_design.fixed_effects",
        "author_declared_design.cluster_statement",
        "variable_registry",
    ]:
        if field_sources and field_sources.get(key) in {None, "", "author_input_needed"}:
            issues.append(_gate_issue("intake_provenance_tag_missing", f"Missing author-provided provenance tag for `{key}`.", intake_path))
    if run_validation.get("data_provenance") != "author_supplied":
        issues.append(
            _gate_issue(
                "run_data_provenance_not_author_supplied",
                "Run validation must report data_provenance=author_supplied before manuscript writing.",
                Path(str(run_validation.get("run_dir") or "")) / "provenance.yaml",
            )
        )
    return issues


def _append_minimal_gate_author_report(pack_dir: Path, gate: dict[str, Any], *, result: WritePackResult) -> None:
    report_path = pack_dir / "AUTHOR_REPORT.md"
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else "# AUTHOR_REPORT\n"
    hard_blocks = gate.get("issues", [])
    lines = [
        existing.rstrip(),
        "",
        "## Minimal Intake Gate",
        "",
        f"- Status: `{gate.get('status')}`",
        f"- Write status: `{result.status}`",
        "- Manuscript prose generated: `false`",
        "",
        "## Non-Overridable Hard Blocks",
        "",
    ]
    lines.extend([f"- `{issue['code']}`: {issue['message']}" for issue in hard_blocks] if hard_blocks else ["- None."])
    lines.extend(["", "## Next Best Actions", ""])
    if hard_blocks:
        lines.append("- Fill the minimal design checklist, variable roles, and provenance tags, then rerun `econpaper write`.")
    else:
        lines.append("- Minimal intake gate passed.")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_json_for_gate(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _gate_issue(code: str, message: str, path: Path) -> dict[str, str]:
    return {"code": code, "severity": "hard_block", "message": message, "path": str(path)}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and not value.strip().startswith("[AUTHOR_INPUT_NEEDED]")
    if isinstance(value, list | tuple | set):
        return any(_present(item) for item in value)
    return True


def _registry_entries(intake: dict[str, Any]) -> list[dict[str, str]]:
    raw = intake.get("variable_registry") if isinstance(intake, dict) else []
    entries = raw if isinstance(raw, list) else []
    normalized: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or entry.get("variable") or "").strip()
        role = str(entry.get("role") or entry.get("semantic_role") or "").strip()
        if not _present(name) or not _present(role):
            continue
        normalized.append({"name": name, "role": role})
    return normalized


def _registry_roles(entries: list[dict[str, str]]) -> set[str]:
    roles: set[str] = set()
    for entry in entries:
        roles.update(_role_tokens(entry.get("role")))
    return roles


def _role_tokens(role: Any) -> set[str]:
    text = str(role or "").lower()
    return {token for token in re.split(r"[^a-z0-9_]+", text) if token}


def _declared_outcome_variables(intake: dict[str, Any]) -> list[str]:
    variables: list[str] = []
    for entry in intake.get("outcome_magnitude_context", []) if isinstance(intake, dict) else []:
        if isinstance(entry, dict) and _present(entry.get("variable")):
            variables.append(str(entry["variable"]))
    return variables


def _treatment_variable(intake: dict[str, Any]) -> str | None:
    timing = intake.get("treatment_timing") if isinstance(intake.get("treatment_timing"), dict) else {}
    value = timing.get("treatment_variable")
    return str(value).strip() if _present(value) else None


def _append_tier_author_report(pack_dir: Path, tiering: TieringResult, *, mode: str, result: WritePackResult) -> None:
    report_path = pack_dir / "AUTHOR_REPORT.md"
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else "# AUTHOR_REPORT\n"
    metrics = tiering.metrics
    tier_a_blockers = list(metrics.get("tier_a_blockers", []))
    floor_requests = metrics.get("floor_section_requests", {}) if isinstance(metrics.get("floor_section_requests"), dict) else {}
    provenance = metrics.get("provenance") if isinstance(metrics.get("provenance"), dict) else {}
    lines = [
        existing.rstrip(),
        "",
        "## Tier Status",
        "",
        f"- Write mode: `{mode}`",
        f"- Current reachable tier: `Tier {tiering.draft_tier}`",
        "- Strict/release target: `Tier A`",
        f"- Pack status: `{result.status}`",
        f"- Floor sections: `{metrics.get('sections_floor_count', 0)}`",
        f"- EvidencePack status: `{metrics.get('evidence_pack_status', 'unknown')}`",
        f"- Data provenance: `{provenance.get('data_provenance', 'unknown')}`",
        "",
        "## Tier A Blockers",
        "",
    ]
    lines.extend([f"- `{code}`" for code in tier_a_blockers] if tier_a_blockers else ["- None."])
    lines.extend(["", "## Author Inputs Needed For Tier A", ""])
    author_requests = _author_tier_requests(metrics, floor_requests)
    lines.extend([f"- {item}" for item in author_requests] if author_requests else ["- None from author input; remaining blockers are machine evidence or validation gates."])
    lines.extend(["", "## Evidence Requests For Tier A", ""])
    evidence_requests = _evidence_tier_requests(metrics)
    lines.extend([f"- {item}" for item in evidence_requests] if evidence_requests else ["- None."])
    lines.extend(["", "## Non-Overridable Gates", ""])
    non_overridable = _non_overridable_tier_requests(metrics)
    lines.extend([f"- {item}" for item in non_overridable] if non_overridable else ["- None currently flagged."])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _author_tier_requests(metrics: dict[str, Any], floor_requests: dict[str, Any]) -> list[str]:
    requests: list[str] = []
    for section in metrics.get("missing_core_sections") or []:
        requests.append(f"Provide or regenerate required core section `{section}`.")
    for section in metrics.get("floor_sections") or []:
        section_requests = floor_requests.get(section) if isinstance(floor_requests, dict) else None
        if isinstance(section_requests, list) and section_requests:
            for item in section_requests:
                requests.append(f"`{section}`: {item}")
        else:
            requests.append(f"`{section}`: replace visible floor with author-confirmed prose or inputs.")
    blockers = set(metrics.get("tier_a_blockers") or [])
    if "words_total_below_6000" in blockers:
        requests.append("Expand the manuscript to a complete journal draft; Tier A currently requires at least 6000 non-heading words.")
    if "citation_integrity_below_1_0" in blockers:
        requests.append("Supply verified literature notes/citekeys for every citation-bearing claim.")
    if "verified_literature_notes_missing" in blockers:
        requests.append("Supply verified literature notes before allowing Tier A related-work or positioning prose.")
    if "design_gate_not_pass" in blockers:
        requests.append("Resolve design-profile or coherence diagnostics, including any author-confirmed identification assumptions.")
    if "public_path_leaks_present" in blockers:
        requests.append("Remove public references to internal paths, file names, or generated artifact locations from prose.")
    return _dedupe(requests)


def _evidence_tier_requests(metrics: dict[str, Any]) -> list[str]:
    requests: list[str] = []
    missing = metrics.get("did_tier_a_missing_artifacts") or []
    if missing:
        requests.append("Produce DID Tier A EvidencePack artifacts: " + ", ".join(f"`{item}`" for item in missing) + ".")
    incomplete = metrics.get("did_tier_a_incomplete_artifacts") or []
    if incomplete:
        requests.append("Repair incomplete DID Tier A artifact content: " + ", ".join(f"`{item}`" for item in incomplete) + ".")
    b_incomplete = metrics.get("did_tier_b_incomplete_artifacts") or []
    if b_incomplete:
        requests.append("Repair incomplete DID Tier B artifact content before relying on draft Tier B: " + ", ".join(f"`{item}`" for item in b_incomplete) + ".")
    blockers = set(metrics.get("tier_a_blockers") or [])
    if "evidence_coverage_below_0_80" in blockers:
        requests.append("Bind at least 80% of EvidencePack evidence items to claim-ledger evidence_refs or remove non-claimable evidence.")
    if metrics.get("evidence_pack_status") != "passed":
        requests.append("Repair EvidencePack v2 validation issues before any tier upgrade.")
    return _dedupe(requests)


def _non_overridable_tier_requests(metrics: dict[str, Any]) -> list[str]:
    blockers = set(metrics.get("tier_a_blockers") or [])
    provenance = metrics.get("provenance") if isinstance(metrics.get("provenance"), dict) else {}
    requests: list[str] = []
    if "evidence_pack_invalid" in blockers:
        requests.append("Invalid EvidencePack cannot be overridden by prose; regenerate or repair the pack.")
    if metrics.get("did_tier_b_missing_artifacts"):
        requests.append("Tier B cannot be labeled as Tier A; missing DID Tier B artifacts keep the pack below the draft evidence boundary.")
    if metrics.get("did_tier_b_incomplete_artifacts"):
        requests.append("Artifact type labels cannot override incomplete DID Tier B artifact content.")
    if provenance.get("data_provenance") != "author_supplied":
        requests.append("Release requires data_provenance=author_supplied; synthetic or unknown provenance cannot be released.")
    return _dedupe(requests)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
