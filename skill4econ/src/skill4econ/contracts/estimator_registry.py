from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core import PACKAGE_ROOT, ROOT


DEFAULT_REGISTRY = PACKAGE_ROOT / "configs" / "estimator_registry.yaml"


def load_estimator_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path) if path else DEFAULT_REGISTRY
    if not registry_path.is_absolute():
        workspace_path = ROOT.parent / registry_path
        repo_path = ROOT / registry_path
        registry_path = workspace_path if workspace_path.exists() else repo_path
    text = registry_path.read_text(encoding="utf-8")
    if registry_path.suffix.lower() == ".json":
        payload = json.loads(text)
    else:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover - environment dependent
            raise RuntimeError("PyYAML is required to read estimator_registry.yaml.") from exc
        payload = yaml.safe_load(text) or {}
    if not isinstance(payload, dict):
        raise ValueError("Estimator registry must be a mapping/object.")
    return payload


def _backend_available(defn: dict[str, Any], dependency_report: dict[str, Any], engine_policy: str) -> tuple[bool, str]:
    engines = [str(item).lower() for item in defn.get("engines") or []]
    if engine_policy == "python":
        engines = [engine for engine in engines if engine == "python"]
    elif engine_policy == "stata":
        engines = [engine for engine in engines if engine == "stata"]
    if not engines:
        return False, f"engine_policy={engine_policy} excludes this estimator backend."
    if "python" in engines:
        return True, "python backend available"
    if "stata" in engines and dependency_report.get("stata", {}).get("available"):
        return True, "Stata executable available"
    if "r" in engines and dependency_report.get("r", {}).get("available"):
        return True, "Rscript available"
    missing = []
    if "stata" in engines:
        missing.append("Stata")
    if "r" in engines:
        missing.append("Rscript")
    return False, f"backend_unavailable: {'/'.join(missing) or 'unknown'}"


def _preferred_engine(defn: dict[str, Any], dependency_report: dict[str, Any], engine_policy: str) -> str | None:
    engines = [str(item).lower() for item in defn.get("engines") or []]
    if engine_policy == "python":
        return "python" if "python" in engines else None
    if engine_policy == "stata":
        return "stata" if "stata" in engines and dependency_report.get("stata", {}).get("available") else None
    if "stata" in engines and dependency_report.get("stata", {}).get("available"):
        return "stata"
    if "python" in engines:
        return "python"
    if "r" in engines and dependency_report.get("r", {}).get("available"):
        return "r"
    return None


def _method_for_engine(defn: dict[str, Any], engine: str | None) -> str | None:
    if engine == "python":
        return defn.get("python_method")
    if engine == "stata":
        return defn.get("stata_method")
    if engine == "r":
        return defn.get("r_method")
    return None


def route_did_estimators(
    did_design: dict[str, Any],
    *,
    spec: dict[str, Any],
    dependency_report: dict[str, Any],
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_estimator_registry()
    did_registry = registry.get("did") if isinstance(registry.get("did"), dict) else {}
    design_type = str(did_design.get("design_type") or "unknown")
    recommended = list(did_design.get("recommended_estimators") or [])
    aliases = {"cs_did_attgt_not_yet": "cs_did_attgt"}
    requested = spec.get("estimators") or spec.get("did_estimators") or recommended
    requested = [aliases.get(str(item), str(item)) for item in requested]
    exclude = {str(item) for item in (spec.get("exclude_estimators") or [])}
    engine_policy = str(spec.get("engine_policy") or "stata_first").lower()
    if engine_policy not in {"stata_first", "stata", "python"}:
        engine_policy = "stata_first"

    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for name in requested:
        if name in seen:
            continue
        seen.add(name)
        if name in exclude:
            skipped.append({"estimator": name, "reason": "excluded_by_user"})
            continue
        defn = did_registry.get(name)
        if not isinstance(defn, dict):
            skipped.append({"estimator": name, "reason": "not_in_registry"})
            continue
        allowed = set(str(item) for item in defn.get("allowed_designs") or [])
        if design_type not in allowed:
            skipped.append(
                {
                    "estimator": name,
                    "reason": "design_not_allowed",
                    "design_type": design_type,
                    "allowed_designs": sorted(allowed),
                }
            )
            continue
        available, availability_reason = _backend_available(defn, dependency_report, engine_policy)
        if not available:
            skipped.append(
                {
                    "estimator": name,
                    "reason": availability_reason,
                    "backend": defn.get("backend"),
                    "role": defn.get("role"),
                }
            )
            continue
        engine = _preferred_engine(defn, dependency_report, engine_policy)
        method = _method_for_engine(defn, engine)
        if not method:
            skipped.append(
                {
                    "estimator": name,
                    "reason": "adapter_not_wired",
                    "engine": engine,
                    "backend": defn.get("backend"),
                    "role": defn.get("role"),
                }
            )
            continue
        role = str(defn.get("role") or "supporting")
        main_allowed = bool(defn.get("main_allowed", False))
        if design_type == "staggered_adoption" and name == "twfe":
            main_allowed = False
            role = "benchmark_not_main"
        elif name == "twfe" and design_type in {"two_by_two", "single_timing"}:
            main_allowed = True
            role = "main_or_benchmark"
        critical = bool(role in {"main_if_staggered", "covariate_adjusted_main"})
        if name == "twfe" and design_type in {"two_by_two", "single_timing"}:
            critical = True
        selected.append(
            {
                "estimator": name,
                "engine": engine,
                "method": method,
                "backend": defn.get("backend"),
                "role": role,
                "main_allowed": main_allowed,
                "critical": critical,
                "availability": availability_reason,
            }
        )

    if design_type == "staggered_adoption":
        main = [item for item in selected if item.get("main_allowed") and item.get("estimator") != "twfe"]
        if not main:
            skipped.append(
                {
                    "estimator": "modern_staggered_did",
                    "reason": "no_modern_staggered_estimator_selected",
                    "required_fix": "Enable csdid/cs_did_attgt/did_imputation or use a supported R/Stata backend.",
                }
            )
    return {
        "design_type": design_type,
        "engine_policy": engine_policy,
        "selected_estimators": selected,
        "skipped_estimators": skipped,
        "routing_policy": {
            "twfe_not_main_for_staggered": True,
            "no_fake_fallback": True,
            "respects_engine_policy": True,
        },
    }


def write_estimator_routing(run_dir: Path, routing: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "selected_estimators.json").write_text(
        json.dumps({"selected_estimators": routing.get("selected_estimators", [])}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "skipped_estimators.json").write_text(
        json.dumps({"skipped_estimators": routing.get("skipped_estimators", [])}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "estimator_routing.json").write_text(
        json.dumps(routing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
