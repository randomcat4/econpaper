"""Export a skill4econ run directory into an EasyPaper artifact bundle."""
from __future__ import annotations

import csv
import json
import re
import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .artifact_manifest import BUNDLE_V2_VERSION, MANIFEST_VERSION

CLAIMABLE_AGENT_STATUS = "claimable_success"
BLOCKED_AGENT_STATUSES = {
    "blocked_missing_dependency",
    "blocked_interface_only",
    "blocked_parser_only",
    "failed",
    "skipped",
}
RESULT_EXTENSIONS = {".tex", ".csv", ".md", ".pdf", ".png", ".jpg", ".jpeg", ".svg"}
TABLE_EXTENSIONS = {".tex", ".csv", ".md"}
FIGURE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".svg"}
FATAL_RISK_LEVELS = {"fatal", "high", "blocker"}
NOT_FOR_CLAIM_DEGRADATIONS = {"not_for_claim", "not_paper_ready"}


class Skill4EconBundleError(ValueError):
    """Raised when a skill4econ run cannot be exported safely."""


@dataclass(frozen=True)
class Skill4EconExportResult:
    artifact_manifest_path: Path
    claim_gate_report_path: Path
    artifact_usage_report_path: Path
    reviewer_attack_pack_json_path: Path
    reviewer_attack_pack_md_path: Path
    handoff_path: Path
    manifest_lock_path: Path
    claimable: bool

    def to_summary(self) -> dict[str, Any]:
        return {
            "artifact_manifest_path": self.artifact_manifest_path.as_posix(),
            "claim_gate_report": self.claim_gate_report_path.as_posix(),
            "artifact_usage_report": self.artifact_usage_report_path.as_posix(),
            "reviewer_attack_pack_json": self.reviewer_attack_pack_json_path.as_posix(),
            "reviewer_attack_pack_md": self.reviewer_attack_pack_md_path.as_posix(),
            "handoff": self.handoff_path.as_posix(),
            "manifest_lock": self.manifest_lock_path.as_posix(),
            "claimable": self.claimable,
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Skill4EconBundleError(f"Invalid JSON in {path}") from exc
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _risk_items(reviewer_risk: Mapping[str, Any]) -> list[dict[str, Any]]:
    risks = reviewer_risk.get("risks") if isinstance(reviewer_risk, Mapping) else []
    return [dict(item) for item in risks if isinstance(item, Mapping)]


def _risk_blocks_claims(risks: list[dict[str, Any]]) -> bool:
    for risk in risks:
        level = str(risk.get("severity") or risk.get("level") or "").lower()
        degradation = str(risk.get("claim_degradation") or "").lower()
        if level in FATAL_RISK_LEVELS or degradation in NOT_FOR_CLAIM_DEGRADATIONS:
            return True
    return False


def _load_model_table(run_dir: Path) -> list[dict[str, str]]:
    path = run_dir / "model_table.csv"
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _candidate_artifact_records(run_dir: Path, artifact_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    records = artifact_manifest.get("artifacts") if isinstance(artifact_manifest, Mapping) else []
    if isinstance(records, list) and records:
        return [dict(item) for item in records if isinstance(item, Mapping)]
    fallback: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in RESULT_EXTENSIONS:
            continue
        rel = path.relative_to(run_dir).as_posix()
        suffix = path.suffix.lower()
        kind = "figure" if suffix in FIGURE_EXTENSIONS else "table" if suffix in TABLE_EXTENSIONS else "artifact"
        fallback.append({"path": rel, "type": kind, "role": "supporting", "required": False})
    return fallback


def _record_kind(record: Mapping[str, Any], path: Path) -> str:
    text = str(record.get("type") or record.get("kind") or "").lower()
    if text in {"figure", "table"}:
        return text
    suffix = path.suffix.lower()
    if suffix in FIGURE_EXTENSIONS:
        return "figure"
    if suffix in TABLE_EXTENSIONS:
        return "table"
    return ""


def _safe_id(prefix: str, value: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value).strip("_") or "artifact"
    if stem.startswith(prefix + ":"):
        return stem
    return f"{prefix}:{stem}"


def _copy_artifacts(
    *,
    run_dir: Path,
    out_dir: Path,
    records: list[dict[str, Any]],
    claimable: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    materials_root = out_dir / "replication" / "materials"
    items: list[dict[str, Any]] = []
    usage: list[dict[str, Any]] = []
    for record in records:
        raw_path = str(record.get("path") or "")
        if not raw_path or ".." in raw_path.replace("\\", "/").split("/"):
            continue
        source = (run_dir / raw_path).resolve()
        if not source.is_file():
            continue
        kind = _record_kind(record, source)
        if kind not in {"figure", "table"}:
            continue
        target_subdir = "figures" if kind == "figure" else "tables"
        target = materials_root / target_subdir / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        rel = target.relative_to(materials_root).as_posix()
        artifact_id = _safe_id("fig" if kind == "figure" else "tab", str(record.get("role") or source.stem))
        semantic_role = str(record.get("semantic_role") or record.get("role") or "")
        if not semantic_role or semantic_role in {"main_result", "dynamic_effect"}:
            semantic_role = "result_figure" if kind == "figure" else "result_table"
        data_hash = _sha256(source)
        code_hash = data_hash
        item = {
            "id": artifact_id,
            "path": rel,
            "section": "results",
            "caption": str(record.get("caption") or record.get("role") or source.stem).replace("_", " ").title() + ".",
            "semantic_role": semantic_role,
            "caption_mode": "locked",
            "data_hash": data_hash,
            "code_hash": code_hash,
            "claimable": bool(claimable),
        }
        if kind == "figure":
            item["target_type"] = "data_visualization"
        items.append({"kind": kind, **item})
        usage.append(
            {
                "source_path": raw_path,
                "bundle_path": rel,
                "kind": kind,
                "semantic_role": semantic_role,
                "claimable": bool(claimable),
                "sha256": data_hash,
            }
        )
    return items, usage


def _build_claim_gate_report(
    *,
    status_payload: Mapping[str, Any],
    manifest: Mapping[str, Any],
    reviewer_risk: Mapping[str, Any],
    model_table: list[dict[str, str]],
) -> dict[str, Any]:
    risks = _risk_items(reviewer_risk)
    agent_status = str(status_payload.get("agent_status") or manifest.get("agent_status") or "")
    paper_readiness = str(
        status_payload.get("paper_readiness")
        or manifest.get("paper_readiness")
        or ""
    )
    main_claim_available = bool(
        status_payload.get("main_claim_available")
        if "main_claim_available" in status_payload
        else manifest.get("main_claim_available", False)
    )
    blocks: list[str] = []
    if agent_status != CLAIMABLE_AGENT_STATUS:
        blocks.append(f"agent_status={agent_status or '<missing>'}")
    if paper_readiness and paper_readiness != "paper_ready":
        blocks.append(f"paper_readiness={paper_readiness}")
    if not main_claim_available:
        blocks.append("main_claim_available=false")
    if _risk_blocks_claims(risks):
        blocks.append("reviewer_risk_blocks_claim")
    if agent_status in BLOCKED_AGENT_STATUSES:
        blocks.append(f"blocked_status={agent_status}")
    claimable = not blocks
    return {
        "claimable": claimable,
        "agent_status": agent_status,
        "paper_readiness": paper_readiness,
        "main_claim_available": main_claim_available,
        "claim_level": status_payload.get("claim_level") or manifest.get("claim_level"),
        "blocks": blocks,
        "risks": risks,
        "model_rows": len(model_table),
        "allowed_paper_uses": ["results", "robustness"] if claimable else ["limitations", "appendix"],
        "forbidden_claims": [] if claimable else ["empirical_result", "causal_claim", "main_finding"],
    }


def _reviewer_attack_pack(claim_gate: Mapping[str, Any]) -> dict[str, Any]:
    attacks = []
    if not claim_gate.get("claimable"):
        attacks.append(
            {
                "severity": "blocker",
                "issue": "Artifact is not claimable.",
                "detail": "; ".join(str(item) for item in claim_gate.get("blocks") or []),
            }
        )
    for risk in claim_gate.get("risks") or []:
        if isinstance(risk, Mapping):
            attacks.append(
                {
                    "severity": str(risk.get("severity") or risk.get("level") or "warning"),
                    "issue": str(risk.get("code") or "reviewer_risk"),
                    "detail": str(risk.get("message") or risk.get("detail") or risk),
                }
            )
    attacks.extend(
        [
            {
                "severity": "warning",
                "issue": "No autonomous empirical estimates",
                "detail": "EasyPaper may describe only file-backed skill4econ artifacts.",
            },
            {
                "severity": "warning",
                "issue": "Finance tier-1 adapter gaps",
                "detail": "Fama-MacBeth, factor alpha, portfolio sorts, and CAR/BHAR require validated backend artifacts.",
            },
        ]
    )
    return {"attacks": attacks, "blockers": [item for item in attacks if item["severity"] == "blocker"]}


def export_skill4econ_run_bundle(
    run_dir: str | Path,
    output_dir: str | Path,
    *,
    strict: bool = False,
) -> Skill4EconExportResult:
    """Create an EasyPaper-readable bundle from a skill4econ run directory."""
    run_path = Path(run_dir).expanduser().resolve()
    out_path = Path(output_dir).expanduser().resolve()
    if not run_path.is_dir():
        raise Skill4EconBundleError(f"skill4econ run_dir does not exist: {run_path}")

    status_payload = _read_json(run_path / "status.json")
    manifest = _read_json(run_path / "manifest.json")
    artifact_manifest = _read_json(run_path / "artifact_manifest.json")
    reviewer_risk = _read_json(run_path / "reviewer_risk.json")
    model_table = _load_model_table(run_path)
    claim_gate = _build_claim_gate_report(
        status_payload=status_payload,
        manifest=manifest,
        reviewer_risk=reviewer_risk,
        model_table=model_table,
    )
    if strict and not claim_gate["claimable"]:
        raise Skill4EconBundleError(
            "skill4econ run is not paper-claimable: " + "; ".join(claim_gate["blocks"])
        )

    records = _candidate_artifact_records(run_path, artifact_manifest)
    copied, usage = _copy_artifacts(
        run_dir=run_path,
        out_dir=out_path,
        records=records,
        claimable=bool(claim_gate["claimable"]),
    )
    figures = [{k: v for k, v in item.items() if k != "kind"} for item in copied if item["kind"] == "figure"]
    tables = [{k: v for k, v in item.items() if k != "kind"} for item in copied if item["kind"] == "table"]
    artifact_payload = {
        "version": MANIFEST_VERSION,
        "source_agent": "skill4econ",
        "materials_root": "replication/materials",
        "figures": figures if claim_gate["claimable"] else [],
        "tables": tables if claim_gate["claimable"] else [],
        "skill4econ_bundle_version": BUNDLE_V2_VERSION,
        "run_status": manifest.get("status") or status_payload.get("status"),
        "claim_level": claim_gate.get("claim_level"),
        "allowed_paper_uses": claim_gate["allowed_paper_uses"],
        "forbidden_claims": claim_gate["forbidden_claims"],
    }

    artifact_manifest_path = out_path / "artifact_manifest.normalized.json"
    claim_gate_report_path = out_path / "claim_gate_report.json"
    artifact_usage_report_path = out_path / "artifact_usage_report.json"
    reviewer_attack_pack_json_path = out_path / "reviewer_attack_pack.json"
    reviewer_attack_pack_md_path = out_path / "reviewer_attack_pack.md"
    handoff_path = out_path / "HANDOFF.md"
    manifest_lock_path = out_path / "replication" / "manifest.lock.json"

    _write_json(artifact_manifest_path, artifact_payload)
    _write_json(claim_gate_report_path, claim_gate)
    _write_json(artifact_usage_report_path, {"artifacts": usage, "source_run_dir": run_path.as_posix()})
    attack_pack = _reviewer_attack_pack(claim_gate)
    _write_json(reviewer_attack_pack_json_path, attack_pack)
    reviewer_attack_pack_md_path.write_text(
        "# Reviewer Attack Pack\n\n"
        + "\n".join(f"- **{item['severity']}** {item['issue']}: {item['detail']}" for item in attack_pack["attacks"])
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        manifest_lock_path,
        {
            "source_run_dir": run_path.as_posix(),
            "manifest": manifest,
            "status": status_payload,
            "claim_gate_report": claim_gate,
            "artifact_usage": usage,
        },
    )
    handoff_path.write_text(
        "\n".join(
            [
                "# skill4econ EasyPaper Handoff",
                "",
                f"- Source run: `{run_path.as_posix()}`",
                f"- Claimable: `{bool(claim_gate['claimable'])}`",
                f"- Agent status: `{claim_gate.get('agent_status')}`",
                f"- Blocks: `{'; '.join(claim_gate.get('blocks') or []) or 'none'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return Skill4EconExportResult(
        artifact_manifest_path=artifact_manifest_path,
        claim_gate_report_path=claim_gate_report_path,
        artifact_usage_report_path=artifact_usage_report_path,
        reviewer_attack_pack_json_path=reviewer_attack_pack_json_path,
        reviewer_attack_pack_md_path=reviewer_attack_pack_md_path,
        handoff_path=handoff_path,
        manifest_lock_path=manifest_lock_path,
        claimable=bool(claim_gate["claimable"]),
    )
