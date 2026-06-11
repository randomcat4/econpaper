"""File-backed artifact manifest support for empirical papers."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..shared.asset_paths import resolve_asset_path
from .models import FigureSpec, PaperMetaData, TableSpec

MANIFEST_VERSION = "econ-finance-artifact-manifest/v1"
MANIFEST_V2_VERSION = "econ-finance-artifact-manifest/v2"
BUNDLE_V2_VERSION = "skill4econ-easypaper-bundle/v2"
FIGURE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".svg"}
TABLE_EXTENSIONS = {".tex", ".csv", ".md"}
CAPTION_MODES = {"locked", "polish"}
RESULT_SECTIONS = {"result", "results", "robustness"}


class ArtifactManifestError(ValueError):
    """Raised when an empirical artifact manifest is invalid."""


@dataclass(frozen=True)
class NormalizedArtifact:
    """A manifest artifact with a validated file path under materials_root."""

    id: str
    path: str
    resolved_path: Path
    latex_path: str
    section: str
    caption: str
    kind: str
    semantic_role: str = ""
    target_type: str = ""
    caption_mode: str = "locked"
    data_hash: str = ""
    code_hash: str = ""
    title: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedArtifactManifest:
    """Validated artifact manifest ready to map into EasyPaper metadata."""

    version: str
    materials_root: Path
    source_agent: str = ""
    run_status: str = ""
    claim_level: str = ""
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    allowed_paper_uses: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    figures: list[NormalizedArtifact] = field(default_factory=list)
    tables: list[NormalizedArtifact] = field(default_factory=list)


def _as_mapping(payload: Mapping[str, Any] | str | Path) -> tuple[Mapping[str, Any], Path | None]:
    if isinstance(payload, (str, Path)):
        path = Path(payload).expanduser().resolve()
        return json.loads(path.read_text(encoding="utf-8")), path
    if not isinstance(payload, Mapping):
        raise ArtifactManifestError("Artifact manifest must be a mapping or JSON file path.")
    return payload, None


def _path_segments(path_text: str) -> list[str]:
    return [part for part in path_text.replace("\\", "/").split("/") if part]


def _posix(path: Path) -> str:
    return str(path).replace("\\", "/")


def _candidate_roots(
    raw_root: str,
    *,
    manifest_path: Path | None,
    repo_root: Path | None,
) -> list[Path]:
    root = Path(raw_root).expanduser()
    if root.is_absolute():
        return [root.resolve()]

    bases: list[Path] = []
    if manifest_path is not None:
        bases.append(manifest_path.parent)
    if repo_root is not None:
        bases.append(repo_root)
    bases.append(Path.cwd())

    candidates: list[Path] = []
    seen: set[str] = set()
    for base in bases:
        candidate = (base / root).resolve()
        key = str(candidate).casefold()
        if key not in seen:
            candidates.append(candidate)
            seen.add(key)
    return candidates


def _resolve_materials_root(
    raw_root: Any,
    *,
    manifest_path: Path | None,
    repo_root: str | Path | None,
) -> Path:
    if not raw_root or not str(raw_root).strip():
        raise ArtifactManifestError("Artifact manifest requires materials_root.")
    repo_path = Path(repo_root).expanduser().resolve() if repo_root else None
    candidates = _candidate_roots(
        str(raw_root).strip(),
        manifest_path=manifest_path,
        repo_root=repo_path,
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise ArtifactManifestError(
        "Artifact materials_root does not exist: "
        + "; ".join(_posix(candidate) for candidate in candidates)
    )


def _require_text(item: Mapping[str, Any], key: str, *, kind: str) -> str:
    value = str(item.get(key) or "").strip()
    if not value:
        raise ArtifactManifestError(f"{kind} artifact requires {key}.")
    return value


def _default_semantic_role(kind: str, section: str, target_type: str) -> str:
    normalized_section = section.strip().lower().replace("-", "_")
    normalized_target = target_type.strip().lower().replace("-", "_")
    if kind == "figure" and (
        normalized_target == "data_visualization" or normalized_section in RESULT_SECTIONS
    ):
        return "result_figure"
    if kind == "table" and normalized_section in RESULT_SECTIONS:
        return "result_table"
    return ""


def _is_empirical_result_artifact(
    *,
    kind: str,
    section: str,
    target_type: str,
    semantic_role: str,
) -> bool:
    normalized_section = section.strip().lower().replace("-", "_").replace(" ", "_")
    normalized_target = target_type.strip().lower().replace("-", "_").replace(" ", "_")
    normalized_role = semantic_role.strip().lower().replace("-", "_").replace(" ", "_")
    return (
        normalized_target == "data_visualization"
        or normalized_role in {"result_figure", "result_table", "result_plot"}
        or (kind in {"figure", "table"} and normalized_section in RESULT_SECTIONS)
    )


def _validate_artifact_path(
    path_text: str,
    *,
    materials_root: Path,
    kind: str,
) -> tuple[Path, str]:
    allowed_extensions = FIGURE_EXTENSIONS if kind == "figure" else TABLE_EXTENSIONS
    if Path(path_text).suffix.lower() not in allowed_extensions:
        raise ArtifactManifestError(
            f"{kind} path has unsupported extension {Path(path_text).suffix.lower()!r}: {path_text}"
        )

    resolved_asset = resolve_asset_path(
        path_text,
        materials_root=str(materials_root),
        require_within_root=True,
        allowed_extensions=allowed_extensions,
    )
    if resolved_asset.error:
        if "may not contain" in resolved_asset.error:
            raise ArtifactManifestError(f"{kind} path may not contain '..': {path_text}")
        if "escapes" in resolved_asset.error:
            raise ArtifactManifestError(f"{kind} path escapes materials_root: {path_text}")
        raise ArtifactManifestError(f"{kind} path invalid: {resolved_asset.error}")
    if not resolved_asset.exists:
        candidate = Path(resolved_asset.resolved_path or path_text).expanduser().resolve()
        raise ArtifactManifestError(f"{kind} file does not exist: {_posix(candidate)}")

    resolved = Path(resolved_asset.resolved_path or path_text).resolve()
    try:
        rel = resolved.relative_to(materials_root.resolve())
    except ValueError as exc:
        raise ArtifactManifestError(
            f"{kind} path escapes materials_root: {path_text}"
        ) from exc
    return resolved, rel.as_posix()


def _normalize_items(
    items: Iterable[Any],
    *,
    materials_root: Path,
    kind: str,
) -> list[NormalizedArtifact]:
    normalized: list[NormalizedArtifact] = []
    for raw in items:
        if not isinstance(raw, Mapping):
            raise ArtifactManifestError(f"{kind} artifacts must be objects.")
        artifact_id = _require_text(raw, "id", kind=kind)
        raw_path = _require_text(raw, "path", kind=kind)
        section = _require_text(raw, "section", kind=kind)
        caption = _require_text(raw, "caption", kind=kind)
        caption_mode = str(raw.get("caption_mode") or "locked").strip().lower()
        if caption_mode not in CAPTION_MODES:
            raise ArtifactManifestError(
                f"{kind} artifact {artifact_id} has unsupported caption_mode: {caption_mode}"
            )
        resolved, latex_path = _validate_artifact_path(
            raw_path,
            materials_root=materials_root,
            kind=kind,
        )
        target_type = str(raw.get("target_type") or "").strip()
        semantic_role = str(raw.get("semantic_role") or "").strip()
        if not semantic_role:
            semantic_role = _default_semantic_role(kind, section, target_type)
        if kind == "figure" and not target_type and semantic_role == "result_figure":
            target_type = "data_visualization"
        data_hash = str(raw.get("data_hash") or "").strip()
        code_hash = str(raw.get("code_hash") or "").strip()
        if _is_empirical_result_artifact(
            kind=kind,
            section=section,
            target_type=target_type,
            semantic_role=semantic_role,
        ):
            if not data_hash:
                raise ArtifactManifestError(
                    f"{kind} artifact {artifact_id} requires data_hash for empirical provenance."
                )
            if not code_hash:
                raise ArtifactManifestError(
                    f"{kind} artifact {artifact_id} requires code_hash for empirical provenance."
                )

        known_keys = {
            "id",
            "path",
            "section",
            "caption",
            "caption_mode",
            "target_type",
            "semantic_role",
            "data_hash",
            "code_hash",
            "title",
        }
        normalized.append(
            NormalizedArtifact(
                id=artifact_id,
                path=latex_path,
                resolved_path=resolved,
                latex_path=_posix(resolved),
                section=section,
                caption=caption,
                kind=kind,
                semantic_role=semantic_role,
                target_type=target_type,
                caption_mode=caption_mode,
                data_hash=data_hash,
                code_hash=code_hash,
                title=str(raw.get("title") or ""),
                extra={k: v for k, v in raw.items() if k not in known_keys},
            )
        )
    return normalized


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _normalize_v2_item(raw: Mapping[str, Any], *, kind: str) -> dict[str, Any]:
    files = raw.get("files") if isinstance(raw.get("files"), Mapping) else {}
    path_value = raw.get("path") or raw.get("file_path") or files.get("path")
    section = raw.get("section") or raw.get("section_type") or raw.get("paper_section")
    caption = raw.get("caption") or raw.get("locked_caption") or raw.get("title")
    role = raw.get("semantic_role") or raw.get("role")
    normalized = dict(raw)
    normalized["id"] = str(raw.get("id") or raw.get("label") or raw.get("artifact_id") or "")
    normalized["path"] = str(path_value or "")
    normalized["section"] = str(section or "results")
    normalized["caption"] = str(caption or "")
    if role:
        normalized["semantic_role"] = str(role)
    if kind == "figure":
        normalized.setdefault("target_type", raw.get("target_type") or "data_visualization")
    normalized.setdefault("caption_mode", raw.get("caption_mode") or "locked")
    normalized.setdefault("data_hash", raw.get("data_hash") or raw.get("source_hash") or "")
    normalized.setdefault("code_hash", raw.get("code_hash") or raw.get("producer_hash") or "")
    return normalized


def _items_from_v2(manifest: Mapping[str, Any], *, kind: str) -> list[dict[str, Any]]:
    direct = _as_list(manifest.get("figures" if kind == "figure" else "tables"))
    files = manifest.get("files") if isinstance(manifest.get("files"), Mapping) else {}
    nested = _as_list(files.get("figures" if kind == "figure" else "tables"))
    artifact_type = "figure" if kind == "figure" else "table"
    from_artifacts = [
        item
        for item in _as_list(manifest.get("artifacts"))
        if isinstance(item, Mapping)
        and str(item.get("type") or item.get("kind") or "").lower() == artifact_type
    ]
    return [
        _normalize_v2_item(item, kind=kind)
        for item in [*direct, *nested, *from_artifacts]
        if isinstance(item, Mapping)
    ]


def _normalize_manifest_version(version: Any) -> str:
    text = str(version or "").strip()
    if text in {MANIFEST_VERSION, MANIFEST_V2_VERSION, BUNDLE_V2_VERSION}:
        return text
    raise ArtifactManifestError(
        f"Artifact manifest version must be {MANIFEST_VERSION!r} or v2-compatible; got {version!r}."
    )


def _validate_v2_hashes(items: list[NormalizedArtifact], *, kind: str) -> None:
    pattern = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
    for item in items:
        if not _is_empirical_result_artifact(
            kind=kind,
            section=item.section,
            target_type=item.target_type,
            semantic_role=item.semantic_role,
        ):
            continue
        for key, value in {"data_hash": item.data_hash, "code_hash": item.code_hash}.items():
            if value and not pattern.match(value):
                raise ArtifactManifestError(
                    f"{kind} artifact {item.id} requires production v2 {key} as sha256:<64 hex>."
                )


def normalize_artifact_manifest(
    payload: Mapping[str, Any] | str | Path,
    *,
    manifest_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> NormalizedArtifactManifest:
    """Validate and normalize an artifact manifest v1 payload."""
    manifest, loaded_path = _as_mapping(payload)
    source_path = Path(manifest_path).expanduser().resolve() if manifest_path else loaded_path

    version = _normalize_manifest_version(manifest.get("version"))
    is_v2 = version in {MANIFEST_V2_VERSION, BUNDLE_V2_VERSION}
    materials_root = _resolve_materials_root(
        manifest.get("materials_root")
        or (manifest.get("files", {}) if isinstance(manifest.get("files"), Mapping) else {}).get("materials_root")
        or "replication/materials",
        manifest_path=source_path,
        repo_root=repo_root,
    )

    figures = _items_from_v2(manifest, kind="figure") if is_v2 else manifest.get("figures") or []
    tables = _items_from_v2(manifest, kind="table") if is_v2 else manifest.get("tables") or []
    if not isinstance(figures, list) or not isinstance(tables, list):
        raise ArtifactManifestError("Artifact manifest figures and tables must be lists.")

    normalized_figures = _normalize_items(figures, materials_root=materials_root, kind="figure")
    normalized_tables = _normalize_items(tables, materials_root=materials_root, kind="table")
    if is_v2:
        _validate_v2_hashes(normalized_figures, kind="figure")
        _validate_v2_hashes(normalized_tables, kind="table")

    return NormalizedArtifactManifest(
        version=version,
        materials_root=materials_root,
        source_agent=str(manifest.get("source_agent") or manifest.get("producer") or ""),
        run_status=str(manifest.get("run_status") or manifest.get("status") or ""),
        claim_level=str(manifest.get("claim_level") or ""),
        diagnostics=[
            dict(item)
            for item in _as_list(manifest.get("diagnostics"))
            if isinstance(item, Mapping)
        ],
        allowed_paper_uses=_string_list(manifest.get("allowed_paper_uses")),
        forbidden_claims=_string_list(manifest.get("forbidden_claims")),
        figures=normalized_figures,
        tables=normalized_tables,
    )


def load_artifact_manifest(
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> NormalizedArtifactManifest:
    """Load a manifest JSON file and return its normalized representation."""
    return normalize_artifact_manifest(Path(manifest_path), repo_root=repo_root)


def manifest_to_figure_specs(
    payload: Mapping[str, Any] | str | Path | NormalizedArtifactManifest,
    *,
    manifest_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> list[FigureSpec]:
    """Convert manifest figures into file-backed FigureSpec objects."""
    manifest = (
        payload
        if isinstance(payload, NormalizedArtifactManifest)
        else normalize_artifact_manifest(payload, manifest_path=manifest_path, repo_root=repo_root)
    )
    return [
        FigureSpec(
            id=item.id,
            caption=item.caption,
            description=item.title,
            section=item.section,
            section_type=item.section,
            file_path=item.latex_path,
            derived_file_path=item.latex_path,
            auto_generate=False,
            target_type=item.target_type or "data_visualization",
            semantic_role=item.semantic_role or "result_figure",
            caption_mode=item.caption_mode,
            data_hash=item.data_hash,
            code_hash=item.code_hash,
        )
        for item in manifest.figures
    ]


def manifest_to_table_specs(
    payload: Mapping[str, Any] | str | Path | NormalizedArtifactManifest,
    *,
    manifest_path: str | Path | None = None,
    repo_root: str | Path | None = None,
) -> list[TableSpec]:
    """Convert manifest tables into file-backed TableSpec objects."""
    manifest = (
        payload
        if isinstance(payload, NormalizedArtifactManifest)
        else normalize_artifact_manifest(payload, manifest_path=manifest_path, repo_root=repo_root)
    )
    return [
        TableSpec(
            id=item.id,
            caption=item.caption,
            description=item.title,
            section=item.section,
            section_type=item.section,
            file_path=item.latex_path,
            auto_generate=False,
            semantic_role=item.semantic_role,
            caption_mode=item.caption_mode,
            data_hash=item.data_hash,
            code_hash=item.code_hash,
        )
        for item in manifest.tables
    ]


def append_manifest_artifacts_to_metadata(
    metadata: PaperMetaData,
    manifest_path: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> PaperMetaData:
    """Mutate metadata with file-backed figures/tables from a manifest file."""
    manifest = load_artifact_manifest(manifest_path, repo_root=repo_root)
    metadata.materials_root = _posix(manifest.materials_root)
    metadata.figures.extend(manifest_to_figure_specs(manifest))
    metadata.tables.extend(manifest_to_table_specs(manifest))
    return metadata
