from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .evidence_pack import artifact_types_from_pack, load_evidence_pack


TIERING_VERSION = "v3.1"
AUTHOR_INPUT_MARKER = "[AUTHOR_INPUT_NEEDED]"
MAGNITUDE_UNVERIFIED = "[MAGNITUDE_UNVERIFIED]"
CORE_SECTIONS = {
    "00_abstract.md",
    "01_introduction.md",
    "02_data.md",
    "03_empirical_strategy.md",
    "04_results.md",
    "05_robustness.md",
}
DID_TIER_A_ARTIFACTS = {
    "model_table",
    "event_study",
    "pretrend_test",
    "cohort_table",
    "robustness_grid",
    "placebo_tests",
    "heterogeneity",
    "summary_stats",
    "figure_manifest",
}
DID_TIER_B_ARTIFACTS = {
    "model_table",
    "event_study",
    "pretrend_test",
    "summary_stats",
    "robustness_grid",
}
PATH_LEAK_RE = re.compile(
    r"(?i)(reports/|manuscript_pack[\\/]|tables/|figures/|\.tex\b|\.csv\b|[A-Z]:\\)"
)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?")


@dataclass
class TieringResult:
    metrics: dict[str, Any]
    status: str = "passed"
    issues: list[dict[str, Any]] = field(default_factory=list)

    @property
    def draft_tier(self) -> str:
        return str(self.metrics.get("draft_tier") or "C")

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.get("tier") == "hard_block" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TIERING_VERSION,
            "status": self.status,
            "draft_tier": self.draft_tier,
            "has_hard_blocks": self.has_hard_blocks,
            "metrics": self.metrics,
            "issues": self.issues,
        }


def evaluate_pack_tier(pack_dir: str | Path) -> TieringResult:
    pack = Path(pack_dir)
    sections = _read_sections(pack / "sections")
    main_text = _read_text(pack / "main.md") or "\n\n".join(sections.values())
    evidence_pack = load_evidence_pack(pack / "evidence_pack.json")
    evidence = evidence_pack.pack if not evidence_pack.has_hard_blocks else {}
    claims = _load_json(pack / "claim_ledger.json")
    design = _load_json(pack / "design_profile.json")
    citation = _load_json(pack / "reports" / "internal" / "citation_safety_report.json")
    run_validation = _load_json(pack / "reports" / "internal" / "run_validation.json")
    coherence = _load_json(pack / "reports" / "internal" / "global_coherence.json")

    floor_sections = sorted(
        name
        for name, text in sections.items()
        if AUTHOR_INPUT_MARKER in text or MAGNITUDE_UNVERIFIED in text
    )
    floor_section_requests = {
        name: _floor_requests(sections[name])
        for name in floor_sections
    }
    missing_core_sections = sorted(CORE_SECTIONS - set(sections))
    core_placeholder_count = sum(
        _marker_count(text)
        for name, text in sections.items()
        if name in CORE_SECTIONS
    )
    artifact_types = artifact_types_from_pack(evidence)
    did_content = _did_artifact_content_checks(pack, evidence)
    did_a_incomplete = _did_incomplete_artifacts(DID_TIER_A_ARTIFACTS, did_content, tier="a")
    did_b_incomplete = _did_incomplete_artifacts(DID_TIER_B_ARTIFACTS, did_content, tier="b")
    evidence_coverage = _evidence_coverage(evidence, claims)
    citation_integrity = _citation_integrity(citation)
    verified_literature_note_count = _verified_literature_note_count(citation)
    path_leaks = _path_leaks({"main.md": main_text, **sections})
    design_gate = _design_gate_status(design, coherence)
    words_total = _word_count(main_text)
    bound_claim_count = _bound_claim_count(claims)
    claim_density = round((bound_claim_count / words_total) * 1000, 2) if words_total else 0.0
    did_a_missing = sorted(DID_TIER_A_ARTIFACTS - artifact_types)
    did_b_missing = sorted(DID_TIER_B_ARTIFACTS - artifact_types)
    provenance = {
        "data_provenance": run_validation.get("data_provenance") or "unknown",
        "public_watermark": run_validation.get("public_watermark"),
    }
    evidence_pack_status = evidence_pack.status
    evidence_pack_issues = [issue.to_dict() for issue in evidence_pack.issues]

    tier_a_reasons = []
    if evidence_pack.has_hard_blocks:
        tier_a_reasons.append("evidence_pack_invalid")
    if missing_core_sections:
        tier_a_reasons.append("core_sections_missing")
    if words_total < 6000:
        tier_a_reasons.append("words_total_below_6000")
    if core_placeholder_count:
        tier_a_reasons.append("core_placeholders_present")
    if floor_sections:
        tier_a_reasons.append("floor_sections_present")
    if evidence_coverage < 0.80:
        tier_a_reasons.append("evidence_coverage_below_0_80")
    if citation_integrity < 1.0:
        tier_a_reasons.append("citation_integrity_below_1_0")
    if verified_literature_note_count == 0:
        tier_a_reasons.append("verified_literature_notes_missing")
    if path_leaks:
        tier_a_reasons.append("public_path_leaks_present")
    if design_gate != "pass":
        tier_a_reasons.append("design_gate_not_pass")
    if did_a_missing:
        tier_a_reasons.append("did_tier_a_artifacts_missing")
    if did_a_incomplete:
        tier_a_reasons.append("did_tier_a_artifacts_incomplete")

    tier_b_reasons = []
    if evidence_pack.has_hard_blocks:
        tier_b_reasons.append("evidence_pack_invalid")
    if missing_core_sections:
        tier_b_reasons.append("core_sections_missing")
    if words_total < 2500:
        tier_b_reasons.append("words_total_below_2500")
    if core_placeholder_count:
        tier_b_reasons.append("core_placeholders_present")
    if evidence_coverage < 0.50:
        tier_b_reasons.append("evidence_coverage_below_0_50")
    if path_leaks:
        tier_b_reasons.append("public_path_leaks_present")
    if design_gate == "hard_block":
        tier_b_reasons.append("design_gate_hard_block")
    if did_b_missing:
        tier_b_reasons.append("did_tier_b_artifacts_missing")
    if did_b_incomplete:
        tier_b_reasons.append("did_tier_b_artifacts_incomplete")

    if not tier_a_reasons:
        draft_tier = "A"
    elif not tier_b_reasons:
        draft_tier = "B"
    else:
        draft_tier = "C"

    metrics = {
        "version": TIERING_VERSION,
        "draft_tier": draft_tier,
        "words_total": words_total,
        "missing_core_sections": missing_core_sections,
        "core_placeholder_count": core_placeholder_count,
        "sections_floor_count": len(floor_sections),
        "floor_sections": floor_sections,
        "floor_section_requests": floor_section_requests,
        "evidence_coverage": evidence_coverage,
        "citation_integrity": citation_integrity,
        "verified_literature_note_count": verified_literature_note_count,
        "claim_density": claim_density,
        "path_leak_count": len(path_leaks),
        "path_leaks": path_leaks,
        "design_gate": design_gate,
        "evidence_pack_status": evidence_pack_status,
        "evidence_pack_issues": evidence_pack_issues,
        "artifact_types": sorted(artifact_types),
        "did_artifact_content": did_content,
        "did_tier_a_missing_artifacts": did_a_missing,
        "did_tier_b_missing_artifacts": did_b_missing,
        "did_tier_a_incomplete_artifacts": did_a_incomplete,
        "did_tier_b_incomplete_artifacts": did_b_incomplete,
        "tier_a_blockers": tier_a_reasons,
        "tier_b_blockers": tier_b_reasons,
        "provenance": provenance,
    }
    return TieringResult(metrics=metrics)


def write_pack_metrics(pack_dir: str | Path) -> TieringResult:
    result = evaluate_pack_tier(pack_dir)
    pack = Path(pack_dir)
    internal = pack / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "metrics.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _read_sections(sections_dir: Path) -> dict[str, str]:
    if not sections_dir.exists():
        return {}
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(sections_dir.glob("*.md"))
    }


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _word_count(text: str) -> int:
    body_lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
        and not line.lstrip().startswith("|")
        and not line.lstrip().startswith("\\")
    ]
    return len(WORD_RE.findall("\n".join(body_lines)))


def _marker_count(text: str) -> int:
    return text.count(AUTHOR_INPUT_MARKER) + text.count(MAGNITUDE_UNVERIFIED)


def _floor_requests(text: str) -> list[str]:
    requests: list[str] = []
    in_missing_inputs = False
    for raw in text.splitlines():
        stripped = raw.strip()
        lowered = stripped.lower()
        if lowered in {"## missing inputs", "## missing author inputs"}:
            in_missing_inputs = True
            continue
        if stripped.startswith("## ") and lowered not in {"## missing inputs", "## missing author inputs"}:
            in_missing_inputs = False
        if AUTHOR_INPUT_MARKER in stripped or MAGNITUDE_UNVERIFIED in stripped:
            requests.append(stripped)
        elif in_missing_inputs and stripped.startswith("- "):
            requests.append(stripped[2:].strip())
    return requests or ["Section contains a floor marker but no structured missing-input line."]


def _did_incomplete_artifacts(required: set[str], checks: dict[str, Any], *, tier: str) -> list[str]:
    incomplete: list[str] = []
    for artifact_type in sorted(required):
        check = checks.get(artifact_type)
        if not check:
            continue
        if check.get(f"tier_{tier}_status", check.get("status")) != "passed":
            incomplete.append(artifact_type)
    return incomplete


def _did_artifact_content_checks(pack: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    by_type: dict[str, list[dict[str, Any]]] = {}
    for artifact in evidence.get("artifacts", []) if isinstance(evidence, dict) else []:
        if not isinstance(artifact, dict):
            continue
        artifact_type = str(artifact.get("artifact_type") or "")
        if artifact_type in DID_TIER_A_ARTIFACTS | DID_TIER_B_ARTIFACTS:
            by_type.setdefault(artifact_type, []).append(artifact)
    checks: dict[str, Any] = {}
    for artifact_type, artifacts in by_type.items():
        checks[artifact_type] = _check_did_artifact_content(pack, artifact_type, artifacts)
    return checks


def _check_did_artifact_content(pack: Path, artifact_type: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    paths = _artifact_paths(pack, artifacts)
    issues = [f"missing_file:{artifact.get('path')}" for artifact in artifacts if not _artifact_path_exists(pack, artifact)]
    if artifact_type == "model_table":
        detail = _check_model_table(paths)
    elif artifact_type == "event_study":
        detail = _check_event_study(paths)
    elif artifact_type == "pretrend_test":
        detail = _check_pretrend_test(paths)
    elif artifact_type == "cohort_table":
        detail = _check_cohort_table(paths)
    elif artifact_type == "robustness_grid":
        detail = _check_robustness_grid(paths)
    elif artifact_type == "placebo_tests":
        detail = _check_placebo_tests(paths)
    elif artifact_type == "heterogeneity":
        detail = _check_heterogeneity(paths)
    elif artifact_type == "summary_stats":
        detail = _check_summary_stats(paths)
    elif artifact_type == "figure_manifest":
        detail = _check_figure_manifest(pack, paths)
    else:
        detail = {"passed": bool(paths), "issues": []}
    issues.extend(detail.get("issues", []))
    tier_b_passed = bool(detail.get("tier_b_passed", detail.get("passed"))) and not any(
        issue for issue in issues if "_tier_b_" in issue or issue.startswith("missing_file:")
    )
    tier_a_passed = bool(detail.get("tier_a_passed", detail.get("passed"))) and not issues
    status = "passed" if tier_a_passed else "failed"
    return {
        "status": status,
        "tier_a_status": "passed" if tier_a_passed else "failed",
        "tier_b_status": "passed" if tier_b_passed else "failed",
        "paths": [str(path.relative_to(pack)) if _is_relative_to(path, pack) else str(path) for path in paths],
        "issues": issues,
        "details": {key: value for key, value in detail.items() if key not in {"passed", "issues"}},
    }


def _artifact_paths(pack: Path, artifacts: list[dict[str, Any]]) -> list[Path]:
    paths: list[Path] = []
    for artifact in artifacts:
        rel_path = str(artifact.get("path") or "")
        if not rel_path:
            continue
        rel = Path(rel_path)
        if rel.is_absolute() or any(part == ".." for part in rel.parts):
            continue
        path = pack / rel
        if path.exists() and path.is_file():
            paths.append(path)
    return paths


def _artifact_path_exists(pack: Path, artifact: dict[str, Any]) -> bool:
    rel_path = str(artifact.get("path") or "")
    if not rel_path:
        return False
    rel = Path(rel_path)
    if rel.is_absolute() or any(part == ".." for part in rel.parts):
        return False
    return (pack / rel).exists()


def _check_model_table(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    main_rows = [
        row for row in rows
        if _has_any(row, ["coef", "coefficient", "estimate", "effect"])
        and _has_any(row, ["std_error", "standard_error", "se"])
    ]
    has_n = any(_has_any(row, ["n_obs", "nobs", "n", "N"]) for row in main_rows)
    has_ci = any(_has_any(row, ["ci_low", "conf_low", "lower_ci"]) and _has_any(row, ["ci_high", "conf_high", "upper_ci"]) for row in main_rows)
    has_clusters = any(_has_any(row, ["n_clusters", "cluster_count", "clusters"]) for row in main_rows)
    issues: list[str] = []
    if not main_rows:
        issues.append("model_table_requires_estimate_and_standard_error")
    if not has_n:
        issues.append("model_table_requires_n_obs")
    if not has_ci:
        issues.append("model_table_tier_a_requires_ci")
    if not has_clusters:
        issues.append("model_table_tier_a_requires_n_clusters")
    return {
        "passed": bool(main_rows) and has_n and has_ci and has_clusters,
        "tier_b_passed": bool(main_rows) and has_n,
        "tier_a_passed": bool(main_rows) and has_n and has_ci and has_clusters,
        "issues": issues,
        "row_count": len(rows),
    }


def _check_event_study(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    usable = [
        row for row in rows
        if _has_any(row, ["event_time", "term", "relative_time"])
        and _has_any(row, ["coef", "coefficient", "estimate"])
        and _has_any(row, ["std_error", "standard_error", "se"])
    ]
    event_times = [_event_time(row) for row in usable]
    has_pre = any(value is not None and value < 0 for value in event_times)
    has_post = any(value is not None and value >= 0 for value in event_times)
    issues: list[str] = []
    if not usable:
        issues.append("event_study_requires_event_time_estimate_and_se")
    if not has_pre:
        issues.append("event_study_requires_pre_period")
    if not has_post:
        issues.append("event_study_requires_post_or_treatment_period")
    return {"passed": bool(usable) and has_pre and has_post, "issues": issues, "row_count": len(rows)}


def _check_pretrend_test(paths: list[Path]) -> dict[str, Any]:
    payloads = _read_json_objects(paths)
    rows = _read_rows([path for path in paths if path.suffix.lower() == ".csv"])
    has_stat = any(
        _has_any(payload, ["p_value", "pvalue", "lead_p_value", "min_p_value", "max_abs_t", "max_abs_estimate", "p_values", "joint_test_stat", "f_stat", "chi2"])
        for payload in payloads
    ) or any(_has_any(row, ["p_value", "pvalue", "t_stat", "estimate", "coef", "std_error", "se"]) for row in rows)
    has_pre_window = any(
        _has_any(payload, ["lead_count", "pre_period_count", "n_pre_periods"])
        for payload in payloads
    ) or any(_has_any(row, ["event_time", "relative_time", "pre_period"]) for row in rows)
    issues = [] if has_stat else ["pretrend_test_requires_structured_statistic"]
    if has_stat and not has_pre_window:
        issues.append("pretrend_test_requires_pre_period_metadata")
    return {
        "passed": has_stat and has_pre_window,
        "issues": issues,
        "json_count": len(payloads),
        "row_count": len(rows),
    }


def _check_cohort_table(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    usable = [
        row for row in rows
        if _has_any(row, ["cohort", "first_treat_year", "first_treatment_time", "adoption_time"])
        and _has_any(row, ["n_units", "unit_count", "count", "n"])
    ]
    issues = [] if usable else ["cohort_table_requires_cohort_and_unit_count"]
    return {"passed": bool(usable), "issues": issues, "row_count": len(rows)}


def _check_robustness_grid(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    families = {
        str(row.get("family") or row.get("robustness_family") or row.get("check_family") or "").strip()
        for row in rows
        if any(_present(row.get(key)) for key in ["family", "robustness_family", "check_family"])
    }
    families.discard("")
    issues: list[str] = []
    if len(families) < 2:
        issues.append("robustness_grid_tier_b_requires_at_least_2_families")
    if len(families) < 4:
        issues.append("robustness_grid_tier_a_requires_at_least_4_families")
    return {
        "passed": len(families) >= 4,
        "tier_b_passed": len(families) >= 2,
        "tier_a_passed": len(families) >= 4,
        "issues": issues,
        "family_count": len(families),
        "families": sorted(families),
    }


def _check_placebo_tests(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    usable = [
        row for row in rows
        if _has_any(row, ["placebo", "test", "check", "variant"])
        and _has_any(row, ["p_value", "pvalue", "estimate", "coef"])
        and _row_status_ok(row)
    ]
    issues = [] if usable else ["placebo_tests_requires_at_least_one_structured_test"]
    return {"passed": bool(usable), "issues": issues, "row_count": len(rows)}


def _check_heterogeneity(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    dimensions = {
        str(row.get("dimension") or row.get("heterogeneity_dimension") or row.get("group") or row.get("subgroup") or "").strip()
        for row in rows
        if any(_present(row.get(key)) for key in ["dimension", "heterogeneity_dimension", "group", "subgroup"])
        and _has_any(row, ["estimate", "coef", "coefficient"])
        and _row_status_ok(row)
    }
    dimensions.discard("")
    issues = [] if len(dimensions) >= 2 else ["heterogeneity_requires_at_least_2_dimensions"]
    return {"passed": len(dimensions) >= 2, "issues": issues, "dimension_count": len(dimensions), "dimensions": sorted(dimensions)}


def _check_summary_stats(paths: list[Path]) -> dict[str, Any]:
    rows = _read_rows(paths)
    usable = [
        row for row in rows
        if _has_any(row, ["variable", "term", "name"])
        and _has_any(row, ["mean"])
        and _has_any(row, ["sd", "std", "standard_deviation"])
        and _has_any(row, ["unit", "units"])
    ]
    issues = [] if usable else ["summary_stats_requires_variable_mean_sd_unit"]
    return {"passed": bool(usable), "issues": issues, "row_count": len(rows)}


def _check_figure_manifest(pack: Path, paths: list[Path]) -> dict[str, Any]:
    text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in paths)
    has_event_study = "event_study" in text.lower() or ("event" in text.lower() and "study" in text.lower())
    figure_refs = re.findall(r"(?im)\bpath:\s*([^\s]+)", text)
    existing_refs = [
        ref for ref in figure_refs
        if not Path(ref).is_absolute()
        and ".." not in Path(ref).parts
        and (pack / ref).exists()
    ]
    issues: list[str] = []
    if not has_event_study:
        issues.append("figure_manifest_requires_event_study_figure")
    if not figure_refs:
        issues.append("figure_manifest_requires_explicit_figure_path")
    elif not existing_refs:
        issues.append("figure_manifest_referenced_figures_missing")
    return {"passed": bool(paths) and has_event_study and bool(existing_refs), "issues": issues, "figure_refs": figure_refs}


def _read_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            try:
                with path.open("r", newline="", encoding="utf-8-sig") as handle:
                    rows.extend(dict(row) for row in csv.DictReader(handle))
            except Exception:
                continue
        elif suffix == ".json":
            payload = _load_json(path)
            if isinstance(payload.get("rows"), list):
                rows.extend(item for item in payload["rows"] if isinstance(item, dict))
            elif isinstance(payload.get("model_table"), list):
                rows.extend(item for item in payload["model_table"] if isinstance(item, dict))
            elif isinstance(payload.get("coefficients"), list):
                rows.extend(item for item in payload["coefficients"] if isinstance(item, dict))
            elif payload:
                rows.append(payload)
    return rows


def _read_json_objects(paths: list[Path]) -> list[dict[str, Any]]:
    return [_load_json(path) for path in paths if path.suffix.lower() == ".json" and _load_json(path)]


def _has_any(row: dict[str, Any], keys: list[str]) -> bool:
    lowered = {str(key).lower(): value for key, value in row.items()}
    return any(_present(lowered.get(key.lower())) for key in keys)


def _present(value: Any) -> bool:
    return value not in {None, "", "nan", "NaN", "NA", "N/A"}


def _row_status_ok(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or row.get("state") or "computed").strip().lower()
    return status in {"computed", "ok", "passed", "pass", "success", "succeeded"}


def _event_time(row: dict[str, Any]) -> int | None:
    for key in ["event_time", "relative_time"]:
        if key in row:
            try:
                return int(float(str(row[key]).strip()))
            except Exception:
                pass
    term = str(row.get("term") or "")
    match = re.search(r"(-?\d+)", term)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _evidence_coverage(evidence: dict[str, Any], claims: dict[str, Any]) -> float:
    items = {
        str(item.get("evidence_id"))
        for item in evidence.get("evidence_items", [])
        if isinstance(item, dict) and item.get("evidence_id")
    }
    if not items:
        return 0.0
    used: set[str] = set()
    for claim in claims.get("claims", []) if isinstance(claims, dict) else []:
        if not isinstance(claim, dict):
            continue
        used.update(str(ref) for ref in claim.get("evidence_refs", []) if ref)
    return round(len(items & used) / len(items), 4)


def _citation_integrity(citation: dict[str, Any]) -> float:
    missing = citation.get("missing_citekeys", []) if isinstance(citation, dict) else []
    uses = citation.get("citation_uses", []) if isinstance(citation, dict) else []
    if missing:
        return 0.0
    if not uses:
        return 1.0
    supported = [
        item
        for item in uses
        if isinstance(item, dict) and item.get("citekey") and item.get("note_id")
    ]
    return round(len(supported) / len(uses), 4)


def _verified_literature_note_count(citation: dict[str, Any]) -> int:
    notes = citation.get("external_notes_used", []) if isinstance(citation, dict) else []
    if not isinstance(notes, list):
        return 0
    return sum(1 for item in notes if item)


def _path_leaks(texts: dict[str, str]) -> list[dict[str, Any]]:
    leaks: list[dict[str, Any]] = []
    for name, text in texts.items():
        for match in PATH_LEAK_RE.finditer(text):
            leaks.append({"path": name, "token": match.group(0)})
    return leaks


def _design_gate_status(design: dict[str, Any], coherence: dict[str, Any]) -> str:
    if coherence.get("has_hard_blocks") or coherence.get("status") == "failed":
        return "hard_block"
    if design.get("hard_blocks") or design.get("status") == "failed":
        return "hard_block"
    missing = design.get("diagnostics_missing", []) if isinstance(design, dict) else []
    if missing:
        return "partial"
    return "pass" if design else "missing"


def _bound_claim_count(claims: dict[str, Any]) -> int:
    count = 0
    for claim in claims.get("claims", []) if isinstance(claims, dict) else []:
        if not isinstance(claim, dict):
            continue
        if claim.get("evidence_refs"):
            count += 1
    return count
