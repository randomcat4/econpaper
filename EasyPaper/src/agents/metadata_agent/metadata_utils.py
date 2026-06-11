"""
General metadata-agent utility helpers.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List

from ..shared.asset_paths import format_resolution_error, resolve_asset_path

_EMPIRICAL_RESULT_ROLES = {
    "result",
    "results",
    "result_figure",
    "result_plot",
    "result_table",
    "empirical_result",
    "empirical_results",
    "data_result",
}


def _norm_role(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def is_empirical_result_figure(fig: Any) -> bool:
    """
    Return True for figures that must be backed by a real empirical artifact.
    """
    target_type = _norm_role(getattr(fig, "target_type", None))
    semantic_role = _norm_role(getattr(fig, "semantic_role", ""))
    section_type = _norm_role(
        getattr(fig, "section_type", None) or getattr(fig, "section", "")
    )
    return (
        target_type == "data_visualization"
        or semantic_role in _EMPIRICAL_RESULT_ROLES
        or (
            section_type in {"result", "results", "robustness"}
            and semantic_role in {"", "result_figure", "result_plot"}
        )
    )


def merge_usage_reports(plan_report: dict, gen_report: dict) -> dict:
    """
    Merge usage reports from prepare_plan and execute_generation phases.
    """
    plan_calls = plan_report.get("calls", [])
    gen_calls = gen_report.get("calls", [])
    all_calls = plan_calls + gen_calls

    from ..shared.usage_tracker import LLMCallRecord, UsageTracker

    merged = UsageTracker()
    for call in all_calls:
        merged.record(LLMCallRecord(**call))
    return merged.to_dict()


def parse_references(bibtex_list: List[str]) -> List[Dict[str, Any]]:
    """
    Parse BibTeX entries into a lightweight structured format.
    """
    parsed = []
    for bibtex in bibtex_list:
        try:
            ref_id_match = re.search(r'@\w+{([^,]+),', bibtex)
            title_match = re.search(r'title\s*=\s*[{"]([^}"]+)[}"]', bibtex, re.IGNORECASE)
            author_match = re.search(r'author\s*=\s*[{"]([^}"]+)[}"]', bibtex, re.IGNORECASE)
            year_match = re.search(r'year\s*=\s*[{"]?(\d{4})[}"]?', bibtex, re.IGNORECASE)
            ref = {
                "ref_id": ref_id_match.group(1) if ref_id_match else f"ref_{len(parsed)+1}",
                "title": title_match.group(1) if title_match else "",
                "authors": author_match.group(1) if author_match else "",
                "year": int(year_match.group(1)) if year_match else None,
                "bibtex": bibtex,
            }
            parsed.append(ref)
        except Exception:
            parsed.append(
                {
                    "ref_id": f"ref_{len(parsed)+1}",
                    "bibtex": bibtex,
                }
            )
    return parsed


def validate_ref_usage(
    generated_sections: Dict[str, str],
    ref_pool: "ReferencePool",
) -> Dict[str, Any]:
    """
    Check that every reference in the pool is cited at least once.
    """
    from ..shared.reference_pool import ReferencePool

    all_content = "\n".join(generated_sections.values())
    cited_keys = ReferencePool.extract_cite_keys(all_content)
    pool_keys = ref_pool.valid_citation_keys
    uncited = pool_keys - cited_keys
    if uncited:
        print(
            f"[MetaDataAgent] WARNING: {len(uncited)} uncited reference(s): "
            + ", ".join(sorted(uncited)[:10])
            + ("..." if len(uncited) > 10 else "")
        )
    else:
        print(f"[MetaDataAgent] All {len(pool_keys)} pooled references are cited.")
    return {
        "cited_keys": sorted(cited_keys),
        "pool_keys": sorted(pool_keys),
        "uncited_keys": sorted(uncited),
        "coverage": (len(cited_keys & pool_keys) / len(pool_keys)) if pool_keys else 1.0,
    }


def validate_file_paths(metadata: "PaperMetaData") -> List[str]:
    """
    Validate that provided figure/table file paths exist before generation.
    """
    errors = []
    materials_root = getattr(metadata, "materials_root", None)
    base_path = materials_root or os.getcwd()

    for fig in metadata.figures:
        if is_empirical_result_figure(fig) and fig.auto_generate and not fig.file_path:
            errors.append(
                f"Empirical result figure {fig.id} must be file-backed; "
                "autonomous data visualization is forbidden"
            )
            continue
        if is_empirical_result_figure(fig) and not fig.file_path:
            errors.append(f"Empirical result figure {fig.id} requires file_path")
            continue
        if fig.auto_generate:
            continue
        if fig.file_path:
            resolved = resolve_asset_path(
                fig.file_path,
                materials_root=base_path,
                require_within_root=bool(materials_root),
            )
            if not resolved.exists:
                errors.append(format_resolution_error("Figure", fig.file_path, resolved))

    for tbl in metadata.tables:
        if tbl.auto_generate:
            continue
        if tbl.file_path:
            resolved = resolve_asset_path(
                tbl.file_path,
                materials_root=base_path,
                require_within_root=bool(materials_root),
            )
            if not resolved.exists:
                errors.append(format_resolution_error("Table", tbl.file_path, resolved))
        elif not tbl.content and not tbl.auto_generate:
            errors.append(f"Table {tbl.id} has no file_path or content")

    return errors


def resolve_direct_metadata_paths(raw: Dict[str, Any], base: Path, repo: Path) -> Dict[str, Any]:
    """
    Resolve direct metadata-file asset paths before request validation.

    Figure/table paths prefer ``materials_root`` when provided, then the
    metadata file directory. Template paths keep metadata-directory precedence
    with repository-root fallback for shared templates.
    """
    materials_root = raw.get("materials_root")
    for fig in raw.get("figures") or []:
        fp = fig.get("file_path")
        if fp and not Path(fp).is_absolute():
            resolved = resolve_asset_path(
                fp,
                materials_root=materials_root,
                fallback_base=str(base),
            )
            fig["file_path"] = str(Path(resolved.resolved_path or fp).resolve())
        elif fp and materials_root:
            resolved = resolve_asset_path(
                fp,
                materials_root=materials_root,
                require_within_root=True,
            )
            if resolved.error:
                raise ValueError(format_resolution_error("Figure", fp, resolved))

    for tab in raw.get("tables") or []:
        fp = tab.get("file_path")
        if fp and not Path(fp).is_absolute():
            resolved = resolve_asset_path(
                fp,
                materials_root=materials_root,
                fallback_base=str(base),
            )
            tab["file_path"] = str(Path(resolved.resolved_path or fp).resolve())
        elif fp and materials_root:
            resolved = resolve_asset_path(
                fp,
                materials_root=materials_root,
                require_within_root=True,
            )
            if resolved.error:
                raise ValueError(format_resolution_error("Table", fp, resolved))

    tpl = raw.get("template_path")
    if tpl and not Path(tpl).is_absolute():
        base_tpl = (base / tpl).resolve()
        repo_tpl = (repo / tpl).resolve()
        raw["template_path"] = str(base_tpl if base_tpl.is_file() else repo_tpl)

    for manifest_key in ("figures_manifest", "artifact_manifest_path"):
        manifest = raw.get(manifest_key)
        if manifest and not Path(manifest).is_absolute():
            base_manifest = (base / manifest).resolve()
            repo_manifest = (repo / manifest).resolve()
            raw[manifest_key] = str(base_manifest if base_manifest.is_file() else repo_manifest)

    out_dir = raw.get("output_dir")
    if out_dir and not Path(out_dir).is_absolute():
        raw["output_dir"] = str((base / out_dir).resolve())

    return raw


def convert_figures_for_latex(metadata: "PaperMetaData") -> int:
    """
    Convert figure files to staged LaTeX-compatible formats (PDF preferred, then PNG).

    The source ``file_path`` remains the figure identity. Converted artifacts are
    written under a designated EasyPaper staging directory and tracked separately.
    """
    from PIL import Image as PILImage

    latex_ok = {".pdf", ".png", ".jpg", ".jpeg", ".eps"}
    converted = 0
    materials_root = getattr(metadata, "materials_root", None)
    base_path = materials_root or os.getcwd()
    derived_dir = os.path.join(base_path, ".easypaper", "derived_figures")

    for fig in metadata.figures:
        if fig.auto_generate or not fig.file_path:
            continue
        asset = resolve_asset_path(
            fig.file_path,
            materials_root=base_path,
            require_within_root=bool(materials_root),
        )
        if not asset.exists:
            continue
        resolved = os.path.normpath(asset.resolved_path or fig.file_path)
        ext = os.path.splitext(resolved)[1].lower()
        if ext in latex_ok:
            continue

        os.makedirs(derived_dir, exist_ok=True)
        safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(getattr(fig, "id", "") or os.path.basename(resolved)))
        pdf_path = os.path.join(derived_dir, f"{safe_stem}.pdf")
        try:
            img = PILImage.open(resolved)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(pdf_path, "PDF")
            fig.derived_file_path = pdf_path if os.path.isabs(fig.file_path) else os.path.relpath(pdf_path, base_path)
            converted += 1
            print(f"[MetaDataAgent] Converted figure {fig.id}: {ext} -> .pdf")
        except Exception as exc:
            png_path = os.path.join(derived_dir, f"{safe_stem}.png")
            try:
                img = PILImage.open(resolved)
                img.save(png_path, "PNG")
                fig.derived_file_path = png_path if os.path.isabs(fig.file_path) else os.path.relpath(png_path, base_path)
                converted += 1
                print(f"[MetaDataAgent] Converted figure {fig.id}: {ext} -> .png")
            except Exception as png_exc:
                print(f"[MetaDataAgent] WARNING: Cannot convert {fig.id} ({ext}): pdf={exc}, png={png_exc}")

    return converted
