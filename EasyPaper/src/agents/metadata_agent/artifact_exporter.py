"""
Artifact export helpers for MetaDataAgent.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class ArtifactExporter:
    """
    File export and manifest helpers for metadata-agent runs.
    """

    _COMPILE_EXTS = {
        ".tex", ".bib", ".bst", ".cls", ".sty", ".bbl",
        ".png", ".jpg", ".jpeg", ".pdf", ".eps", ".svg", ".gif",
    }
    _ANALYSIS_SUBDIRS = (
        "analysis/planning",
        "analysis/research_context",
        "analysis/citations",
        "analysis/structure",
        "analysis/review",
        "analysis/references",
        "analysis/code_context",
        "analysis/tables",
        "analysis/tables/section_preview",
        "logs/traces",
    )
    _MANIFEST_MAX_HASH_BYTES = 2 * 1024 * 1024

    @staticmethod
    async def save_artifact(
        paper_dir: Path,
        relative_path: str,
        content: Any,
        emitter: "ProgressEmitter",
        category: str,
        label: str = "",
        artifacts_prefix: str = "",
    ) -> Path:
        target = paper_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(content, bytes):
            target.write_bytes(content)
        elif isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_text(
                json.dumps(content, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        mime, _ = mimetypes.guess_type(str(target))
        if mime is None:
            ext = target.suffix.lower()
            mime = {
                ".json": "application/json",
                ".tex": "text/x-latex",
                ".bib": "text/x-bibtex",
                ".md": "text/markdown",
                ".bst": "text/plain",
                ".cls": "text/plain",
            }.get(ext, "application/octet-stream")

        size = target.stat().st_size

        storage_key = ""
        if artifacts_prefix:
            candidate_key = f"{artifacts_prefix}/{relative_path}"
            from ...utils.storage_client import storage_client
            if await storage_client.upload(candidate_key, target.read_bytes()):
                storage_key = candidate_key

        await emitter.artifact_saved(
            relative_path=relative_path,
            absolute_path=str(target),
            category=category,
            size=size,
            mime_type=mime,
            label=label or target.name,
            storage_key=storage_key,
        )
        return target

    @classmethod
    def ensure_export_directories(cls, paper_dir: Path) -> None:
        for d_name in cls._ANALYSIS_SUBDIRS:
            (paper_dir / d_name).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def write_json_file(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def export_plan_artifacts(
        cls,
        paper_dir: Path,
        paper_plan: Optional["PaperPlan"] = None,
        plan_review_summary: Optional[Dict[str, Any]] = None,
        plan_evolution: Optional[Dict[str, Any]] = None,
        evidence_dag: Optional["EvidenceDAG"] = None,
        figure_supplementation_trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        planning_dir = paper_dir / "analysis" / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        if paper_plan is not None:
            (planning_dir / "paper_plan.json").write_text(
                paper_plan.model_dump_json(indent=2),
                encoding="utf-8",
            )
        if plan_review_summary is not None:
            cls.write_json_file(planning_dir / "plan_review.json", plan_review_summary)
        if plan_evolution and plan_evolution.get("enabled"):
            cls._export_plan_evolution(planning_dir, plan_evolution)
        if evidence_dag is not None:
            cls.write_json_file(
                planning_dir / "evidence_dag.json",
                evidence_dag.to_serializable(),
            )
        if figure_supplementation_trace is not None:
            cls.write_json_file(
                planning_dir / "figure_supplementation.json",
                figure_supplementation_trace,
            )

    @classmethod
    def _export_plan_evolution(
        cls,
        planning_dir: Path,
        plan_evolution: Dict[str, Any],
    ) -> None:
        """Export detailed planner review snapshots plus a compact index."""
        if "initial" in plan_evolution:
            cls.write_json_file(planning_dir / "paper_plan.initial.json", plan_evolution["initial"])

        compact_iterations: List[Dict[str, Any]] = []
        for raw_iter in plan_evolution.get("iterations", []) or []:
            if not isinstance(raw_iter, dict):
                continue
            iteration = int(raw_iter.get("iteration", len(compact_iterations) + 1) or 1)
            prefix = planning_dir / f"paper_plan.review_{iteration:02d}"
            if "before" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.before.json"), raw_iter["before"])
            if "issues" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.issues.json"), raw_iter["issues"])
            if "after" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.after.json"), raw_iter["after"])
            issues = raw_iter.get("issues", []) or []
            compact_iterations.append(
                {
                    "iteration": iteration,
                    "status": raw_iter.get("status", ""),
                    "changed": bool(raw_iter.get("changed", False)),
                    "has_after": "after" in raw_iter,
                    "issue_count": len(issues) if isinstance(issues, list) else 0,
                    "blocking_issue_count": sum(
                        1
                        for issue in issues
                        if isinstance(issue, dict)
                        and issue.get("severity") in {"blocker", "major"}
                    ) if isinstance(issues, list) else 0,
                    "issues": [
                        {
                            "issue_id": issue.get("issue_id", ""),
                            "severity": issue.get("severity", ""),
                            "category": issue.get("category", ""),
                            "section_type": issue.get("section_type", ""),
                        }
                        for issue in issues
                        if isinstance(issue, dict)
                    ],
                }
            )

        compact = {
            "enabled": True,
            "max_iterations": plan_evolution.get("max_iterations", 0),
            "final_status": plan_evolution.get("final_status", "not_run"),
            "iterations": compact_iterations,
        }
        cls.write_json_file(planning_dir / "paper_plan_evolution.json", compact)

    @classmethod
    def export_table_artifacts(
        cls,
        paper_dir: Path,
        *,
        table_review: Optional[Dict[str, Any]] = None,
        table_review_evolution: Optional[Dict[str, Any]] = None,
        restructure_iterations: Optional[List[Dict[str, Any]]] = None,
        section_preview_artifacts: Optional[Dict[str, Dict[str, Any]]] = None,
        final_pdf_table_review: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Persist durable table-analysis artifacts under ``analysis/tables``.

        Generation helpers may create raw records or temporary preview files, but
        this exporter owns final naming and registration of the durable artifact
        tree.
        """
        tables_dir = paper_dir / "analysis" / "tables"
        preview_dir = tables_dir / "section_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)

        if table_review is not None:
            cls.write_json_file(tables_dir / "table_review.json", table_review)
        if table_review_evolution is not None:
            cls.write_json_file(
                tables_dir / "table_review_evolution.json",
                table_review_evolution,
            )
        if final_pdf_table_review is not None:
            cls.write_json_file(
                tables_dir / "final_pdf_table_review.json",
                final_pdf_table_review,
            )

        for raw_iter in restructure_iterations or []:
            if not isinstance(raw_iter, dict):
                continue
            iteration = int(raw_iter.get("iteration", 1) or 1)
            prefix = tables_dir / f"table_restructure.review_{iteration:02d}"
            if "before" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.before.json"), raw_iter["before"])
            if "issues" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.issues.json"), raw_iter["issues"])
            if "after" in raw_iter:
                cls.write_json_file(Path(f"{prefix}.after.json"), raw_iter["after"])

        for section, artifacts in (section_preview_artifacts or {}).items():
            if not isinstance(artifacts, dict):
                continue
            safe_section = "".join(
                ch if ch.isalnum() or ch in {"_", "-"} else "_"
                for ch in str(section or "section")
            ) or "section"
            for key, suffix in (("tex_path", ".tex"), ("pdf_path", ".pdf")):
                src = artifacts.get(key)
                if not src:
                    continue
                src_path = Path(src)
                if not src_path.exists():
                    continue
                dest = preview_dir / f"{safe_section}{suffix}"
                dest.parent.mkdir(parents=True, exist_ok=True)
                if src_path.resolve() != dest.resolve():
                    shutil.copyfile(src_path, dest)
            if artifacts.get("tex") is not None:
                cls.write_text_file(
                    preview_dir / f"{safe_section}.tex",
                    str(artifacts.get("tex") or ""),
                )

    @classmethod
    def export_generation_core_artifacts(
        cls,
        paper_dir: Path,
        latex_content: str,
        references_bibtex: str,
        metadata: Dict[str, Any],
    ) -> None:
        cls.ensure_export_directories(paper_dir)
        (paper_dir / "main.tex").write_text(latex_content, encoding="utf-8")
        (paper_dir / "references.bib").write_text(references_bibtex, encoding="utf-8")
        cls.write_json_file(paper_dir / "metadata.json", metadata)

    @staticmethod
    def write_text_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def build_structure_summary(
        paper_plan: Optional["PaperPlan"],
        generated_sections: Dict[str, str],
    ) -> Dict[str, Any]:
        planned_sections: List[Dict[str, Any]] = []
        if paper_plan is not None:
            for section in paper_plan.sections:
                planned_sections.append(
                    {
                        "section_type": section.section_type,
                        "section_title": section.section_title,
                        "paragraph_count": len(section.paragraphs or []),
                        "figure_count": len(section.figures or []),
                        "table_count": len(section.tables or []),
                    },
                )
        generated_order = list(generated_sections.keys())
        return {
            "planned_sections": planned_sections,
            "generated_section_order": generated_order,
            "generated_section_count": len(generated_order),
            "missing_from_generation": [
                item["section_type"]
                for item in planned_sections
                if item["section_type"] not in generated_sections
            ],
        }

    @classmethod
    def export_analysis_artifacts(
        cls,
        paper_dir: Path,
        research_context: Optional[Dict[str, Any]],
        code_context: Optional[Dict[str, Any]],
        code_summary_markdown: Optional[str],
        ref_pool_snapshot: Dict[str, Any],
        citation_budget_usage: List[Dict[str, Any]],
        paper_plan: Optional["PaperPlan"],
        generated_sections: Dict[str, str],
        citation_audit: Optional[Dict[str, Any]] = None,
        citation_audit_markdown: Optional[str] = None,
    ) -> None:
        cls.ensure_export_directories(paper_dir)

        research_payload = dict(research_context or {})
        if "summary" not in research_payload:
            research_payload["summary"] = ""
        if not research_context:
            research_payload.setdefault("status", "unavailable")
            research_payload.setdefault("reason", "research_context_missing")
        cls.write_json_file(
            paper_dir / "analysis" / "research_context" / "research_context.json",
            research_payload,
        )

        citations_payload = {
            "status": "ok" if citation_budget_usage else "empty",
            "citation_budget_usage": citation_budget_usage or [],
        }
        cls.write_json_file(
            paper_dir / "analysis" / "citations" / "citation_budget_usage.json",
            citations_payload,
        )
        audit_payload = dict(citation_audit or {})
        if not audit_payload:
            audit_payload = {"status": "not_run", "records": [], "unresolved_findings": []}
        cls.write_json_file(
            paper_dir / "analysis" / "citations" / "citation_grounding_audit.json",
            audit_payload,
        )
        cls.write_text_file(
            paper_dir / "analysis" / "citations" / "citation_grounding_audit.md",
            citation_audit_markdown or "# Citation Grounding Audit\n\nStatus: not_run\n",
        )
        repair_attempts = audit_payload.get("repair_attempts", [])
        cls.write_json_file(
            paper_dir / "analysis" / "citations" / "citation_repair_attempts.json",
            {
                "status": "ok" if repair_attempts else "empty",
                "repair_attempts": repair_attempts,
            },
        )

        structure_payload = cls.build_structure_summary(
            paper_plan=paper_plan,
            generated_sections=generated_sections,
        )
        cls.write_json_file(
            paper_dir / "analysis" / "structure" / "structure_summary.json",
            structure_payload,
        )

        ref_payload = dict(ref_pool_snapshot or {})
        ref_payload.setdefault("core_refs", [])
        ref_payload.setdefault("discovered_refs", [])
        cls.write_json_file(
            paper_dir / "analysis" / "references" / "ref_pool_snapshot.json",
            ref_payload,
        )

        code_payload = dict(code_context or {})
        if not code_context:
            code_payload["status"] = "unavailable"
            code_payload["reason"] = "code_context_missing"
        cls.write_json_file(
            paper_dir / "analysis" / "code_context" / "code_context.json",
            code_payload,
        )
        cls.write_text_file(
            paper_dir / "analysis" / "code_context" / "code_summary.md",
            code_summary_markdown or "# Code Summary\n\nNo code summary available.\n",
        )

    @classmethod
    def export_trace_artifacts(
        cls,
        paper_dir: Path,
        prompt_traces: List[Dict[str, Any]],
        usage_report: Dict[str, Any],
        export_prompt_traces: bool,
    ) -> None:
        cls.ensure_export_directories(paper_dir)
        trace_items = prompt_traces if export_prompt_traces else []
        cls.write_json_file(
            paper_dir / "logs" / "traces" / "prompt_traces.json",
            {
                "status": "enabled" if export_prompt_traces else "disabled",
                "count": len(trace_items),
                "items": trace_items,
            },
        )
        usage_payload = dict(usage_report or {})
        usage_payload.setdefault("summary", {})
        cls.write_json_file(
            paper_dir / "logs" / "traces" / "usage_report.json",
            usage_payload,
        )

    @classmethod
    def export_artifacts_manifest(
        cls,
        paper_dir: Path,
        *,
        paper_title: str,
        errors: List[str],
        warnings: Optional[List[str]] = None,
        review_iterations: int,
        pdf_path: Optional[str],
        total_words: int,
    ) -> None:
        paper_dir = Path(paper_dir)
        manifest_path = paper_dir / "artifacts_manifest.json"
        file_entries: List[Dict[str, Any]] = []
        for fpath in sorted(paper_dir.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(paper_dir).as_posix()
            if rel == "artifacts_manifest.json":
                continue
            try:
                size_b = fpath.stat().st_size
            except OSError:
                size_b = -1
            entry: Dict[str, Any] = {
                "path": rel,
                "size_bytes": size_b,
            }
            if 0 <= size_b <= cls._MANIFEST_MAX_HASH_BYTES:
                digest = hashlib.sha256()
                with open(fpath, "rb") as f:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        digest.update(chunk)
                entry["sha256"] = digest.hexdigest()
            else:
                entry["sha256"] = None
                if size_b > cls._MANIFEST_MAX_HASH_BYTES:
                    entry["sha256_skipped_reason"] = "file_too_large_for_manifest_hash"
                elif size_b < 0:
                    entry["sha256_skipped_reason"] = "stat_failed"
            file_entries.append(entry)

        payload = {
            "manifest_version": "1",
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "paper_title": paper_title,
            "warnings": list(warnings or []),
            "run": {
                "error_count": len(errors),
                "errors_preview": list(errors[:10]),
                "warning_count": len(warnings or []),
                "warnings_preview": list((warnings or [])[:10]),
                "review_iterations": review_iterations,
                "pdf_path": pdf_path,
                "total_words": total_words,
            },
            "file_count": len(file_entries),
            "files": file_entries,
        }
        cls.write_json_file(manifest_path, payload)

    @classmethod
    async def save_compilation_output(
        cls,
        compile_dir: Path,
        paper_dir: Path,
        emitter: "ProgressEmitter",
        artifacts_prefix: str = "",
    ) -> None:
        if not compile_dir or not compile_dir.is_dir():
            return

        for path in sorted(compile_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in cls._COMPILE_EXTS:
                continue
            rel = path.relative_to(compile_dir).as_posix()
            await cls.save_artifact(
                paper_dir=paper_dir,
                relative_path=rel,
                content=path.read_bytes(),
                emitter=emitter,
                category="compilation",
                label=path.name,
                artifacts_prefix=artifacts_prefix,
            )
