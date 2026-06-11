"""Configuration and backend discovery for skill4econ.

Resolves external dependencies (Stata executable, optional DEA backend path)
through a chain of sources, from most specific to most general:

    1. The per-run spec dict (e.g. spec["stata"]["executable"]).
    2. Environment variables (SKILL4ECON_STATA, SKILL4ECON_DEA_BACKEND).
    3. A user config file at ~/.skill4econ/config.toml.
    4. PATH lookup via shutil.which (Stata only).
    5. Common install directories on Windows, macOS, and Linux (Stata only).

If nothing resolves, the resolver returns None and the wrapper writes a
missing_dependency manifest. The package itself ships a vendored DEA backend
under skill4econ.backends.dea, so DEA resolution falls through to the vendored
module instead of erroring.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - older interpreters
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        tomllib = None  # type: ignore[assignment]


USER_CONFIG_PATH = Path.home() / ".skill4econ" / "config.toml"

ENV_STATA = "SKILL4ECON_STATA"
ENV_DEA_BACKEND = "SKILL4ECON_DEA_BACKEND"
ENV_USER_CONFIG = "SKILL4ECON_CONFIG"

STATA_EXECUTABLE_NAMES = (
    "stata-mp",
    "stata-se",
    "stata-be",
    "stata",
    "StataMP-64",
    "StataSE-64",
    "StataBE-64",
    "StataMP",
    "StataSE",
    "StataBE",
)


def _load_user_config() -> dict[str, Any]:
    path = Path(os.environ.get(ENV_USER_CONFIG) or USER_CONFIG_PATH)
    if not path.exists() or tomllib is None:
        return {}
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _from_spec(spec: dict[str, Any] | None, *keys: str) -> Any:
    if not spec:
        return None
    node: Any = spec
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
        if node is None:
            return None
    return node


def _candidate_to_path(value: Any) -> Path | None:
    if value is None:
        return None
    try:
        path = Path(str(value)).expanduser()
    except Exception:
        return None
    return path if path.exists() else None


def _windows_stata_candidates() -> list[Path]:
    candidates: list[Path] = []
    drives = [f"{ch}:\\" for ch in "CDEFGH" if Path(f"{ch}:\\").exists()]
    for drive in drives:
        root = Path(drive)
        for parent in root.glob("stata*"):
            for name in STATA_EXECUTABLE_NAMES:
                exe = parent / f"{name}.exe"
                if exe.exists():
                    candidates.append(exe)
        program_files = root / "Program Files"
        if program_files.exists():
            for parent in program_files.glob("Stata*"):
                for name in STATA_EXECUTABLE_NAMES:
                    exe = parent / f"{name}.exe"
                    if exe.exists():
                        candidates.append(exe)
    return candidates


def _posix_stata_candidates() -> list[Path]:
    candidates: list[Path] = []
    for root in (Path("/usr/local"), Path("/opt"), Path.home()):
        if not root.exists():
            continue
        for parent in root.glob("stata*"):
            for name in STATA_EXECUTABLE_NAMES:
                exe = parent / name
                if exe.exists() and os.access(exe, os.X_OK):
                    candidates.append(exe)
    apps = Path("/Applications")
    if apps.exists():
        for app in apps.glob("Stata*/StataMP.app/Contents/MacOS/StataMP"):
            candidates.append(app)
        for app in apps.glob("Stata*/StataSE.app/Contents/MacOS/StataSE"):
            candidates.append(app)
        for app in apps.glob("Stata*/StataBE.app/Contents/MacOS/StataBE"):
            candidates.append(app)
    return candidates


def _path_candidates() -> list[Path]:
    found: list[Path] = []
    for name in STATA_EXECUTABLE_NAMES:
        located = shutil.which(name)
        if located:
            found.append(Path(located))
    return found


def resolve_stata(spec: dict[str, Any] | None = None) -> tuple[Path | None, str]:
    """Return (path, source) for the Stata executable, or (None, "missing")."""
    spec_value = _from_spec(spec, "stata", "executable") or _from_spec(spec, "stata_executable")
    path = _candidate_to_path(spec_value)
    if path:
        return path, "spec"

    env_value = os.environ.get(ENV_STATA)
    path = _candidate_to_path(env_value)
    if path:
        return path, f"env:{ENV_STATA}"

    user_cfg = _load_user_config()
    cfg_value = _from_spec(user_cfg, "stata", "executable")
    path = _candidate_to_path(cfg_value)
    if path:
        return path, "user_config"

    for path in _path_candidates():
        return path, "PATH"

    candidates = _windows_stata_candidates() if sys.platform.startswith("win") else _posix_stata_candidates()
    for path in candidates:
        return path, "common_dirs"

    return None, "missing"


def resolve_stata_batch_args(executable: Path, spec: dict[str, Any] | None = None) -> list[str]:
    """Pick the batch-mode flag for the resolved executable.

    Stata on Windows historically uses ``/e do <file>``; Unix builds use
    ``-b do <file>``. Allow per-spec or user-config override.
    """
    override = _from_spec(spec, "stata", "batch_args")
    if override:
        return [str(v) for v in override]
    user_cfg = _load_user_config()
    override = _from_spec(user_cfg, "stata", "batch_args")
    if override:
        return [str(v) for v in override]
    name = executable.name.lower()
    if name.endswith(".exe") or sys.platform.startswith("win"):
        return ["/e", "do"]
    return ["-b", "do"]


def resolve_dea_backend(spec: dict[str, Any] | None = None) -> tuple[Path | None, str]:
    """Return (path, source) for an external DEA backend override.

    The vendored backend under skill4econ.backends.dea is the default. An
    override is only useful if the user has a customized fork and wants to
    keep using it.
    """
    spec_value = _from_spec(spec, "dea", "backend_path") or _from_spec(spec, "dea_backend_path")
    path = _candidate_to_path(spec_value)
    if path:
        return path, "spec"

    env_value = os.environ.get(ENV_DEA_BACKEND)
    path = _candidate_to_path(env_value)
    if path:
        return path, f"env:{ENV_DEA_BACKEND}"

    user_cfg = _load_user_config()
    cfg_value = _from_spec(user_cfg, "dea", "backend_path")
    path = _candidate_to_path(cfg_value)
    if path:
        return path, "user_config"

    return None, "vendored"


def stata_discovery_chain() -> list[str]:
    """Human-readable description of the discovery chain, for error messages."""
    return [
        "spec.stata.executable / spec.stata_executable",
        f"env {ENV_STATA}",
        f"user config {USER_CONFIG_PATH}",
        "PATH lookup (stata, stata-mp, StataMP-64, ...)",
        "common install dirs (Win: <drive>:\\stata*, Program Files\\Stata*; "
        "POSIX: /usr/local/stata*, /opt/stata*, /Applications/Stata*)",
    ]


def dea_discovery_chain() -> list[str]:
    return [
        "spec.dea.backend_path",
        f"env {ENV_DEA_BACKEND}",
        f"user config {USER_CONFIG_PATH}",
        "vendored backend: skill4econ.backends.dea",
    ]
