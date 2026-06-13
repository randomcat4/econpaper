from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


EVIDENCE_PACK_SCHEMA_VERSION = "evidence_pack.v2"
KNOWN_ARTIFACT_TYPES = {
    "model_table",
    "event_study",
    "pretrend_test",
    "cohort_table",
    "robustness_grid",
    "placebo_tests",
    "heterogeneity",
    "summary_stats",
    "figure_manifest",
    "rdd_bandwidth",
    "rdd_diagnostics",
    "rdd_density_test",
    "covariate_continuity",
    "spatial_impact_decomposition",
    "spatial_model_coefficients",
    "spatial_w_metadata",
    "spatial_w_audit",
    "spatial_backend_status",
    "w3_null_imposed_wcr",
    "w3_effective_f",
    "w3_conley",
    "w3_romano_wolf",
    "diagnostic",
    "figure",
    "table",
    "metadata",
    "supporting_artifact",
}
TYPE_ALIASES = {
    "figure_manifest": "figure_manifest",
    "figures_manifest": "figure_manifest",
    "figure_manifest_yaml": "figure_manifest",
    "summary_statistics": "summary_stats",
    "summary_stat": "summary_stats",
    "placebo": "placebo_tests",
    "placebo_test": "placebo_tests",
    "heterogeneity_splits": "heterogeneity",
    "cohort": "cohort_table",
    "cohorts": "cohort_table",
    "pretrend": "pretrend_test",
    "pre_trend": "pretrend_test",
    "eventstudy": "event_study",
    "event-study": "event_study",
    "bandwidth": "rdd_bandwidth",
    "density_test": "rdd_density_test",
    "manipulation_test": "rdd_density_test",
    "covariate_balance": "covariate_continuity",
    "spatial_impacts": "spatial_impact_decomposition",
    "spatial_impact": "spatial_impact_decomposition",
    "sdm_impacts": "spatial_impact_decomposition",
    "spatial_coefficients": "spatial_model_coefficients",
    "spatial_coef": "spatial_model_coefficients",
    "w_metadata": "spatial_w_metadata",
    "w_audit": "spatial_w_audit",
    "spatial_backend": "spatial_backend_status",
    "null_imposed_wcr": "w3_null_imposed_wcr",
    "wild_cluster_randomization": "w3_null_imposed_wcr",
    "mop_effective_f": "w3_effective_f",
    "effective_f": "w3_effective_f",
    "conley_full": "w3_conley",
    "romano_wolf": "w3_romano_wolf",
}
EVIDENCE_ITEM_REQUIRED = {
    "evidence_id",
    "artifact_id",
    "statistic",
    "value",
    "variable",
    "provenance_hash",
}
ARTIFACT_MANIFEST_TYPE_FIELD = "evidence_type"


@dataclass
class EvidencePackIssue:
    code: str
    severity: str
    message: str
    path: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "details": self.details,
        }


@dataclass
class EvidencePackResult:
    pack: dict[str, Any]
    status: str = "passed"
    issues: list[EvidencePackIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(
        self,
        code: str,
        severity: str,
        message: str,
        *,
        path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(EvidencePackIssue(code, severity, message, path, details or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "pack": self.pack,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def build_evidence_pack(
    *,
    evidence_ledger: dict[str, Any],
    run_dir: str | Path | None = None,
    artifact_manifest: dict[str, Any] | None = None,
    run_validation: dict[str, Any] | None = None,
    provenance: dict[str, Any] | None = None,
) -> EvidencePackResult:
    run_path = Path(run_dir) if run_dir is not None else None
    artifact_manifest = artifact_manifest or {}
    run_validation = run_validation or {}
    provenance = provenance or {}
    artifact_type_field = _artifact_manifest_type_field(artifact_manifest)
    pack = {
        "schema_version": EVIDENCE_PACK_SCHEMA_VERSION,
        "source": {
            "run_id": evidence_ledger.get("run_id") or artifact_manifest.get("run_id"),
            "workflow": artifact_manifest.get("workflow") or run_validation.get("method_or_workflow"),
            "data_provenance": run_validation.get("data_provenance") or provenance.get("data_provenance") or "unknown",
        },
        "artifacts": _normalized_artifacts(evidence_ledger, artifact_manifest, run_path, artifact_type_field=artifact_type_field),
        "evidence_items": [
            dict(item)
            for item in evidence_ledger.get("evidence_items", [])
            if isinstance(item, dict)
        ],
        "variable_semantics": evidence_ledger.get("variable_semantics", {}),
    }
    result = validate_evidence_pack(pack, run_dir=run_path)
    _validate_artifact_manifest_contract(artifact_manifest, result)
    pack["validation"] = {
        "status": result.status,
        "has_hard_blocks": result.has_hard_blocks,
        "issues": [issue.to_dict() for issue in result.issues],
    }
    result.pack = pack
    return result


def write_evidence_pack(
    *,
    evidence_ledger: dict[str, Any],
    run_dir: str | Path | None,
    out_dir: str | Path,
    artifact_manifest_path: str | Path | None = None,
    run_validation_path: str | Path | None = None,
    provenance_path: str | Path | None = None,
) -> EvidencePackResult:
    run_path = Path(run_dir) if run_dir is not None else None
    out_path = Path(out_dir)
    artifact_manifest = _load_optional_json(Path(artifact_manifest_path)) if artifact_manifest_path else {}
    run_validation = _load_optional_json(Path(run_validation_path)) if run_validation_path else {}
    provenance = _load_optional_provenance(Path(provenance_path)) if provenance_path else {}
    result = build_evidence_pack(
        evidence_ledger=evidence_ledger,
        run_dir=run_path,
        artifact_manifest=artifact_manifest,
        run_validation=run_validation,
        provenance=provenance,
    )
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    out_path.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result.pack, ensure_ascii=False, indent=2)
    (out_path / "evidence_pack.json").write_text(text, encoding="utf-8")
    (internal / "evidence_pack.json").write_text(text, encoding="utf-8")
    (internal / "evidence_pack_validation.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def load_evidence_pack(path: str | Path) -> EvidencePackResult:
    pack_path = Path(path)
    if not pack_path.exists():
        result = EvidencePackResult(pack={})
        result.add_issue("evidence_pack_missing", "hard_block", f"EvidencePack v2 file is missing: {pack_path}", path=str(pack_path))
        return result
    try:
        payload = json.loads(pack_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        result = EvidencePackResult(pack={})
        result.add_issue("evidence_pack_invalid_json", "hard_block", f"Could not parse EvidencePack v2: {exc}", path=str(pack_path))
        return result
    if not isinstance(payload, dict):
        result = EvidencePackResult(pack={})
        result.add_issue("evidence_pack_not_object", "hard_block", "EvidencePack v2 must be a JSON object.", path=str(pack_path))
        return result
    return validate_evidence_pack(payload, require_embedded_validation=True)


def validate_evidence_pack(
    pack: dict[str, Any],
    *,
    run_dir: str | Path | None = None,
    require_embedded_validation: bool = False,
) -> EvidencePackResult:
    result = EvidencePackResult(pack=pack)
    run_path = Path(run_dir) if run_dir is not None else None
    if pack.get("schema_version") != EVIDENCE_PACK_SCHEMA_VERSION:
        result.add_issue(
            "evidence_pack_schema_version_invalid",
            "hard_block",
            f"Expected schema_version={EVIDENCE_PACK_SCHEMA_VERSION}.",
        )
    artifacts = pack.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        result.add_issue("evidence_pack_artifacts_missing", "hard_block", "EvidencePack v2 requires at least one artifact.")
        artifacts = []
    evidence_items = pack.get("evidence_items")
    if not isinstance(evidence_items, list):
        result.add_issue("evidence_pack_items_not_list", "hard_block", "evidence_items must be a list.")
        evidence_items = []
    embedded = pack.get("validation")
    if require_embedded_validation and not isinstance(embedded, dict):
        result.add_issue("evidence_pack_validation_missing", "hard_block", "EvidencePack v2 requires embedded validation metadata.")
    elif isinstance(embedded, dict) and (embedded.get("has_hard_blocks") or embedded.get("status") == "failed"):
        result.add_issue(
            "evidence_pack_persisted_validation_failed",
            "hard_block",
            "EvidencePack v2 was built with hard validation blocks.",
            details={"issues": embedded.get("issues", [])},
        )

    artifact_ids: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            result.add_issue("evidence_pack_artifact_not_object", "hard_block", "Each artifact must be an object.")
            continue
        artifact_id = str(artifact.get("artifact_id") or "")
        artifact_type = str(artifact.get("artifact_type") or "")
        rel_path = str(artifact.get("path") or "")
        if not artifact_id or not artifact_type or not rel_path:
            result.add_issue(
                "evidence_pack_artifact_missing_required_field",
                "hard_block",
                "Each artifact requires artifact_id, artifact_type, and path.",
                details={"artifact": artifact},
            )
        if artifact_id in artifact_ids:
            result.add_issue("evidence_pack_duplicate_artifact_id", "hard_block", f"Duplicate artifact_id `{artifact_id}`.")
        artifact_ids.add(artifact_id)
        if artifact_type not in KNOWN_ARTIFACT_TYPES:
            result.add_issue(
                "evidence_pack_unknown_artifact_type",
                "hard_block",
                f"Unknown artifact_type `{artifact_type}`.",
                details={"artifact_id": artifact_id},
            )
        if _path_escapes_package(rel_path):
            result.add_issue(
                "evidence_pack_artifact_path_unsafe",
                "hard_block",
                "Artifact paths must be relative package paths.",
                path=rel_path,
                details={"artifact_id": artifact_id},
            )
        if run_path and rel_path and not _path_escapes_package(rel_path):
            exists = (run_path / rel_path).exists()
            if artifact.get("exists") is True and not exists:
                result.add_issue(
                    "evidence_pack_declared_artifact_missing",
                    "hard_block",
                    "Artifact is declared as existing but does not exist under the run directory.",
                    path=rel_path,
                    details={"artifact_id": artifact_id},
                )

    evidence_ids: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, dict):
            result.add_issue("evidence_pack_item_not_object", "hard_block", "Each evidence item must be an object.")
            continue
        evidence_id = str(item.get("evidence_id") or "")
        if evidence_id in evidence_ids:
            result.add_issue("evidence_pack_duplicate_evidence_id", "hard_block", f"Duplicate evidence_id `{evidence_id}`.")
        evidence_ids.add(evidence_id)
        missing = sorted(field for field in EVIDENCE_ITEM_REQUIRED if item.get(field) in {None, ""})
        if missing:
            result.add_issue(
                "evidence_pack_item_missing_required_field",
                "hard_block",
                "Evidence items require stable ids, values, variables, and provenance hashes.",
                details={"evidence_id": evidence_id or None, "missing": missing},
            )
        artifact_id = str(item.get("artifact_id") or "")
        if artifact_id and artifact_id not in artifact_ids:
            result.add_issue(
                "evidence_pack_item_artifact_missing",
                "hard_block",
                "Evidence item references an artifact_id not present in the pack.",
                details={"evidence_id": evidence_id, "artifact_id": artifact_id},
            )

    result.status = "failed" if result.has_hard_blocks else "passed"
    return result


def _artifact_manifest_type_field(artifact_manifest: dict[str, Any]) -> str:
    contract = artifact_manifest.get("evidence_contract") if isinstance(artifact_manifest, dict) else None
    if isinstance(contract, dict) and isinstance(contract.get("artifact_type_field"), str):
        return str(contract["artifact_type_field"])
    return ARTIFACT_MANIFEST_TYPE_FIELD


def _validate_artifact_manifest_contract(artifact_manifest: dict[str, Any], result: EvidencePackResult) -> None:
    if not isinstance(artifact_manifest, dict):
        return
    artifacts = artifact_manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return
    contract = artifact_manifest.get("evidence_contract")
    if not isinstance(contract, dict):
        result.add_issue(
            "artifact_manifest_contract_missing",
            "hard_block",
            "Artifact manifest with artifacts must declare evidence_contract for EvidencePack v2.",
        )
        return
    if contract.get("schema_version") != EVIDENCE_PACK_SCHEMA_VERSION:
        result.add_issue(
            "artifact_manifest_schema_version_invalid",
            "hard_block",
            f"Expected artifact_manifest.evidence_contract.schema_version={EVIDENCE_PACK_SCHEMA_VERSION}.",
            details={"actual": contract.get("schema_version")},
        )
    if contract.get("artifact_type_field") != ARTIFACT_MANIFEST_TYPE_FIELD:
        result.add_issue(
            "artifact_manifest_type_field_invalid",
            "hard_block",
            f"Expected artifact_manifest.evidence_contract.artifact_type_field={ARTIFACT_MANIFEST_TYPE_FIELD}.",
            details={"actual": contract.get("artifact_type_field")},
        )


def artifact_types_from_pack(pack: dict[str, Any]) -> set[str]:
    return {
        str(artifact.get("artifact_type"))
        for artifact in pack.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("artifact_type")
    }


def normalize_artifact_type(raw_type: Any, path: Any = "", role: Any = "") -> str:
    raw = str(raw_type or "").strip().lower()
    path_text = str(path or "").replace("\\", "/").lower()
    name = path_text.rsplit("/", 1)[-1]
    role_text = str(role or "").lower()
    text = " ".join([raw, role_text, path_text])
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    if cleaned in TYPE_ALIASES:
        return TYPE_ALIASES[cleaned]
    if "model_table" in text or "coefficient" in text:
        return "model_table"
    if cleaned in {"event_study", "eventstudy"} or name in {"event_study.csv", "event_study.json"}:
        return "event_study"
    if "pretrend" in text or "pre_trend" in text:
        return "pretrend_test"
    if "cohort" in text:
        return "cohort_table"
    if "robustness_grid" in text or ("robustness" in text and "grid" in text):
        return "robustness_grid"
    if "placebo" in text:
        return "placebo_tests"
    if "heterogeneity" in text:
        return "heterogeneity"
    if "summary_stats" in text or "summary_statistics" in text or "data_summary" in text:
        return "summary_stats"
    if "figures/manifest" in text or "figure_manifest" in text or "figures_manifest" in text:
        return "figure_manifest"
    if "rdd_bandwidth" in text:
        return "rdd_bandwidth"
    if "rdd_diagnostics" in text:
        return "rdd_diagnostics"
    if "rdd_density_test" in text or "density_test" in text or "manipulation_test" in text:
        return "rdd_density_test"
    if "covariate_continuity" in text:
        return "covariate_continuity"
    if (
        "spatial_impact_decomposition" in text
        or "spatialreg_live_impacts" in text
        or "spxtregress_live_impacts" in text
        or "xsmle_live_impacts" in text
        or ("xsmle" in text and "impacts" in text)
    ):
        return "spatial_impact_decomposition"
    if (
        "spatial_model_coefficients" in text
        or "spatialreg_live_coefficients" in text
        or ("spxtregress" in text and "coefficients" in text)
        or ("xsmle" in text and "coefficients" in text)
    ):
        return "spatial_model_coefficients"
    if "w_metadata" in text:
        return "spatial_w_metadata"
    if "w_audit" in text or "spatial_w_audit" in text:
        return "spatial_w_audit"
    if "spatial_backend_status" in text or "live_backend_certification_matrix" in text:
        return "spatial_backend_status"
    if "null_imposed_wcr" in text or "wild_cluster_randomization" in text:
        return "w3_null_imposed_wcr"
    if "mop_effective_f" in text or "effective_f" in text:
        return "w3_effective_f"
    if "conley" in text and ("full" in text or "covariance" in text):
        return "w3_conley"
    if "romano_wolf" in text or "romano-wolf" in text:
        return "w3_romano_wolf"
    if cleaned in {"diagnostic", "metadata", "table", "figure"}:
        return cleaned
    if cleaned in KNOWN_ARTIFACT_TYPES:
        return cleaned
    return "supporting_artifact"


def _normalized_artifacts(
    evidence_ledger: dict[str, Any],
    artifact_manifest: dict[str, Any],
    run_dir: Path | None,
    *,
    artifact_type_field: str = ARTIFACT_MANIFEST_TYPE_FIELD,
) -> list[dict[str, Any]]:
    artifacts: dict[tuple[str, str], dict[str, Any]] = {}
    for item in evidence_ledger.get("artifacts", []) if isinstance(evidence_ledger, dict) else []:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path") or "")
        artifact_type = normalize_artifact_type(
            item.get("artifact_type") or item.get("evidence_type") or item.get("type"),
            rel_path,
            item.get("role"),
        )
        key = (rel_path, artifact_type)
        artifacts[key] = {
            "artifact_id": str(item.get("artifact_id") or _artifact_id(artifact_type, rel_path)),
            "artifact_type": artifact_type,
            "path": rel_path,
            "hash": item.get("hash") or _safe_file_hash(run_dir, rel_path),
            "claimable": bool(item.get("claimable")),
            "exists": True if item.get("exists") is True else _path_exists(run_dir, rel_path),
            "source": "evidence_ledger",
        }
    for item in artifact_manifest.get("artifacts", []) if isinstance(artifact_manifest, dict) else []:
        if not isinstance(item, dict):
            continue
        rel_path = str(item.get("path") or "")
        artifact_type = normalize_artifact_type(
            item.get(artifact_type_field) or item.get("artifact_type") or item.get("evidence_type") or item.get("type"),
            rel_path,
            item.get("role"),
        )
        key = (rel_path, artifact_type)
        existing = artifacts.get(key, {})
        artifacts[key] = {
            "artifact_id": existing.get("artifact_id") or str(item.get("artifact_id") or _artifact_id(artifact_type, rel_path)),
            "artifact_type": artifact_type,
            "role": item.get("role"),
            "path": rel_path,
            "hash": existing.get("hash") or item.get("hash") or _safe_file_hash(run_dir, rel_path),
            "claimable": bool(existing.get("claimable") or item.get("claimable") or item.get("required_for_paper")),
            "required": bool(item.get("required") or item.get("required_for_paper")),
            "exists": bool(item.get("exists")) if "exists" in item else _path_exists(run_dir, rel_path),
            "source": "artifact_manifest" if not existing else "evidence_ledger+artifact_manifest",
        }
    return sorted(artifacts.values(), key=lambda item: (item.get("artifact_type") or "", item.get("path") or ""))


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_optional_provenance(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    try:
        import yaml  # type: ignore
    except Exception:
        return _load_simple_provenance(text)
    try:
        payload = yaml.safe_load(text) or {}
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_simple_provenance(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        cleaned = value.strip().strip("'\"")
        if key.strip() and cleaned:
            result[key.strip()] = cleaned
    return result


def _artifact_id(artifact_type: str, rel_path: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", rel_path.replace(".", "_")).strip("_")
    return f"{artifact_type}_{stem or 'artifact'}"


def _path_escapes_package(rel_path: str) -> bool:
    path = Path(rel_path)
    return path.is_absolute() or any(part == ".." for part in path.parts)


def _path_exists(run_dir: Path | None, rel_path: str) -> bool:
    if run_dir is None or not rel_path or _path_escapes_package(rel_path):
        return False
    return (run_dir / rel_path).exists()


def _safe_file_hash(run_dir: Path | None, rel_path: str) -> str | None:
    if run_dir is None or not rel_path or _path_escapes_package(rel_path):
        return None
    path = run_dir / rel_path
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
