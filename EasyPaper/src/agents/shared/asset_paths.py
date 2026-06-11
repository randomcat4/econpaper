"""
Shared asset path resolution helpers.

The generation stack accepts metadata-local paths as well as paths relative to
``materials_root``.  This module keeps that precedence consistent across direct
metadata loading, validation, figure collection, and table conversion.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class ResolvedAssetPath:
    original_path: str
    resolved_path: Optional[str]
    candidates: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def exists(self) -> bool:
        return bool(self.resolved_path and os.path.exists(self.resolved_path))


def _norm(path: str) -> str:
    return os.path.normpath(os.path.expanduser(str(path)))


def _path_segments(path: str) -> list[str]:
    return [part for part in str(path or "").replace("\\", "/").split("/") if part]


def _is_relative_to(path: str, root: str) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def _candidate_paths(
    path: str,
    *,
    materials_root: Optional[str] = None,
    fallback_base: Optional[str] = None,
    extra_bases: Optional[Iterable[str]] = None,
) -> list[str]:
    raw = str(path or "").strip()
    if not raw:
        return []
    if os.path.isabs(raw):
        return [_norm(raw)]

    bases: list[str] = []
    for base in [materials_root, fallback_base, *(extra_bases or [])]:
        if base and str(base).strip() and str(base) not in bases:
            bases.append(str(base))

    if not bases:
        return [_norm(raw)]
    return [_norm(os.path.join(base, raw)) for base in bases]


def resolve_asset_path(
    path: str,
    *,
    materials_root: Optional[str] = None,
    fallback_base: Optional[str] = None,
    extra_bases: Optional[Iterable[str]] = None,
    require_within_root: bool = False,
    allowed_extensions: Optional[Iterable[str]] = None,
) -> ResolvedAssetPath:
    """
    Resolve an asset path with ``materials_root`` precedence.

    Resolution order:
    1. absolute path unchanged
    2. ``materials_root`` + relative path
    3. fallback base + relative path
    4. any extra bases + relative path
    """
    raw = str(path or "").strip()
    if any(segment == ".." for segment in _path_segments(raw)):
        return ResolvedAssetPath(
            original_path=raw,
            resolved_path=None,
            candidates=[],
            error=f"Path may not contain '..': {raw}",
        )

    allowed = {str(ext).lower() for ext in (allowed_extensions or [])}
    if allowed and Path(raw).suffix.lower() not in allowed:
        return ResolvedAssetPath(
            original_path=raw,
            resolved_path=None,
            candidates=[],
            error=f"Unsupported file extension {Path(raw).suffix!r}: {raw}",
        )

    candidates = _candidate_paths(
        path,
        materials_root=materials_root,
        fallback_base=fallback_base,
        extra_bases=extra_bases,
    )
    if require_within_root:
        root = materials_root or fallback_base
        if not root:
            return ResolvedAssetPath(
                original_path=raw,
                resolved_path=None,
                candidates=candidates,
                error="Root-confined resolution requires materials_root or fallback_base.",
            )
        escaping = [candidate for candidate in candidates if not _is_relative_to(candidate, str(root))]
        if escaping:
            return ResolvedAssetPath(
                original_path=raw,
                resolved_path=None,
                candidates=candidates,
                error=f"Path escapes materials_root: {raw}",
            )
    for candidate in candidates:
        if os.path.exists(candidate):
            return ResolvedAssetPath(
                original_path=str(path or ""),
                resolved_path=candidate,
                candidates=candidates,
            )
    return ResolvedAssetPath(
        original_path=str(path or ""),
        resolved_path=candidates[0] if candidates else None,
        candidates=candidates,
    )


def format_resolution_error(kind: str, path: str, resolved: ResolvedAssetPath) -> str:
    candidates = ", ".join(resolved.candidates) if resolved.candidates else "<none>"
    if resolved.error:
        return f"{kind} file invalid: {path} ({resolved.error}; candidates: {candidates})"
    return (
        f"{kind} file not found: {path} "
        f"(resolved: {resolved.resolved_path}; candidates: {candidates})"
    )
