#!/usr/bin/env python
"""Standalone runner for economics and finance EasyPaper jobs."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from easypaper import EasyPaper  # noqa: E402
from src.agents.metadata_agent.artifact_manifest import (  # noqa: E402
    NormalizedArtifactManifest,
    load_artifact_manifest,
)
from src.agents.metadata_agent.metadata_utils import resolve_direct_metadata_paths  # noqa: E402
from src.agents.metadata_agent.models import PaperGenerationRequest, PaperGenerationResult  # noqa: E402
from src.agents.metadata_agent.skill4econ_export_bundle import export_skill4econ_run_bundle  # noqa: E402
from src.config.easypaper_config import build_app_config, write_redacted_app_config  # noqa: E402

API_KEY_ENV_NAMES = ("KIMI_API_KEY", "MOONSHOT_API_KEY", "OPENAI_API_KEY")
BASE_URL_ENV_NAMES = ("KIMI_BASE_URL", "MOONSHOT_BASE_URL", "OPENAI_BASE_URL")
MODEL_ENV_NAMES = ("KIMI_MODEL", "MOONSHOT_MODEL", "OPENAI_MODEL")
REPORT_FILENAMES = {
    "claim_gate_report": "claim_gate_report.json",
    "artifact_usage_report": "artifact_usage_report.json",
    "reviewer_attack_pack_json": "reviewer_attack_pack.json",
    "reviewer_attack_pack_markdown": "reviewer_attack_pack.md",
}
VENUE_FILES = {
    "aer": "aer.yaml",
    "american-economic-review": "aer.yaml",
    "american economic review": "aer.yaml",
    "jfe": "jfe.yaml",
    "journal-of-financial-economics": "jfe.yaml",
    "journal of financial economics": "jfe.yaml",
    "qje": "qje.yaml",
    "quarterly-journal-of-economics": "qje.yaml",
    "quarterly journal of economics": "qje.yaml",
}


def _first_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _write_event(events_path: Path, payload: dict[str, Any]) -> None:
    with events_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest_to_json(manifest: NormalizedArtifactManifest | None) -> dict[str, Any]:
    if manifest is None:
        return {"version": None, "materials_root": None, "figures": [], "tables": []}

    def _item(item) -> dict[str, Any]:
        return {
            "id": item.id,
            "path": item.path,
            "resolved_path": item.resolved_path.as_posix(),
            "latex_path": item.latex_path,
            "section": item.section,
            "caption": item.caption,
            "kind": item.kind,
            "semantic_role": item.semantic_role,
            "target_type": item.target_type,
            "caption_mode": item.caption_mode,
            "data_hash": item.data_hash,
            "code_hash": item.code_hash,
            "title": item.title,
            "extra": item.extra,
        }

    return {
        "version": manifest.version,
        "materials_root": manifest.materials_root.as_posix(),
        "source_agent": manifest.source_agent,
        "figures": [_item(item) for item in manifest.figures],
        "tables": [_item(item) for item in manifest.tables],
    }


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Request YAML must contain an object: {path}")
    return raw


def _resolve_request_payload(
    request_path: Path,
    *,
    repo_root: Path,
    output_dir: Path,
    venue: str | None,
    compile_pdf: bool | None,
) -> dict[str, Any]:
    raw = _load_yaml(request_path)
    if venue:
        raw["venue"] = venue
    if compile_pdf is not None:
        raw["compile_pdf"] = compile_pdf
    raw["output_dir"] = str(output_dir)
    raw["save_output"] = True
    raw.setdefault("enable_figure_supplementation", False)
    return resolve_direct_metadata_paths(raw, request_path.parent, repo_root)


def _resolve_manifest(
    request_payload: dict[str, Any],
    *,
    repo_root: Path,
) -> NormalizedArtifactManifest | None:
    manifest_path = request_payload.get("artifact_manifest_path") or request_payload.get("figures_manifest")
    if not manifest_path:
        return None
    return load_artifact_manifest(manifest_path, repo_root=repo_root)


def _maybe_export_skill4econ_bundle(
    request_payload: dict[str, Any],
    *,
    output_dir: Path,
    skill4econ_run_dir: str | None,
    strict: bool,
) -> dict[str, Any] | None:
    if not skill4econ_run_dir:
        return None
    export_dir = output_dir / "skill4econ_bundle"
    result = export_skill4econ_run_bundle(
        skill4econ_run_dir,
        export_dir,
        strict=strict,
    )
    request_payload["artifact_manifest_path"] = str(result.artifact_manifest_path)
    return result.to_summary()


def _load_venue_config(venue: str | None, *, repo_root: Path) -> dict[str, Any]:
    if not venue:
        return {}
    key = str(venue).strip().lower()
    filename = VENUE_FILES.get(key)
    if not filename:
        filename = VENUE_FILES.get(key.replace("_", "-"))
    if not filename:
        return {}
    path = repo_root / "src" / "skills" / "builtin" / "venues" / filename
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    config = raw.get("venue_config")
    return dict(config) if isinstance(config, dict) else {}


def _resolve_runtime_value(
    explicit: str | None,
    env_names: tuple[str, ...],
    *,
    name: str,
    allow_dummy: bool,
) -> str:
    value = str(explicit or "").strip() or _first_env(env_names)
    if value:
        return value
    if allow_dummy:
        return f"mock-{name}"
    env_hint = ", ".join(env_names)
    raise ValueError(f"{name} is required. Pass --{name.replace('_', '-')} or set one of: {env_hint}")


def _normalize_section_id(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _section_text(metadata, section_id: str) -> str:
    values = {
        "introduction": metadata.idea_hypothesis,
        "data": metadata.data,
        "empirical_strategy": metadata.empirical_strategy or metadata.method,
        "results": metadata.results or metadata.experiments,
        "robustness": metadata.robustness or "Robustness checks are specified in the request.",
        "conclusion": metadata.results or metadata.idea_hypothesis,
    }
    return str(values.get(section_id, "") or f"{section_id.replace('_', ' ').title()} content.")


def _artifact_label_variants(artifact_id: str) -> set[str]:
    label = str(artifact_id or "").strip()
    if not label:
        return set()
    return {label, label.replace(":", "_"), label.replace("_", ":")}


def _figure_blocks_for_section(metadata, section_id: str) -> list[str]:
    blocks: list[str] = []
    for fig in metadata.figures:
        fig_section = _normalize_section_id(getattr(fig, "section_type", None) or getattr(fig, "section", ""))
        if fig_section != section_id:
            continue
        figure_path = str(getattr(fig, "derived_file_path", None) or getattr(fig, "file_path", "") or fig.id)
        figure_path = figure_path.replace("\\", "/")
        blocks.append(
            "\n".join(
                [
                    "\\begin{figure}[tbp]",
                    "\\centering",
                    f"\\includegraphics[width=0.82\\linewidth]{{{figure_path}}}",
                    f"\\caption{{{fig.caption}}}\\label{{{fig.id}}}",
                    "\\end{figure}",
                ]
            )
        )
    return blocks


def _table_blocks_for_section(metadata, section_id: str) -> list[str]:
    blocks: list[str] = []
    for table in metadata.tables:
        table_section = _normalize_section_id(getattr(table, "section_type", None) or getattr(table, "section", ""))
        if table_section != section_id:
            continue
        table_path = str(getattr(table, "file_path", "") or table.id).replace("\\", "/")
        blocks.append(
            "\n".join(
                [
                    "\\begin{table}[tbp]",
                    "\\centering",
                    f"\\input{{{table_path}}}",
                    f"\\caption{{{table.caption}}}\\label{{{table.id}}}",
                    "\\end{table}",
                ]
            )
        )
    return blocks


def _mock_result(metadata, output_dir: Path, *, venue_config: dict[str, Any]) -> PaperGenerationResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    main_tex = output_dir / "main.tex"
    required_sections = venue_config.get("required_sections") or [
        "Introduction",
        "Data",
        "Empirical Strategy",
        "Results",
        "Robustness",
        "Conclusion",
    ]
    author = "Anonymous Manuscript" if venue_config.get("anonymous") else "Author Names"
    venue_notes = [
        f"% Venue: {venue_config.get('name', metadata.venue or 'unknown')}",
        f"% anonymous: {bool(venue_config.get('anonymous', False))}",
        f"% double_spacing: {bool(venue_config.get('double_spacing', False))}",
    ]
    if venue_config.get("min_font_pt") is not None:
        venue_notes.append(f"% min_font_pt: {venue_config.get('min_font_pt')}")
    section_blocks: list[str] = []
    for title in required_sections:
        section_id = _normalize_section_id(title)
        body = _section_text(metadata, section_id)
        block_parts = [f"\\section{{{title}}}", body]
        block_parts.extend(_figure_blocks_for_section(metadata, section_id))
        block_parts.extend(_table_blocks_for_section(metadata, section_id))
        section_blocks.append("\n\n".join(part for part in block_parts if part))
    latex = (
        "\\documentclass{article}\n"
        + "\n".join(venue_notes)
        + "\n"
        "\\begin{document}\n"
        f"\\title{{{metadata.title}}}\n"
        f"\\author{{{author}}}\n"
        "\\maketitle\n"
        + "\n\n".join(section_blocks)
        + "\n"
        "\\end{document}\n"
    )
    main_tex.write_text(latex, encoding="utf-8")
    (output_dir / "references.bib").write_text("\n".join(metadata.references), encoding="utf-8")
    return PaperGenerationResult(
        status="ok",
        paper_title=metadata.title,
        latex_content=latex,
        output_path=str(output_dir),
        total_word_count=len(latex.split()),
    )


def _report_path_map(output_dir: Path) -> dict[str, Path]:
    return {key: output_dir / filename for key, filename in REPORT_FILENAMES.items()}


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _normalized_artifact_rows(manifest: NormalizedArtifactManifest | None) -> list[dict[str, Any]]:
    if manifest is None:
        return []
    rows: list[dict[str, Any]] = []
    for item in [*manifest.figures, *manifest.tables]:
        rows.append(
            {
                "id": item.id,
                "kind": item.kind,
                "section": item.section,
                "path": item.path,
                "resolved_path": item.resolved_path.as_posix(),
                "latex_path": item.latex_path,
                "caption": item.caption,
                "caption_mode": item.caption_mode,
                "semantic_role": item.semantic_role,
                "target_type": item.target_type,
                "data_hash": item.data_hash,
                "code_hash": item.code_hash,
                "exists": item.resolved_path.is_file(),
            }
        )
    return rows


def _artifact_is_used(row: dict[str, Any], main_tex: str) -> bool:
    for label in _artifact_label_variants(str(row.get("id") or "")):
        if f"\\label{{{label}}}" in main_tex or label in main_tex:
            return True
    latex_path = str(row.get("latex_path") or "").replace("\\", "/")
    path = str(row.get("path") or "").replace("\\", "/")
    return bool((latex_path and latex_path in main_tex) or (path and path in main_tex))


def _summarize_skill4econ_run_dir(run_dir: str | None) -> dict[str, Any]:
    if not run_dir:
        return {"path": None, "provided": False, "exists": None, "files": []}
    path = Path(run_dir).expanduser().resolve()
    files: list[str] = []
    if path.is_dir():
        for child in sorted(p for p in path.rglob("*") if p.is_file())[:50]:
            files.append(child.relative_to(path).as_posix())
    return {
        "path": str(path),
        "provided": True,
        "exists": path.is_dir(),
        "files": files,
    }


def _build_artifact_usage_report(
    *,
    manifest: NormalizedArtifactManifest | None,
    main_tex: str,
    strict: bool,
    skill4econ_run_dir: str | None,
) -> dict[str, Any]:
    rows = _normalized_artifact_rows(manifest)
    for row in rows:
        row["used_in_main_tex"] = _artifact_is_used(row, main_tex)
        row["has_provenance"] = bool(row.get("data_hash") and row.get("code_hash"))

    missing_files = [row["id"] for row in rows if not row.get("exists")]
    unused_artifacts = [row["id"] for row in rows if not row.get("used_in_main_tex")]
    missing_provenance = [
        row["id"]
        for row in rows
        if row.get("semantic_role") in {"result_figure", "result_table", "result_plot"}
        and not row.get("has_provenance")
    ]
    blocking_issues: list[str] = []
    skill4econ = _summarize_skill4econ_run_dir(skill4econ_run_dir)
    if strict and manifest is None:
        blocking_issues.append("strict_artifacts_requires_manifest")
    if strict and missing_files:
        blocking_issues.append("artifact_files_missing")
    if strict and unused_artifacts:
        blocking_issues.append("manifest_artifacts_unused_in_main_tex")
    if strict and missing_provenance:
        blocking_issues.append("empirical_artifacts_missing_provenance")
    if strict and skill4econ["provided"] and not skill4econ["exists"]:
        blocking_issues.append("skill4econ_run_dir_missing")

    return {
        "status": "fail" if blocking_issues else "pass",
        "strict": bool(strict),
        "summary": {
            "manifest_present": manifest is not None,
            "total_artifacts": len(rows),
            "figures": len(manifest.figures) if manifest else 0,
            "tables": len(manifest.tables) if manifest else 0,
            "used_artifacts": len(rows) - len(unused_artifacts),
            "unused_artifacts": unused_artifacts,
            "missing_files": missing_files,
            "missing_provenance": missing_provenance,
        },
        "skill4econ_run_dir": skill4econ,
        "artifacts": rows,
        "blocking_issues": blocking_issues,
    }


def _extract_claims(metadata) -> list[dict[str, Any]]:
    fields = [
        ("idea_hypothesis", "research_claim"),
        ("empirical_strategy", "identification_claim"),
        ("data", "data_claim"),
        ("results", "result_claim"),
        ("robustness", "robustness_claim"),
    ]
    claims: list[dict[str, Any]] = []
    for field, claim_type in fields:
        value = str(getattr(metadata, field, "") or "").strip()
        if not value:
            continue
        claims.append(
            {
                "field": field,
                "claim_type": claim_type,
                "text": value,
            }
        )
    return claims


def _artifact_evidence_ids(manifest: NormalizedArtifactManifest | None) -> list[str]:
    evidence_ids: list[str] = []
    for row in _normalized_artifact_rows(manifest):
        if row.get("data_hash") and row.get("code_hash"):
            evidence_ids.append(str(row["id"]))
    return evidence_ids


def _build_claim_gate_report(
    *,
    metadata,
    manifest: NormalizedArtifactManifest | None,
    main_tex: str,
    strict: bool,
) -> dict[str, Any]:
    claims = _extract_claims(metadata)
    evidence_ids = _artifact_evidence_ids(manifest)
    result_claims = [claim for claim in claims if claim["claim_type"] in {"result_claim", "robustness_claim"}]
    blocking_issues: list[str] = []
    warnings: list[str] = []
    if strict and result_claims and not evidence_ids:
        blocking_issues.append("result_claims_without_artifact_evidence")
    if strict and not main_tex.strip():
        blocking_issues.append("main_tex_missing_for_claim_gate")
    if not evidence_ids:
        warnings.append("no_manifest_artifact_evidence")

    for claim in claims:
        if evidence_ids and claim["claim_type"] in {"result_claim", "robustness_claim", "data_claim"}:
            claim["evidence_artifacts"] = list(evidence_ids)
            claim["status"] = "supported"
        elif claim["claim_type"] in {"result_claim", "robustness_claim", "data_claim"}:
            claim["evidence_artifacts"] = []
            claim["status"] = "needs_evidence"
        else:
            claim["evidence_artifacts"] = []
            claim["status"] = "context"

    return {
        "status": "fail" if blocking_issues else "pass",
        "strict": bool(strict),
        "summary": {
            "claim_count": len(claims),
            "evidence_artifact_count": len(evidence_ids),
            "blocking_issue_count": len(blocking_issues),
        },
        "claims": claims,
        "artifact_evidence_ids": evidence_ids,
        "blocking_issues": blocking_issues,
        "warnings": warnings,
    }


def _build_reviewer_attack_pack(
    *,
    metadata,
    claim_gate_report: dict[str, Any],
    artifact_usage_report: dict[str, Any],
) -> dict[str, Any]:
    questions: list[str] = []
    for claim in claim_gate_report.get("claims", []):
        text = str(claim.get("text") or "")
        short = re.sub(r"\s+", " ", text).strip()
        if len(short) > 180:
            short = short[:177] + "..."
        if claim.get("status") == "supported":
            evidence = ", ".join(claim.get("evidence_artifacts") or [])
            questions.append(f"Can the reported evidence artifact(s) {evidence} substantiate: {short}")
        elif claim.get("status") == "needs_evidence":
            questions.append(f"What artifact or table directly substantiates: {short}")

    for artifact in artifact_usage_report.get("artifacts", []):
        artifact_id = artifact.get("id")
        questions.append(
            "Can the data_hash/code_hash provenance reproduce "
            f"{artifact_id} and match the paper caption?"
        )
        if not artifact.get("used_in_main_tex"):
            questions.append(f"Why is manifest artifact {artifact_id} not used in main.tex?")

    return {
        "title": getattr(metadata, "title", ""),
        "status": "fail"
        if claim_gate_report.get("status") == "fail" or artifact_usage_report.get("status") == "fail"
        else "pass",
        "claim_gate_status": claim_gate_report.get("status"),
        "artifact_usage_status": artifact_usage_report.get("status"),
        "blocking_issues": list(claim_gate_report.get("blocking_issues", []))
        + list(artifact_usage_report.get("blocking_issues", [])),
        "reviewer_questions": questions,
        "artifacts": artifact_usage_report.get("artifacts", []),
    }


def _attack_pack_markdown(pack: dict[str, Any]) -> str:
    lines = [
        f"# Reviewer Attack Pack: {pack.get('title') or 'Untitled Paper'}",
        "",
        f"- Claim gate: {pack.get('claim_gate_status')}",
        f"- Artifact usage: {pack.get('artifact_usage_status')}",
        "",
        "## Blocking Issues",
    ]
    blocking = list(pack.get("blocking_issues") or [])
    if blocking:
        lines.extend(f"- {issue}" for issue in blocking)
    else:
        lines.append("- None")
    lines.extend(["", "## Reviewer Questions"])
    questions = list(pack.get("reviewer_questions") or [])
    if questions:
        lines.extend(f"- {question}" for question in questions)
    else:
        lines.append("- No artifact-backed claims were detected.")
    lines.append("")
    return "\n".join(lines)


def _write_output_reports(
    *,
    output_dir: Path,
    metadata,
    manifest: NormalizedArtifactManifest | None,
    main_tex_path: Path,
    strict_artifacts: bool,
    claim_gate_strict: bool,
    skill4econ_run_dir: str | None,
) -> dict[str, str]:
    main_tex = _read_text_if_exists(main_tex_path)
    paths = _report_path_map(output_dir)
    claim_gate_report = _build_claim_gate_report(
        metadata=metadata,
        manifest=manifest,
        main_tex=main_tex,
        strict=claim_gate_strict,
    )
    artifact_usage_report = _build_artifact_usage_report(
        manifest=manifest,
        main_tex=main_tex,
        strict=strict_artifacts,
        skill4econ_run_dir=skill4econ_run_dir,
    )
    attack_pack = _build_reviewer_attack_pack(
        metadata=metadata,
        claim_gate_report=claim_gate_report,
        artifact_usage_report=artifact_usage_report,
    )
    _write_json(paths["claim_gate_report"], claim_gate_report)
    _write_json(paths["artifact_usage_report"], artifact_usage_report)
    _write_json(paths["reviewer_attack_pack_json"], attack_pack)
    _write_text(paths["reviewer_attack_pack_markdown"], _attack_pack_markdown(attack_pack))
    return {key: str(path) for key, path in paths.items()}


def _raise_for_report_failures(output_dir: Path) -> None:
    paths = _report_path_map(output_dir)
    claim_gate = json.loads(paths["claim_gate_report"].read_text(encoding="utf-8"))
    artifact_usage = json.loads(paths["artifact_usage_report"].read_text(encoding="utf-8"))
    failures = []
    if claim_gate.get("status") == "fail":
        failures.extend(claim_gate.get("blocking_issues") or [])
    if artifact_usage.get("status") == "fail":
        failures.extend(artifact_usage.get("blocking_issues") or [])
    if failures:
        raise ValueError("strict output report checks failed: " + ", ".join(dict.fromkeys(failures)))


def _main_tex_path(result: PaperGenerationResult, output_dir: Path) -> Path:
    if result.output_path:
        return Path(result.output_path) / "main.tex"
    return output_dir / "main.tex"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a standalone EasyPaper economics/finance generation job.",
    )
    parser.add_argument("request", help="Path to econ/finance request YAML.")
    parser.add_argument("--out", required=True, help="Output directory.")
    parser.add_argument("--model", help="OpenAI-compatible model name.")
    parser.add_argument("--base-url", help="OpenAI-compatible base URL.")
    parser.add_argument("--api-key", help="OpenAI-compatible API key. Prefer env vars for shell safety.")
    parser.add_argument("--venue", help="Override request venue.")
    parser.add_argument("--mock-llm", action="store_true", help="Validate inputs and write mock outputs without LLM calls.")
    parser.add_argument("--enable-vlm", action="store_true", help="Enable OpenAI-compatible VLM review service.")
    parser.add_argument("--enable-review", dest="enable_review", action="store_true", default=None)
    parser.add_argument("--disable-review", dest="enable_review", action="store_false")
    parser.add_argument("--max-review-iterations", type=int, default=3)
    parser.add_argument(
        "--strict-artifacts",
        action="store_true",
        help="Fail when declared empirical artifacts are missing, unused, or lack provenance.",
    )
    parser.add_argument(
        "--claim-gate-strict",
        action="store_true",
        help="Fail when output claim-gate checks have blocking issues.",
    )
    parser.add_argument(
        "--skill4econ-run-dir",
        help="Optional EvoScientist/skill4econ run directory to record in output reports.",
    )
    pdf_group = parser.add_mutually_exclusive_group()
    pdf_group.add_argument("--no-pdf", dest="compile_pdf", action="store_false", default=None)
    pdf_group.add_argument("--compile-pdf", dest="compile_pdf", action="store_true")
    return parser.parse_args(argv)


async def run_econ_paper(
    args: argparse.Namespace,
    *,
    client_factory: Callable[[Any], Any] | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    request_path = Path(args.request).expanduser().resolve()
    output_dir = Path(args.out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    events_path = output_dir / "events.jsonl"
    if events_path.exists():
        events_path.unlink()

    request_payload = _resolve_request_payload(
        request_path,
        repo_root=repo_root,
        output_dir=output_dir,
        venue=args.venue,
        compile_pdf=args.compile_pdf,
    )
    skill4econ_export = _maybe_export_skill4econ_bundle(
        request_payload,
        output_dir=output_dir,
        skill4econ_run_dir=args.skill4econ_run_dir,
        strict=bool(args.claim_gate_strict),
    )
    manifest = _resolve_manifest(request_payload, repo_root=repo_root)
    request = PaperGenerationRequest(**request_payload)
    metadata = request.to_metadata()

    compile_pdf = request.compile_pdf if args.compile_pdf is None else bool(args.compile_pdf)
    enable_review = request.enable_review if args.enable_review is None else bool(args.enable_review)
    model = _resolve_runtime_value(args.model, MODEL_ENV_NAMES, name="model", allow_dummy=args.mock_llm)
    base_url = _resolve_runtime_value(args.base_url, BASE_URL_ENV_NAMES, name="base_url", allow_dummy=args.mock_llm)
    api_key = _resolve_runtime_value(args.api_key, API_KEY_ENV_NAMES, name="api_key", allow_dummy=args.mock_llm)
    venue = args.venue or getattr(metadata, "venue", None) or request_payload.get("venue")
    venue_config = _load_venue_config(venue, repo_root=repo_root)

    config = build_app_config(
        model=model,
        base_url=base_url,
        api_key=api_key,
        venue=venue,
        enable_vlm=bool(args.enable_vlm),
    )
    write_redacted_app_config(config, output_dir / "config.redacted.yaml")
    _write_json(output_dir / "request.normalized.json", metadata.model_dump(mode="json"))
    _write_json(output_dir / "manifest.normalized.json", _manifest_to_json(manifest))
    _write_json(output_dir / "venue.normalized.json", venue_config)
    _write_event(
        events_path,
        {
            "type": "runner_started",
            "request": str(request_path),
            "output_dir": str(output_dir),
            "mock_llm": bool(args.mock_llm),
            "strict_artifacts": bool(args.strict_artifacts),
            "claim_gate_strict": bool(args.claim_gate_strict),
            "skill4econ_run_dir": str(Path(args.skill4econ_run_dir).expanduser().resolve())
            if args.skill4econ_run_dir
            else None,
            "skill4econ_export": skill4econ_export,
        },
    )

    async def progress_callback(event: dict[str, Any]) -> None:
        _write_event(events_path, event)

    if args.mock_llm:
        result = _mock_result(metadata, output_dir, venue_config=venue_config)
        _write_event(events_path, {"type": "mock_completed", "status": result.status})
    else:
        client = client_factory(config) if client_factory is not None else EasyPaper(config=config)
        result = await client.generate(
            metadata,
            output_dir=str(output_dir),
            save_output=True,
            compile_pdf=compile_pdf,
            template_path=metadata.template_path,
            target_pages=metadata.target_pages,
            enable_review=enable_review,
            max_review_iterations=args.max_review_iterations,
            enable_planning=True,
            enable_exemplar=False,
            enable_vlm_review=bool(args.enable_vlm),
            progress_callback=progress_callback,
        )
        _write_event(events_path, {"type": "runner_completed", "status": result.status})

    main_tex = _main_tex_path(result, output_dir)
    report_paths = _write_output_reports(
        output_dir=output_dir,
        metadata=metadata,
        manifest=manifest,
        main_tex_path=main_tex,
        strict_artifacts=bool(args.strict_artifacts),
        claim_gate_strict=bool(args.claim_gate_strict),
        skill4econ_run_dir=args.skill4econ_run_dir,
    )
    summary = {
        "status": result.status,
        "main_tex": str(main_tex),
        "events": str(events_path),
        "request_normalized": str(output_dir / "request.normalized.json"),
        "manifest_normalized": str(output_dir / "manifest.normalized.json"),
        "venue_normalized": str(output_dir / "venue.normalized.json"),
        "config_redacted": str(output_dir / "config.redacted.yaml"),
        "skill4econ_export": skill4econ_export,
        **report_paths,
    }
    _write_json(output_dir / "runner.summary.json", summary)
    _raise_for_report_failures(output_dir)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = asyncio.run(run_econ_paper(args))
    except Exception as exc:
        print(f"run_econ_paper failed: {exc}", file=sys.stderr)
        return 2
    print(summary["main_tex"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
