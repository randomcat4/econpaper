from __future__ import annotations

import json
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
from .run_validation import write_run_validation
from .section_writer import write_sections
from .table_generator import write_publication_table
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
    latex_command: str = "pdflatex",
    model_table_paths: list[str | Path] | None = None,
) -> WritePackResult:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    profile = resolve_venue(venue)
    result = WritePackResult(
        manifest={
            "version": WRITE_VERSION,
            "venue": profile.to_dict(),
            "outputs": {},
            "steps": [],
        }
    )

    _copy_input(intake_profile_path, out_path / "intake_profile.json", result, "intake_profile")
    bibliography = out_path / "bibliography"
    bibliography.mkdir(exist_ok=True)
    copied_refs = _copy_input(refs_path, bibliography / "refs.bib", result, "refs_bib")

    run_validation = write_run_validation(run_dir, out_path)
    result.manifest["steps"].append({"name": "validate_run", "status": run_validation.status})
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
    citation_index = _write_citation_reports(copied_refs, internal, result)
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
    result.manifest["outputs"] = {
        "AUTHOR_REPORT.md": str(out_path / "AUTHOR_REPORT.md"),
        "main.md": str(out_path / "main.md"),
        "main.tex": str(out_path / "main.tex"),
        "main.pdf": str(out_path / "main.pdf") if (out_path / "main.pdf").exists() else None,
        "sections": str(out_path / "sections"),
        "tables": str(out_path / "tables"),
        "reports_internal": str(internal),
    }
    if run_validation.status == "failed" or claims.has_hard_blocks or coherence.has_hard_blocks:
        result.add_issue("pack_has_unresolved_gates", "hard_block", "Manuscript pack was produced, but unresolved hard gates remain.")
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


def _write_citation_reports(refs_path: Path, internal: Path, result: WritePackResult) -> Path:
    keys: list[str] = []
    if refs_path.exists():
        keys = sorted(parse_bibtex_keys(refs_path.read_text(encoding="utf-8")))
    citation_index = {
        "version": WRITE_VERSION,
        "refs_bib_present": refs_path.exists(),
        "citekeys": keys,
        "citation_uses": [],
    }
    citation_safety = {
        "version": WRITE_VERSION,
        "refs_bib_present": refs_path.exists(),
        "citekeys": keys,
        "missing_citekeys": [],
        "cite_needed": [],
        "external_notes_used": [],
        "findings": [],
    }
    if not refs_path.exists():
        result.add_issue("refs_bib_missing", "hard_block", "refs.bib is required for generation mode.")
    path = internal / "citation_index.json"
    path.write_text(json.dumps(citation_index, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal / "citation_safety_report.json").write_text(json.dumps(citation_safety, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


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
