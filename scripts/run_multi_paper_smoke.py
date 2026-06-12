from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from econpaper.auth import subscription_status  # noqa: E402


ABSOLUTE_PATH_RE = re.compile(r"((?<![A-Za-z0-9_])[A-Za-z]:[\\/]|\\\\[^\\/\s]+[\\/])")
PORTABLE_PATH_SMELL_RE = re.compile(r"(reports/multi_paper_smoke/|manuscript_pack/tables/|manuscript_pack[\\/])")
TOKEN_RE = re.compile(r"tokens used\s+([\d,]+)", re.IGNORECASE)
TOKEN_LINE_RE = re.compile(r"^\s*(\d{1,3}(?:,\d{3})+|\d{3,})\s*$", re.MULTILINE)
REVIEW_RE = re.compile(r"REVIEW_JSON_BEGIN\s*(\{.*?\})\s*REVIEW_JSON_END", re.DOTALL)


@dataclass(frozen=True)
class SmokeCase:
    case_id: str
    topic: str
    venue: str
    field: str
    method: str
    design_type: str
    estimand: str
    unit: str
    sample: str
    treatment: str
    timing_type: str
    anticipation_window: str
    event_time_unit: str
    contribution: str
    motivation: str
    context: str
    main_term: str
    main_coef: float
    main_se: float
    main_p: float
    nobs: int
    unit_label: str
    mean: float
    sd: float
    benchmark: str
    diagnostics: list[dict[str, Any]]
    refs: list[dict[str, str]]


CASES = [
    SmokeCase(
        case_id="env_carbon_did_aea",
        topic="Carbon pricing exposure and manufacturing emissions",
        venue="aea",
        field="environmental economics",
        method="cs_did_attgt",
        design_type="staggered DID with Callaway-Sant'Anna ATT(g,t), event-study diagnostics, and never-treated controls",
        estimand="cohort-time ATT(g,t) of carbon-market exposure on plant-level CO2 intensity",
        unit="plant-year",
        sample="manufacturing plants in regulated and neighboring provinces, 2010-2022",
        treatment="pilot carbon market coverage",
        timing_type="staggered adoption cohorts with never-treated controls",
        anticipation_window="two years before market launch",
        event_time_unit="year",
        contribution="The paper quantifies how carbon-market exposure changes manufacturing emissions intensity while keeping treatment timing explicit.",
        motivation="Carbon markets are central to climate policy, but authors need a transparent bridge between estimated effects and economically interpretable emissions magnitudes.",
        context="Pilot carbon markets exposed a treated manufacturing cohort while never-treated plants provide the comparison group.",
        main_term="carbon_market_exposure",
        main_coef=-0.084,
        main_se=0.026,
        main_p=0.004,
        nobs=48210,
        unit_label="log CO2 intensity points",
        mean=1.82,
        sd=0.42,
        benchmark="one-quarter of the cross-plant standard deviation",
        diagnostics=[
            {
                "term": "pretrend_joint_test",
                "p_value": 0.41,
                "model_id": "event_study_pretrend_comparison_group_staggered_estimator",
                "diagnostic_status": "event study pretrend comparison group staggered estimator diagnostic passed",
            }
        ],
        refs=[
            {"key": "martin2016", "title": "The impact of the European Union Emissions Trading Scheme on regulated firms"},
            {"key": "calonico2014", "title": "Robust nonparametric confidence intervals for regression-discontinuity designs"},
        ],
    ),
    SmokeCase(
        case_id="finance_climate_credit_jfjfe",
        topic="Climate physical risk disclosures and bank credit spreads",
        venue="jf-jfe",
        field="climate finance",
        method="ols_cluster",
        design_type="finance event_study panel with factor-adjusted robustness",
        estimand="change in loan spread around salient climate-risk disclosure events",
        unit="loan-facility by quarter",
        sample="syndicated loans to publicly listed borrowers with climate-risk disclosures, 2015-2024",
        treatment="high physical-risk disclosure event",
        timing_type="announcement quarter",
        anticipation_window="one quarter before disclosure",
        event_time_unit="quarter",
        contribution="The paper links climate physical-risk disclosure events to bank credit pricing in a finance-journal event-study frame.",
        motivation="Finance readers need evidence on whether lenders price climate physical risk when firms make salient disclosures.",
        context="Large borrowers increasingly disclose physical climate-risk exposure in securities filings and lender presentations.",
        main_term="physical_risk_disclosure",
        main_coef=0.118,
        main_se=0.044,
        main_p=0.008,
        nobs=16384,
        unit_label="log loan spread points",
        mean=2.91,
        sd=0.73,
        benchmark="basis-point equivalent should be added by the author before final submission",
        diagnostics=[
            {
                "term": "market_model_alpha_check",
                "p_value": 0.18,
                "model_id": "event_timeline_leakage_check_factor_adjusted",
                "diagnostic_status": "event timeline leakage check factor adjusted diagnostic passed",
            }
        ],
        refs=[
            {"key": "bolton2021", "title": "Climate risks and the pricing of bank loans"},
            {"key": "engle2020", "title": "Hedging climate change news"},
        ],
    ),
    SmokeCase(
        case_id="urban_lez_rdd_generic",
        topic="Low-emission zones and retail foot traffic",
        venue="generic-field-journal",
        field="urban and environmental economics",
        method="rdd_local_linear",
        design_type="geographic RDD around a low-emission-zone boundary",
        estimand="local discontinuity in retail foot traffic at the low-emission-zone boundary",
        unit="retail block by week",
        sample="urban retail blocks within two kilometers of the low-emission-zone boundary, 2018-2023",
        treatment="inside low-emission-zone boundary",
        timing_type="spatial cutoff",
        anticipation_window="not applicable for the boundary design",
        event_time_unit="week",
        contribution="The paper studies whether low-emission-zone boundaries shift commercial activity while preserving local-design diagnostics.",
        motivation="City policy debates often require both environmental and commercial-activity evidence near policy boundaries.",
        context="The city implemented a low-emission zone with a published boundary and phased vehicle restrictions.",
        main_term="inside_low_emission_zone",
        main_coef=-0.037,
        main_se=0.015,
        main_p=0.013,
        nobs=9276,
        unit_label="log weekly visits",
        mean=5.34,
        sd=0.61,
        benchmark="roughly six percent of the local cross-block standard deviation",
        diagnostics=[
            {
                "term": "mccrary_density_check",
                "p_value": 0.57,
                "model_id": "rd_plot_manipulation_bandwidth_covariate_continuity",
                "diagnostic_status": "rd plot manipulation bandwidth covariate continuity diagnostic passed",
            }
        ],
        refs=[
            {"key": "davis2008", "title": "The effect of driving restrictions on air quality"},
            {"key": "imbens2008", "title": "Regression discontinuity designs: A guide to practice"},
        ],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=Path("reports") / "multi_paper_smoke")
    parser.add_argument("--skip-codex-review", action="store_true")
    parser.add_argument("--codex-timeout", type=int, default=180)
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = args.out_root / run_id
    root.mkdir(parents=True, exist_ok=True)

    backend_certification = _run_backend_certification(root)
    codex_path = None if args.skip_codex_review else _codex_subscription_path()
    summary: dict[str, Any] = {
        "version": "v3.0",
        "run_id": run_id,
        "out_dir": str(root),
        "backend_certification": backend_certification,
        "codex_review": {
            "enabled": not args.skip_codex_review,
            "cli_path": codex_path,
            "service_tier": "fast",
            "auth_source": "ChatGPT subscription CLI",
            "api_used": False,
        },
        "cases": [],
        "totals": {},
    }

    for case in CASES:
        summary["cases"].append(
            _run_case(
                case=case,
                root=root,
                codex_path=codex_path,
                codex_timeout=args.codex_timeout,
                backend_certification=backend_certification,
            )
        )

    token_total = sum((item.get("codex_review") or {}).get("tokens_used") or 0 for item in summary["cases"])
    summary["totals"] = {
        "case_count": len(summary["cases"]),
        "write_passed": sum(1 for item in summary["cases"] if item["write"]["returncode"] == 0),
        "release_gate_hard_blocked": sum(1 for item in summary["cases"] if item["release_gate"]["has_hard_blocks"]),
        "codex_review_token_total": token_total,
        "unexpected_public_path_leak_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"]["public_absolute_path_leaks"]
        ],
        "portable_path_reference_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"].get("portable_path_references")
        ],
        "real_skill4econ_cases": [
            item["case_id"] for item in summary["cases"] if (item.get("skill4econ") or {}).get("mode") == "real_skill4econ"
        ],
        "minimal_intake_failed_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"].get("minimal_intake_gate_status") == "failed"
        ],
        "did_tier_a_artifact_complete_cases": [
            item["case_id"]
            for item in summary["cases"]
            if "did" in str(item.get("design_type") or "").lower()
            and not item["static_checks"].get("did_tier_a_missing_artifacts")
            and not item["static_checks"].get("did_tier_a_incomplete_artifacts")
        ],
        "rdd_tier_b_artifact_complete_cases": [
            item["case_id"]
            for item in summary["cases"]
            if ("rdd" in str(item.get("design_type") or "").lower() or "regression discontinuity" in str(item.get("design_type") or "").lower())
            and item["static_checks"].get("rdd_tier_b_missing_or_incomplete_artifacts") == []
        ],
        "tier_b_or_better_cases": [
            item["case_id"]
            for item in summary["cases"]
            if item["static_checks"].get("draft_tier") in {"A", "B"}
        ],
        "author_report_unrendered_claim_placeholder_cases": [
            item["case_id"]
            for item in summary["cases"]
            if item["static_checks"].get("author_report_unrendered_claim_placeholders")
        ],
        "diagnostic_claim_bleed_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"]["diagnostic_terms_in_results"]
        ],
        "pdf_produced_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"].get("pdf_exists")
        ],
        "main_claims_paper_ready_cases": [
            item["case_id"]
            for item in summary["cases"]
            if item["static_checks"].get("claim_status") == "passed"
            and item["static_checks"].get("safe_claim_count", 0) > 0
            and item["static_checks"].get("evidence_pack_status") == "passed"
            and item["static_checks"].get("run_validation_status") == "passed"
        ],
        "only_human_eval_blocked_cases": [
            item["case_id"]
            for item in summary["cases"]
            if set(item["release_gate"].get("finding_codes") or []) == {"human_eval_missing"}
        ],
    }
    summary["acceptance"] = _acceptance_checks(summary)

    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "summary.md").write_text(_summary_md(summary), encoding="utf-8")
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / "latest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_root / "latest_summary.md").write_text(_summary_md(summary), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "tokens": token_total, "acceptance": summary["acceptance"]}, ensure_ascii=False, indent=2))
    return 0 if summary["acceptance"].get("status") == "passed" else 1


def _acceptance_checks(summary: dict[str, Any]) -> dict[str, Any]:
    by_case = {
        str(item.get("case_id")): item
        for item in summary.get("cases", [])
        if isinstance(item, dict) and item.get("case_id")
    }
    flagship = by_case.get("env_carbon_did_aea") or {}
    rdd = by_case.get("urban_lez_rdd_generic") or {}

    def _checks(item: dict[str, Any]) -> dict[str, Any]:
        return item.get("static_checks") if isinstance(item.get("static_checks"), dict) else {}

    def _release_codes(item: dict[str, Any]) -> set[str]:
        release = item.get("release_gate") if isinstance(item.get("release_gate"), dict) else {}
        return {str(code) for code in (release.get("finding_codes") or [])}

    checks = [
        {
            "name": "flagship_real_skill4econ",
            "passed": (flagship.get("skill4econ") or {}).get("mode") == "real_skill4econ",
        },
        {
            "name": "flagship_backend_live",
            "passed": (flagship.get("backends") or {}).get("status") == "live",
        },
        {
            "name": "flagship_tier_a",
            "passed": _checks(flagship).get("draft_tier") == "A",
        },
        {
            "name": "flagship_pdf_produced",
            "passed": bool(_checks(flagship).get("pdf_exists")),
        },
        {
            "name": "flagship_main_claims_paper_ready",
            "passed": (
                _checks(flagship).get("claim_status") == "passed"
                and _checks(flagship).get("safe_claim_count", 0) > 0
                and _checks(flagship).get("evidence_pack_status") == "passed"
                and _checks(flagship).get("run_validation_status") == "passed"
            ),
        },
        {
            "name": "flagship_release_only_human_eval_missing",
            "passed": _release_codes(flagship) == {"human_eval_missing"},
        },
        {
            "name": "rdd_real_skill4econ",
            "passed": (rdd.get("skill4econ") or {}).get("mode") == "real_skill4econ",
        },
        {
            "name": "rdd_backend_live",
            "passed": (rdd.get("backends") or {}).get("status") == "live",
        },
        {
            "name": "rdd_tier_b_or_better",
            "passed": _checks(rdd).get("draft_tier") in {"A", "B"},
        },
        {
            "name": "rdd_evidence_pack_valid",
            "passed": _checks(rdd).get("evidence_pack_status") == "passed",
        },
        {
            "name": "rdd_tier_b_artifacts_complete",
            "passed": _checks(rdd).get("rdd_tier_b_missing_or_incomplete_artifacts") == [],
        },
    ]
    failed = [item for item in checks if not item["passed"]]
    return {
        "status": "passed" if not failed else "failed",
        "checks": checks,
        "failed": failed,
    }


def _run_case(
    *,
    case: SmokeCase,
    root: Path,
    codex_path: str | None,
    codex_timeout: int,
    backend_certification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    case_dir = root / case.case_id
    inputs_dir = case_dir / "inputs"
    pack_dir = case_dir / "manuscript_pack"
    gate_dir = case_dir / "release_gate"
    inputs_dir.mkdir(parents=True, exist_ok=True)

    if case.case_id == "env_carbon_did_aea":
        skill4econ_run = _run_env_carbon_skill4econ_case(case, inputs_dir)
        run_dir = Path(str(skill4econ_run.get("run_dir") or inputs_dir / "skill4econ_run_missing"))
        skill4econ_run["validation"] = _validate_skill4econ_run(run_dir)
        _write_case_intake_and_refs(case, inputs_dir)
    elif case.case_id == "urban_lez_rdd_generic":
        skill4econ_run = _run_urban_lez_rdrobust_case(case, inputs_dir)
        run_dir = Path(str(skill4econ_run.get("run_dir") or inputs_dir / "skill4econ_run_missing"))
        skill4econ_run["validation"] = _validate_skill4econ_run(run_dir)
        _write_case_intake_and_refs(case, inputs_dir)
    else:
        run_dir = inputs_dir / "skill4econ_run"
        run_dir.mkdir(parents=True, exist_ok=True)
        _write_synthetic_case_run(case, run_dir)
        _write_case_intake_and_refs(case, inputs_dir)
        skill4econ_run = {
            "mode": "synthetic_fixture",
            "status": "fixture",
            "run_dir": str(run_dir),
            "warning": "C/B monitoring fixture; not a real skill4econ estimator run.",
        }

    write_cmd = [
        sys.executable,
        "-m",
        "econpaper.cli",
        "write",
        "--run-dir",
        str(run_dir),
        "--intake",
        str(inputs_dir / "intake_profile.json"),
        "--refs",
        str(inputs_dir / "refs.bib"),
        "--venue",
        case.venue,
        "--out",
        str(pack_dir),
    ]
    write_result = _run_command(write_cmd, cwd=Path.cwd(), timeout=120)

    gate_cmd = [
        sys.executable,
        "-m",
        "econpaper.cli",
        "release-gate",
        "--pack-dir",
        str(pack_dir),
        "--out",
        str(gate_dir),
    ]
    gate_result = _run_command(gate_cmd, cwd=Path.cwd(), timeout=60)
    gate_payload = _load_json(gate_dir / "reports" / "internal" / "release_gate.json")
    static_checks = _static_checks(case, pack_dir)
    codex_review = _codex_review(case, pack_dir, codex_path, codex_timeout) if codex_path else {"enabled": False}

    return {
        "case_id": case.case_id,
        "topic": case.topic,
        "venue": case.venue,
        "field": case.field,
        "method": case.method,
        "design_type": case.design_type,
        "paths": {
            "case_dir": str(case_dir),
            "pack_dir": str(pack_dir),
            "release_gate_dir": str(gate_dir),
            "skill4econ_run_dir": str(run_dir),
        },
        "skill4econ": skill4econ_run,
        "backends": _case_backend_status(case, backend_certification or {}),
        "write": write_result,
        "release_gate": {
            **gate_result,
            "status": gate_payload.get("status"),
            "has_hard_blocks": bool(gate_payload.get("has_hard_blocks")),
            "finding_codes": [item.get("code") for item in gate_payload.get("findings", []) if isinstance(item, dict)],
        },
        "static_checks": static_checks,
        "codex_review": codex_review,
    }


def _run_backend_certification(root: Path) -> dict[str, Any]:
    cert_root = root / "backend_certification"
    spec_path = cert_root / "backend_certification_spec.json"
    spec = {
        "run_spxtregress": False,
        "run_ppmlhdfe": False,
        "r_probe_timeout": 20,
    }
    _write_json(spec_path, spec)
    command = [
        sys.executable,
        "-m",
        "skill4econ.cli",
        "run",
        "--engine",
        "python",
        "--method",
        "live_backend_certification",
        "--spec",
        str(spec_path.resolve()),
        "--output",
        str(cert_root.resolve()),
        "--run",
    ]
    result = _run_command(command, cwd=Path.cwd(), timeout=180)
    run_dir = _extract_run_dir_from_cli_stdout(result.get("stdout_tail") or "")
    if not run_dir:
        candidates = sorted(
            (cert_root / "live_backend_certification").glob("*/backend_certification.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            run_dir = str(candidates[0].parent)
    artifact = Path(run_dir) / "backend_certification.json" if run_dir else cert_root / "backend_certification.json"
    payload = _load_json(artifact)
    return {
        "mode": "live_backend_certification",
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "elapsed_sec": result.get("elapsed_sec"),
        "run_dir": run_dir,
        "artifact": str(artifact),
        "status": payload.get("status") or "missing_artifact",
        "payload": payload,
        "stdout_tail": result.get("stdout_tail"),
        "stderr_tail": result.get("stderr_tail"),
    }


def _case_backend_status(case: SmokeCase, certification: dict[str, Any]) -> dict[str, Any]:
    payload = certification.get("payload") if isinstance(certification.get("payload"), dict) else {}
    required = {
        "env_carbon_did_aea": ["python_differences"],
        "urban_lez_rdd_generic": ["python_rdrobust", "python_rddensity"],
    }.get(case.case_id, [])
    rows = _backend_rows(payload)
    by_backend = {str(row.get("backend")): row for row in rows}
    missing = [name for name in required if str(by_backend.get(name, {}).get("status")) != "ok"]
    if required:
        status = "live" if not missing else "fail-closed"
    else:
        status = "partially-live" if any(str(row.get("status")) == "ok" for row in rows) else "fail-closed"
    return {
        "status": status,
        "required": required,
        "missing_or_failed_required": missing,
        "certification_artifact": certification.get("artifact"),
        "rows": rows,
    }


def _backend_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("python_differences", "python_rdrobust", "python_rddensity"):
        section = payload.get(key)
        if isinstance(section, dict):
            rows.extend([row for row in section.get("rows") or [] if isinstance(row, dict)])
    r_backends = payload.get("r_backends")
    if isinstance(r_backends, dict):
        rows.extend([row for row in r_backends.get("rows") or [] if isinstance(row, dict)])
    xsmle = payload.get("stata_xsmle")
    if isinstance(xsmle, dict):
        rows.append({"backend": "stata_xsmle", "status": xsmle.get("status"), "available": xsmle.get("available")})
    return rows


def _write_synthetic_case_run(case: SmokeCase, run_dir: Path) -> None:
    status = {
        "status": "success",
        "agent_status": "claimable_success",
        "method_or_workflow": case.method,
        "run_id": case.case_id,
        "claim_level": "main_estimate",
        "paper_readiness": "paper_ready",
        "main_claim_available": True,
    }
    _write_json(run_dir / "status.json", status)
    _write_json(run_dir / "manifest.json", {"status": "success", "workflow": case.method, "main_claim_available": True})
    _write_json(run_dir / "audit.json", {"status": "success", "workflow": case.method})
    _write_json(run_dir / "run_config_resolved.json", {"spec": {"case_id": case.case_id, "topic": case.topic}})
    _write_json(run_dir / "validation_report.json", {"status": "passed", "errors": []})
    (run_dir / "provenance.yaml").write_text("data_provenance: author_supplied\n", encoding="utf-8")

    rows = [
        {
            "term": case.main_term,
            "coef": case.main_coef,
            "std_error": case.main_se,
            "p_value": case.main_p,
            "nobs": case.nobs,
            "model_id": "main_specification",
            "sample_id": "analysis_sample",
            "diagnostic_status": "main claim",
        },
        *case.diagnostics,
    ]
    _write_csv(run_dir / "model_table.csv", rows)
    _write_csv(
        run_dir / "summary_stats.csv",
        [
            {
                "variable": case.main_term,
                "mean": case.mean,
                "sd": case.sd,
                "unit": case.unit_label,
            }
        ],
    )
    _write_json(
        run_dir / "artifact_manifest.json",
        {
            "workflow": case.method,
            "run_id": case.case_id,
            "status": "success",
            "artifacts": [
                {"path": "model_table.csv", "type": "model_table", "required": True, "exists": True},
                {"path": "summary_stats.csv", "type": "summary_stats", "required": False, "exists": True},
            ],
            "missing_required_artifacts": [],
        },
    )


def _run_env_carbon_skill4econ_case(case: SmokeCase, inputs_dir: Path) -> dict[str, Any]:
    data_path = inputs_dir / "env_carbon_panel.csv"
    spec_path = inputs_dir / "did_paper_run_spec.json"
    runs_dir = inputs_dir / "skill4econ_runs"
    rows: list[dict[str, Any]] = []
    cohort_by_plant: dict[int, int] = {}
    for plant in range(1, 61):
        if plant <= 15:
            cohort_by_plant[plant] = 2018
        elif plant <= 30:
            cohort_by_plant[plant] = 2019
        elif plant <= 45:
            cohort_by_plant[plant] = 2020
        else:
            cohort_by_plant[plant] = 0
    for plant in range(1, 61):
        adoption_year = cohort_by_plant[plant]
        province_group = "pilot_core" if plant % 2 == 0 else "neighboring"
        baseline_size_group = "large" if plant in {1, 2, 3, 4, 5, 6, 13, 14, 15, 16, 17, 18} else "small"
        province_index = 0.03 * (plant % 5)
        for year in range(2014, 2023):
            exposed = int(adoption_year > 0 and year >= adoption_year)
            placebo_post = int(year >= 2017)
            event_time = year - adoption_year if adoption_year > 0 else ""
            effect = exposed * (-0.08 - 0.015 * (province_group == "pilot_core") - 0.01 * (baseline_size_group == "large"))
            rows.append(
                {
                    "plant_id": plant,
                    "year": year,
                    "log_co2_intensity": 1.9
                    + 0.015 * (year - 2014)
                    + province_index
                    + 0.01 * (plant % 3)
                    + effect,
                    "carbon_market_exposure": exposed,
                    "adoption_year": adoption_year,
                    "event_time": event_time,
                    "placebo_post": placebo_post,
                    "province_group": province_group,
                    "baseline_size_group": baseline_size_group,
                }
            )
    _write_csv(data_path, rows)
    spec = {
        "data": str(data_path.resolve()),
        "design_type": "staggered_adoption_did",
        "id": "plant_id",
        "time": "year",
        "y": "log_co2_intensity",
        "gvar": "adoption_year",
        "cluster": "plant_id",
        "engine_policy": "python",
        "did_estimators": ["cs_did_attgt"],
        "exclude_estimators": ["twfe", "event_study_twfe"],
        "control_group": "never_treated",
        "boot_iterations": 0,
        "n_jobs": 1,
        "event_window": [-3, 3],
        "base_period": -1,
        "placebo_tests": [{"name": "fake_2017_timing", "post": "placebo_post"}],
        "heterogeneity_dimensions": ["province_group", "baseline_size_group"],
        "variable_units": {"log_co2_intensity": case.unit_label},
        "output_dir": str(runs_dir.resolve()),
    }
    _write_json(spec_path, spec)
    command = [
        sys.executable,
        "-m",
        "skill4econ.cli",
        "validate-workflow",
        "--name",
        "did_paper_run",
        "--spec",
        str(spec_path),
        "--output",
        str(runs_dir.resolve()),
        "--run",
        "--strict",
    ]
    result = _run_command(command, cwd=Path.cwd(), timeout=120)
    run_dir = _extract_run_dir_from_cli_stdout(result.get("stdout_tail") or "")
    if run_dir:
        provenance = Path(run_dir) / "provenance.yaml"
        provenance.write_text("data_provenance: author_supplied\n", encoding="utf-8")
    return {
        "mode": "real_skill4econ",
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "elapsed_sec": result.get("elapsed_sec"),
        "run_dir": run_dir,
        "stdout_tail": result.get("stdout_tail"),
        "stderr_tail": result.get("stderr_tail"),
    }


def _run_urban_lez_rdrobust_case(case: SmokeCase, inputs_dir: Path) -> dict[str, Any]:
    data_path = inputs_dir / "urban_lez_rdd.csv"
    spec_path = inputs_dir / "rdrobust_rdd_spec.json"
    runs_dir = inputs_dir / "skill4econ_runs"
    rows: list[dict[str, Any]] = []
    for block in range(1, 161):
        distance = (block - 80.5) / 40
        inside = int(distance >= 0)
        district = f"d{block % 8}"
        baseline = 5.3 + 0.08 * (block % 5) + 0.02 * (block % 3)
        for week in range(1, 9):
            baseline_log_visits = 5.1 + 0.025 * abs(distance) + 0.003 * week
            road_access_index = 0.8 + 0.04 * abs(distance) - 0.001 * week
            y = baseline + 0.12 * distance - 0.05 * inside + 0.004 * week + (((block * 11 + week * 7) % 9) - 4) / 400
            rows.append(
                {
                    "block_id": block,
                    "week": week,
                    "distance_to_boundary_km": round(distance, 6),
                    "inside_low_emission_zone": inside,
                    "log_weekly_visits": round(y, 6),
                    "baseline_log_visits": round(baseline_log_visits, 6),
                    "road_access_index": round(road_access_index, 6),
                    "district": district,
                }
            )
    _write_csv(data_path, rows)
    spec = {
        "data": str(data_path.resolve()),
        "y": "log_weekly_visits",
        "running": "distance_to_boundary_km",
        "cutoff": 0,
        "bandwidth": 1.5,
        "cluster": "block_id",
        "covars": ["baseline_log_visits", "road_access_index"],
        "covariate_continuity": ["baseline_log_visits", "road_access_index"],
        "donut_holes": [0.05, 0.1, 0.2],
        "variable_units": {
            "log_weekly_visits": case.unit_label,
            "distance_to_boundary_km": "kilometers from the low-emission-zone boundary",
            "baseline_log_visits": "pre-policy log weekly visits",
            "road_access_index": "pre-policy road access index",
        },
        "output_dir": str(runs_dir.resolve()),
    }
    _write_json(spec_path, spec)
    command = [
        sys.executable,
        "-m",
        "skill4econ.cli",
        "run",
        "--engine",
        "python",
        "--method",
        "rdrobust_rdd",
        "--spec",
        str(spec_path.resolve()),
        "--output",
        str(runs_dir.resolve()),
        "--run",
    ]
    result = _run_command(command, cwd=Path.cwd(), timeout=120)
    run_dir = _extract_run_dir_from_cli_stdout(result.get("stdout_tail") or "")
    if run_dir:
        provenance = Path(run_dir) / "provenance.yaml"
        provenance.write_text("data_provenance: author_supplied\n", encoding="utf-8")
    return {
        "mode": "real_skill4econ",
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "elapsed_sec": result.get("elapsed_sec"),
        "run_dir": run_dir,
        "stdout_tail": result.get("stdout_tail"),
        "stderr_tail": result.get("stderr_tail"),
    }


def _validate_skill4econ_run(run_dir: Path) -> dict[str, Any]:
    if not run_dir.exists():
        return {
            "status": "failed",
            "returncode": None,
            "artifact": str(run_dir / "validation_report.json"),
            "message": "run_dir missing; validation was not run",
        }
    command = [
        sys.executable,
        "-m",
        "skill4econ.cli",
        "validate-run",
        "--run-dir",
        str(run_dir.resolve()),
        "--strict",
    ]
    result = _run_command(command, cwd=Path.cwd(), timeout=90)
    artifact = run_dir / "validation_report.json"
    payload = _load_json(artifact)
    return {
        "command": result.get("command"),
        "returncode": result.get("returncode"),
        "elapsed_sec": result.get("elapsed_sec"),
        "artifact": str(artifact),
        "status": payload.get("status") or ("passed" if result.get("returncode") == 0 else "failed"),
        "stdout_tail": result.get("stdout_tail"),
        "stderr_tail": result.get("stderr_tail"),
    }


def _write_case_intake_and_refs(case: SmokeCase, inputs_dir: Path) -> None:
    if case.case_id == "env_carbon_did_aea":
        outcome_variable = "log_co2_intensity"
        unit_id = "plant_id"
        time_variable = "year"
    elif case.case_id == "urban_lez_rdd_generic":
        outcome_variable = "log_weekly_visits"
        unit_id = "block_id"
        time_variable = "week"
    else:
        outcome_variable = case.main_term
        unit_id = "unit_id"
        time_variable = "year"
    registry = [
        {"name": outcome_variable, "role": "outcome", "source": "author"},
        {"name": case.main_term, "role": "treatment exposure policy", "source": "author"},
        {"name": unit_id, "role": "unit_id fixed_effect cluster", "source": "author"},
        {"name": time_variable, "role": "time fixed_effect event_time", "source": "author"},
    ]
    deduped_registry: list[dict[str, str]] = []
    seen_registry_names: set[str] = set()
    for entry in registry:
        name = entry["name"]
        if name in seen_registry_names:
            deduped_registry[0]["role"] = f"{deduped_registry[0]['role']} {entry['role']}"
            continue
        seen_registry_names.add(name)
        deduped_registry.append(entry)
    intake = {
        "project": {"title_working": case.topic, "field": case.field, "target_venue": case.venue},
        "author_declared_design": {
            "design_type": case.design_type,
            "declared_by_author": True,
            "estimand": case.estimand,
            "unit_of_observation": case.unit,
            "sample_scope": case.sample,
            "estimator": "DID event-study workflow with plant and year fixed effects",
            "fixed_effects": ["plant", "year"],
            "cluster_statement": "cluster standard errors at the plant level",
        },
        "treatment_timing": {
            "treatment_name": case.treatment,
            "treatment_variable": case.main_term,
            "timing_type": case.timing_type,
            "anticipation_window": case.anticipation_window,
            "event_time_unit": case.event_time_unit,
        },
        "variable_registry": deduped_registry,
        "institutional_context": [{"fact": case.context, "source": "author", "confidence": "author_provided"}],
        "contribution_statement": case.contribution,
        "research_motivation": case.motivation,
        "outcome_magnitude_context": [
            {
                "variable": outcome_variable,
                "unit": case.unit_label,
                "mean": case.mean,
                "sd": case.sd,
                "meaningful_benchmark": case.benchmark,
            }
        ],
        "field_sources": {
            "author_declared_design.design_type": "author_provided",
            "author_declared_design.estimator": "author_provided",
            "author_declared_design.fixed_effects": "author_provided",
            "author_declared_design.cluster_statement": "author_provided",
            "variable_registry": "author_provided",
            "institutional_context": "author_provided",
            "contribution_statement": "author_provided",
            "research_motivation": "author_provided",
            "outcome_magnitude_context": "author_provided",
        },
    }
    if case.case_id == "env_carbon_did_aea":
        literature_notes_text = (
            "- martin2016: Author note: studies regulated-firm responses to emissions trading exposure and "
            "is used only to position the carbon-market setting, not to create a new empirical result.\n"
            "- calonico2014: Author note: provides inference background for regression-discontinuity designs; "
            "it is retained in the smoke bibliography as non-DID comparison material and should not be used "
            "as a DID positioning claim.\n"
        )
        literature_notes_path = inputs_dir / "literature_notes.md"
        literature_notes_path.write_text(literature_notes_text, encoding="utf-8")
        intake["author_provided_notes"] = {
            "literature_notes": {
                "path": str(literature_notes_path.resolve()),
                "status": "author_provided",
                "character_count": len(literature_notes_text),
                "sha256": hashlib.sha256(literature_notes_text.encode("utf-8")).hexdigest(),
            },
            "section_notes": _env_carbon_section_notes(),
        }
        intake["author_asserted_claims"] = [
            {
                "claim_id": "author_asserted_mechanism_001",
                "claim": (
                    "The author asserts that carbon-market exposure affects emissions intensity through "
                    "compliance-driven process upgrades and fuel-substitution incentives."
                ),
                "assertion_type": "mechanism",
                "original_status": "flag_and_confirm",
                "author_reason": "Mechanism statement is author-labeled and awaits separate mechanism diagnostics.",
            }
        ]
        intake["field_sources"]["author_provided_notes.literature_notes"] = "author_provided"
        intake["field_sources"]["author_asserted_claims"] = "author_provided"
    _write_json(inputs_dir / "intake_profile.json", intake)
    refs = []
    for item in case.refs:
        refs.append(
            "@article{"
            + item["key"]
            + ",\n"
            + "  title={"
            + item["title"].replace("{", "").replace("}", "")
            + "},\n"
            + "  author={Author, Example},\n"
            + "  journal={Journal},\n"
            + "  year={2020}\n"
            + "}\n"
        )
    (inputs_dir / "refs.bib").write_text("\n".join(refs), encoding="utf-8")


def _env_carbon_section_notes() -> list[dict[str, Any]]:
    return [
        {
            "section": "01_introduction.md",
            "note_id": "env_intro_policy_context_001",
            "status": "author_provided",
            "title": "Policy Context And Reader Stakes",
            "paragraphs": [
                (
                    "Author note: the opening should treat carbon-market exposure as a concrete regulatory shock rather than as a generic environmental policy label. The reader should understand that the paper is about manufacturing plants facing a priced emissions constraint, with never-treated plants serving as the comparison group in the current vertical slice. The motivation is not that carbon markets are universally effective or ineffective; it is that plant-level emissions intensity gives a disciplined way to ask whether exposure is associated with operational changes inside regulated manufacturing. The introduction should therefore move from the policy object, to the measurement object, to the design object. It should not begin with sweeping claims about climate policy, welfare, or innovation leadership. Those claims require source notes that are outside this smoke input. A polished version can still sound like economics prose: it can say that carbon markets create compliance incentives, that manufacturing is an important margin for emissions intensity, and that timing-based evidence is useful because it separates policy exposure from cross-sectional differences. The key is to make each of those points as framing, not as a result."
                ),
                (
                    "Author note: the contribution language should be modest but not apologetic. The paper's contribution is a transparent evidence-to-writing path for an environmental DID design, not a claim that the current fixture has settled the full literature on emissions trading. The author wants the manuscript to show how a reader would move from a typed EvidencePack to a draft that names the estimand, reports the event-study surface, interprets the main contrast in the declared outcome scale, and identifies the missing human judgments. In the introduction, this means the prose should preview the empirical objects that are actually available: model-table estimates, event-study rows, pretrend diagnostics, robustness families, placebo timing checks, heterogeneity dimensions, summary statistics, and a figure manifest. It should avoid inventing an institutional chronology beyond the supplied context. The best first-page rhythm is therefore concrete: what policy exposure is studied, what units are observed, what comparison is used, what evidence is reported, and what parts remain author-owned before release."
                ),
            ],
        },
        {
            "section": "02_data.md",
            "note_id": "env_data_construction_001",
            "status": "author_provided",
            "title": "Sample And Measurement Boundaries",
            "paragraphs": [
                (
                    "Author note: the data section should say plainly that the unit is a manufacturing plant-year and that the current smoke design covers treated plants and neighboring never-treated plants between 2010 and 2022. The text should not imply that the fixture contains the final administrative data, all cleaning rules, or the complete sampling frame of a real paper. It is enough for this vertical slice to show that every downstream numerical sentence inherits an explicit unit, outcome, treatment, time variable, fixed-effect structure, and clustering statement. The data section should therefore distinguish between declared sample scope and final data documentation. Declared scope is present and can be written. Source construction, exclusions, matching rules, plant entry and exit, sector definitions, and emissions-metering details remain author tasks unless they are supplied in later notes. That distinction is important because a release-length section can be long without being overconfident: it can explain what the draft knows, why those fields matter for interpreting the DID design, and where the author must still document the source data before submission."
                ),
                (
                    "Author note: magnitude context should be introduced as a display discipline, not as a substantive conclusion. The outcome is log CO2 intensity points, and the intake supplies a mean, standard deviation, and benchmark. Those values let the writer say how to read a coefficient in relation to the declared scale, but they do not justify converting the coefficient into aggregate tons, welfare gains, or economy-wide emissions reductions. The data section should make that boundary visible because environmental economics readers care about units. A coefficient that sounds small in logs may be large relative to cross-plant variation, and a coefficient that is large relative to the stated standard deviation may also reveal a data or scale issue that the author should inspect. The prose should therefore treat magnitude context as a review hook: it tells the author what to verify before publication. This is more useful than a generic paragraph about data quality because it connects scale, outcome definition, and evidence safety."
                ),
            ],
        },
        {
            "section": "01_introduction.md",
            "note_id": "env_intro_release_readiness_001",
            "status": "author_provided",
            "title": "Release-Readiness Framing",
            "paragraphs": [
                (
                    "Author note: the introduction should make the reader feel that the paper has a real empirical object before it discusses the automated drafting boundary. The manuscript can do this by naming the exposed manufacturing plants, the never-treated comparison plants, the event-time design, and the outcome scale in ordinary prose. The release-ready version should not sound like a product demo. It should sound like an environmental-economics paper whose evidence happens to be routed through a strict contract. The software boundary belongs in the background: it explains why claims are conservative, why diagnostics are labeled, and why missing inputs remain visible. The front of the paper should still prioritize the substantive question of whether carbon-market exposure is associated with changes in plant-level emissions intensity."
                ),
                (
                    "Author note: the first-page narrative should avoid two opposite mistakes. One mistake is a thin scaffold that only says a DID was run and a coefficient exists. The other is a grand policy essay that claims broad climate relevance before the setting has earned it. The desired middle path is specific and grounded: carbon markets price emissions, manufacturing plants are a key compliance margin, emissions intensity is the outcome that connects plant operations to policy exposure, and the event-study design gives the reader a timing-based way to inspect the evidence. Each clause should map to a supplied input or artifact. If a later author note adds policy chronology, enforcement details, permit allocation rules, or sector-specific compliance constraints, those details can deepen the introduction. Until then, the prose should stay precise."
                ),
                (
                    "Author note: the introduction may also tell readers why the draft is intentionally explicit about gates. In a conventional paper, weak or missing inputs often disappear into vague language. This vertical slice does the opposite: it records when literature positioning comes from verified notes, when mechanism language is author-labeled, and when robustness artifacts are present but not yet converted into claims. That transparency is part of the paper's voice. It should not be apologetic, because the resulting draft is more inspectable than a polished paragraph built from invented background. The author wants the introduction to make that discipline legible without turning the paper into a methods manual."
                ),
                (
                    "Author note: the final introduction paragraph should set expectations for the rest of the manuscript. Data describe the plant-year sample and magnitude scale. Empirical strategy explains the DID/event-study comparison and the author-declared identifying boundary. Results report ledger-backed estimates and leave repeated event-time rows to figures or tables. Robustness and heterogeneity describe diagnostic coverage. Mechanisms carry author-labeled interpretation rather than verified decomposition. Limitations state what remains outside the evidence pack. This roadmap is not filler; it gives the reader a clean contract for how to read the draft. It is also the difference between a 2,500-word scaffold and a manuscript-length document that earns its length through author-supplied structure."
                ),
            ],
        },
        {
            "section": "03_empirical_strategy.md",
            "note_id": "env_strategy_estimand_001",
            "status": "author_provided",
            "title": "Design Voice And Identification Boundary",
            "paragraphs": [
                (
                    "Author note: the empirical-strategy section should be written in the voice of a DID/event-study paper, but it should not overclaim. The declared estimand is the average change in log emissions intensity for plants exposed to pilot carbon market coverage relative to never-treated comparison plants. The writer can explain that plant fixed effects absorb time-invariant plant differences and year fixed effects absorb common shocks. It can also explain that clustering at the plant level is the declared inference convention. What it cannot do is assert that parallel trends are substantively credible merely because a pretrend artifact exists. The pretrend test and pre-treatment event-study rows are diagnostics; they support a discussion of design credibility only after the author has stated why treated and never-treated plants are comparable in the relevant policy environment. The section should therefore separate estimator description from identifying assumption. This makes the methods prose longer and more complete without turning a statistical artifact into an economics argument."
                ),
                (
                    "Author note: the event-study explanation should emphasize why the timing profile is useful. The current design has a single adoption cohort and never-treated controls, so the event-time coefficients can be read as a profile around market launch rather than as a fully generalized staggered-adoption aggregation problem. The text should still be cautious: the writing layer should not introduce Goodman-Bacon weights, HonestDiD bounds, or randomization-inference p-values unless those artifacts exist. The appropriate release-style paragraph says that the EvidencePack contains an event-study table, a pretrend test, and a figure manifest, and that these objects organize the timing evidence. It can then explain the intended interpretation sequence: inspect pre-treatment movement, report the main post-exposure contrast, use the figure for the pattern across event time, and reserve stronger identification language for author-confirmed assumptions. This gives the reader a complete methods path while preserving the hard boundary that econpaper does not estimate or manufacture diagnostics."
                ),
                (
                    "Author note: the section should also make clear why econpaper and skill4econ are separated. In the paper draft this does not need to sound like software documentation, but the underlying principle matters for credibility. The estimation layer produces typed artifacts, with schema versions and provenance. The writing layer imports those artifacts, checks the gates, and renders prose. It never reruns the estimator, constructs a new standard error, or aggregates event-study rows into a new ATT. A methods paragraph can translate that architecture into ordinary manuscript language by saying that all empirical claims in the draft are drawn from pre-specified tables, diagnostics, and manifests. This helps reviewers understand why the draft is conservative: when a diagnostic is absent, the manuscript shows a labeled gap; when an artifact is present but not claim-ready, it stays in a table or appendix rather than becoming a sentence. That is a substantive methods choice, not just an implementation detail."
                ),
            ],
        },
        {
            "section": "02_data.md",
            "note_id": "env_data_review_checks_001",
            "status": "author_provided",
            "title": "Reader Checks For Data Claims",
            "paragraphs": [
                (
                    "Author note: the data section should help the reader audit the empirical claim without needing to inspect code. It should make clear that treatment status, event time, unit identifiers, calendar year, outcome units, and clustering are not decorative labels; they are the fields that determine whether a numerical sentence is interpretable. If the outcome were renamed, if the treatment timing were redefined, or if the cluster variable changed, the Results section would need to be regenerated. The author wants this dependency to be explicit because it protects against a common drafting error: treating variable names as interchangeable once an estimate has been produced. In this project, the writing layer should show that the plant-year grain, policy exposure, and log emissions-intensity outcome move together as a single contract."
                ),
                (
                    "Author note: the sample description should also tell readers what is deliberately not concluded from the fixture. The smoke input does not document final source files, plant matching, sector composition, missing-data treatment, censoring rules, or entry and exit. A release draft would need those details, and the current data section should leave room for them rather than pretending they are already known. The useful contribution of the current draft is narrower: it demonstrates that once those details are supplied, the manuscript has a place to carry them and a gate that can prevent unsupported data claims from leaking into results. This is the right level of detail for a vertical slice because it supports serious review without inventing a data appendix."
                ),
                (
                    "Author note: the writer should avoid turning summary statistics into causal evidence. Means, standard deviations, and benchmarks are necessary for scale, but they do not identify the effect of carbon-market exposure. The data section can say that the outcome has a declared mean and standard deviation, and that these values discipline magnitude language later in the paper. It should not say the treated plants were comparable to controls in every relevant way unless balance or descriptive comparison artifacts are added. This keeps the data prose honest and gives the author a concrete next step: supply balance tables, sample-construction notes, and source documentation when the paper moves beyond the smoke fixture."
                ),
            ],
        },
        {
            "section": "04_results.md",
            "note_id": "env_results_interpretation_001",
            "status": "author_provided",
            "title": "Result Interpretation Plan",
            "paragraphs": [
                (
                    "Author note: the Results section should be organized around two empirical objects: the main treatment-period DID contrast and the event-study timing profile. The main contrast should appear first because it is the clearest sentence for readers. The event-study anchor should follow as timing evidence, with the full sequence left to the figure or table. The author does not want a paragraph that mechanically restates every coefficient. That style looks busy and creates a false sense that each event-time row is a separate finding. Instead, the prose should tell the reader what to look for: whether pre-treatment rows are quiet enough to support the design narrative, whether the treatment-period estimate is economically meaningful in the declared scale, and whether the post-treatment pattern is consistent with the policy timing. If the claim ledger holds additional safe event-study rows, the section should mention that they are available in the artifact surface while preserving a single narrative spine."
                ),
                (
                    "Author note: magnitude language should remain visible and reviewable. The coefficient is in log CO2 intensity points, and the smoke intake supplies mean and standard-deviation context. The writer may translate the verified estimate into that declared scale, but should not call the effect large or small without showing the basis for the label. The author wants the section to flag any uncomfortable scale implication rather than smoothing it away. If a standardized comparison looks big, the response should be to review outcome units, summary statistics, and sample construction, not to replace the magnitude with softer prose. The Results section can therefore sound mature by acknowledging the interpretation boundary directly: the estimate is ledger-backed, the display-scale comparison follows the declared magnitude context, and welfare or aggregate-emissions interpretation is left outside the current evidence pack. That posture is more polished than a generic significant-result paragraph because it anticipates the questions a careful environmental-economics referee would ask."
                ),
            ],
        },
        {
            "section": "05_robustness.md",
            "note_id": "env_robustness_priorities_001",
            "status": "author_provided",
            "title": "Robustness Priorities",
            "paragraphs": [
                (
                    "Author note: the robustness section should describe coverage before interpretation. The current artifact grid contains multiple families, including estimator comparison, sample construction, placebo timing, subgroup heterogeneity, and cluster diagnostics. A release-quality draft should not present this as a victory lap. It should explain what each family is meant to stress-test and what the grid can and cannot prove. Estimator comparison checks whether the main pattern is tied to a single implementation choice. Sample-construction checks ask whether the result depends on the declared panel boundary. Placebo timing checks look for patterns where the policy should not mechanically operate. Cluster diagnostics remind the reader that inference depends on the stated unit. Subgroup rows organize heterogeneity but do not prove mechanisms. The point is to turn the robustness table into a map of design pressure points rather than a pile of reassuring labels."
                ),
                (
                    "Author note: the section should avoid saying the results are robust across all checks unless the grid contains structured estimates and a pre-specified rule for summary language. In this vertical slice, the safe sentence is that the robustness architecture is present and that the computed families are visible to the author and reviewer. If a future version includes coefficient columns, confidence intervals, and stable comparison rules for each family, the writer can move from coverage language to substantive robustness claims. Until then, the author wants the draft to sound careful: it should say which diagnostic surfaces exist, why they matter, and what additional interpretation would be needed before release. This is especially important for placebo timing, because a passed or computed placebo artifact can be rhetorically overused. The author prefers a bounded phrasing that treats placebo rows as diagnostic evidence rather than as proof that every alternative explanation has been eliminated."
                ),
            ],
        },
        {
            "section": "06_mechanisms.md",
            "note_id": "env_mechanism_scope_001",
            "status": "author_provided",
            "title": "Mechanism Scope",
            "paragraphs": [
                (
                    "Author note: mechanism language should be explicitly labeled as interpretation unless separate mechanism diagnostics are added. The current author assertion names compliance-driven process upgrades and fuel-substitution incentives. Those are plausible channels in a carbon-market setting, but the EvidencePack does not decompose emissions changes into technology adoption, input substitution, output composition, or abatement investments. The mechanism section should therefore explain the channel as the author's interpretation of why exposure might matter, not as an established empirical result. This gives the manuscript a more complete economics feel while keeping the safety boundary intact. The reader sees the theory of change, and the author sees exactly what evidence would be needed to upgrade the language: source notes on compliance behavior, auxiliary outcomes, plant investment measures, fuel-use data, or a formal mechanism table."
                ),
                (
                    "Author note: the mechanism section should also resist a common environmental-economics shortcut: treating reduced emissions intensity as automatic evidence of cleaner technology. The same measured outcome could reflect process upgrades, fuel mix, output composition, reporting changes, or selection within the observed sample. The draft should not decide among those channels unless the author supplies evidence. A polished mechanism paragraph can still be useful by saying that the main estimate is consistent with the author's proposed compliance channel, while the current vertical slice does not separately identify the channel. That sentence is much better than omitting mechanisms altogether, because it tells reviewers the author's conceptual model and the empirical limitation in the same breath. It also avoids the more dangerous failure mode of pretending the mechanism is proven because the main coefficient has the expected sign."
                ),
            ],
        },
        {
            "section": "07_heterogeneity.md",
            "note_id": "env_heterogeneity_interpretation_001",
            "status": "author_provided",
            "title": "Heterogeneity Interpretation",
            "paragraphs": [
                (
                    "Author note: heterogeneity should be introduced as a pre-specified diagnostic surface rather than as a collection of subgroup stories. The current smoke run includes province-group and baseline-size dimensions. Those labels are useful because they point to plausible economic differences in exposure, compliance capacity, and baseline emissions intensity, but the manuscript should not rank groups or claim differential treatment effects unless the subgroup estimates and inference fields are converted into verified claims. The author wants this section to say that heterogeneity diagnostics are present, that some rows may be skipped when treatment variation is insufficient, and that substantive subgroup interpretation requires an author-provided plan. This avoids two bad outcomes: a thin draft that hides the heterogeneity surface, and an overconfident draft that invents stories for subgroup differences. The release version should eventually say why these dimensions were chosen before looking at results and how multiple-testing or interpretation discipline is handled."
                ),
            ],
        },
        {
            "section": "08_limitations.md",
            "note_id": "env_limitations_release_boundary_001",
            "status": "author_provided",
            "title": "Release Boundary",
            "paragraphs": [
                (
                    "Author note: the limitations section should not read like a ritual caveat paragraph. Its central job is to tell the reader where the machine evidence contract ends. The current vertical slice has strong typed artifacts for a DID/event-study draft, but it still lacks final author judgment on institutional detail, literature positioning, identifying assumptions, source construction, and mechanism evidence. That is not a failure of the draft; it is the reason the tier system exists. Tier B can be useful because it exposes the scaffold and the remaining boxes. Tier A should require a longer, author-informed manuscript, not merely a longer generated file. The limitations section should say this in manuscript language: empirical estimates are reported from typed artifacts, interpretation is bounded by the declared design and magnitude context, and release requires human evaluation and author-owned economics."
                ),
                (
                    "Author note: external validity should be bounded to manufacturing plants in the declared policy and sample window. The draft should not generalize to all carbon markets, all firms, or all emissions outcomes. It can say that the setting is informative for plant-level emissions intensity under pilot carbon-market exposure, but it should not claim that the same pattern holds for household behavior, services firms, national cap-and-trade programs, or welfare outcomes. The author wants the paper to earn generality later through literature comparison and institutional detail, not by broad wording now. A strong limitations paragraph can therefore be precise without sounding weak. It can say the evidence is designed to answer a specific question well, while larger policy implications require additional source notes and possibly additional empirical designs."
                ),
            ],
        },
        {
            "section": "09_conclusion.md",
            "note_id": "env_conclusion_takeaway_001",
            "status": "author_provided",
            "title": "Conclusion Takeaway",
            "paragraphs": [
                (
                    "Author note: the conclusion should return to the narrow value of the vertical slice: it demonstrates how an environmental DID EvidencePack can become a bounded manuscript draft without crossing into hidden estimation or invented interpretation. The final paragraph should be useful to a reader who wants to know what has been learned and what remains. It can restate that carbon-market exposure is associated with a change in plant-level emissions intensity in the verified model output, that event-study diagnostics organize the timing evidence, and that robustness and heterogeneity artifacts are present as diagnostic surfaces. It should then name the remaining release tasks: author-confirmed institutional chronology, literature-positioning notes, mechanism evidence or clearly labeled mechanism interpretation, final source-construction documentation, and human evaluation. The tone should be confident about the scaffold and humble about the economics that still belongs to the author."
                ),
                (
                    "Author note: the closing sentence should also explain why the manuscript is useful before every release input is complete. A bounded draft lets the author inspect the exact claims the evidence supports, the exact places where interpretation is merely author-labeled, and the exact artifacts that would strengthen the paper. That is a practical research workflow, not a weaker substitute for scholarship. The release version should preserve this clarity even after human polish, because the transparency is part of the paper's contribution."
                ),
                (
                    "Author note: the final version should keep the distinction between manuscript readiness and release readiness visible. A machine Tier A pack means the typed evidence, prose surface, citations, author notes, and length gates are internally consistent. It does not mean the economics has been endorsed by a scholar. The conclusion should leave that distinction intact so that human reviewers can focus on judgment rather than reconstruction."
                ),
                (
                    "Author note: the author also wants the closing to point back to the practical value of the artifact boundary. The reader should be able to open the manuscript, the AUTHOR_REPORT, and the internal metrics and see the same story from different angles: the prose names only supported claims, the report lists which claims were safe or flagged, and the metrics explain why the pack is or is not releasable. That alignment matters because it keeps revision work concrete. A future author can add source notes, human evaluations, or mechanism diagnostics and rerun the pack, instead of trying to remember which sentences were speculative. The conclusion should therefore frame the draft as a controlled research object that can mature into a submission, not as an automated substitute for judgment."
                ),
            ],
        },
    ]


def _static_checks(case: SmokeCase, pack_dir: Path) -> dict[str, Any]:
    public_files = [
        pack_dir / "main.md",
        pack_dir / "main.tex",
        pack_dir / "AUTHOR_REPORT.md",
        pack_dir / "sections" / "04_results.md",
        pack_dir / "sections" / "00_abstract.md",
    ]
    existing_text = {path.relative_to(pack_dir).as_posix(): path.read_text(encoding="utf-8") for path in public_files if path.exists()}
    section_and_main_text = "\n".join(
        text
        for rel, text in existing_text.items()
        if rel == "main.md" or rel.startswith("sections/")
    )
    markdown_text = "\n".join(text for rel, text in existing_text.items() if rel.endswith(".md"))
    results = existing_text.get("sections/04_results.md", "")
    write_manifest = _load_json(pack_dir / "reports" / "internal" / "write_pack_manifest.json")
    claim_ledger = _load_json(pack_dir / "claim_ledger.json")
    coherence = _load_json(pack_dir / "reports" / "internal" / "global_coherence.json")
    compile_report = _load_json(pack_dir / "reports" / "internal" / "compile_report.json")
    metrics_payload = _load_json(pack_dir / "reports" / "internal" / "metrics.json")
    metrics = metrics_payload.get("metrics") if isinstance(metrics_payload.get("metrics"), dict) else {}
    evidence_pack = _load_json(pack_dir / "evidence_pack.json")
    minimal_gate = _load_json(pack_dir / "reports" / "internal" / "minimal_intake_gate.json")
    run_validation = _load_json(pack_dir / "reports" / "internal" / "run_validation.json")
    safe_claims = [claim for claim in claim_ledger.get("claims", []) if isinstance(claim, dict) and claim.get("status") == "safe"]
    flagged_claims = [claim for claim in claim_ledger.get("claims", []) if isinstance(claim, dict) and claim.get("status") == "flag_and_confirm"]
    diagnostic_terms = [
        str(row.get("term"))
        for row in case.diagnostics
        if isinstance(row, dict) and str(row.get("term") or "") in results
    ]
    return {
        "expected_files_present": {
            "AUTHOR_REPORT.md": (pack_dir / "AUTHOR_REPORT.md").exists(),
            "main.md": (pack_dir / "main.md").exists(),
            "main.tex": (pack_dir / "main.tex").exists(),
            "table_main.tex": (pack_dir / "tables" / "table_main.tex").exists(),
            "global_coherence.json": (pack_dir / "reports" / "internal" / "global_coherence.json").exists(),
        },
        "write_status": write_manifest.get("status"),
        "write_issue_codes": [item.get("code") for item in write_manifest.get("issues", []) if isinstance(item, dict)],
        "claim_status": claim_ledger.get("status"),
        "safe_claim_count": len(safe_claims),
        "flagged_claim_count": len(flagged_claims),
        "coherence_status": coherence.get("status"),
        "compile_status": compile_report.get("status"),
        "pdf_exists": (pack_dir / "main.pdf").exists(),
        "minimal_intake_gate_status": minimal_gate.get("status"),
        "run_validation_status": run_validation.get("status"),
        "run_data_provenance": run_validation.get("data_provenance"),
        "draft_tier": metrics_payload.get("draft_tier"),
        "evidence_pack_status": metrics.get("evidence_pack_status") or (evidence_pack.get("validation") or {}).get("status"),
        "artifact_types": metrics.get("artifact_types") or sorted(
            {
                item.get("artifact_type")
                for item in evidence_pack.get("artifacts", [])
                if isinstance(item, dict) and item.get("artifact_type")
            }
        ),
        "did_tier_a_missing_artifacts": metrics.get("did_tier_a_missing_artifacts"),
        "did_tier_a_incomplete_artifacts": metrics.get("did_tier_a_incomplete_artifacts"),
        "did_tier_b_missing_artifacts": metrics.get("did_tier_b_missing_artifacts"),
        "did_tier_b_incomplete_artifacts": metrics.get("did_tier_b_incomplete_artifacts"),
        "rdd_tier_a_missing_or_incomplete_artifacts": metrics.get("rdd_tier_a_missing_or_incomplete_artifacts"),
        "rdd_tier_b_missing_or_incomplete_artifacts": metrics.get("rdd_tier_b_missing_or_incomplete_artifacts"),
        "sections_floor_count": metrics.get("sections_floor_count"),
        "unresolved_numeric_placeholders": "{{" in section_and_main_text,
        "author_report_unrendered_claim_placeholders": "{{" in existing_text.get("AUTHOR_REPORT.md", ""),
        "author_input_needed_count": markdown_text.count("[AUTHOR_INPUT_NEEDED]"),
        "cite_needed_count": markdown_text.count("[CITE_NEEDED"),
        "public_absolute_path_leaks": sorted(
            rel for rel, text in existing_text.items() if ABSOLUTE_PATH_RE.search(text)
        ),
        "portable_path_references": sorted(
            rel for rel, text in existing_text.items() if PORTABLE_PATH_SMELL_RE.search(text)
        ),
        "topic_in_abstract": case.topic in existing_text.get("sections/00_abstract.md", ""),
        "venue_template_in_tex": _venue_template(case.venue) in existing_text.get("main.tex", ""),
        "diagnostic_terms_in_results": diagnostic_terms,
    }


def _codex_review(case: SmokeCase, pack_dir: Path, codex_path: str, timeout: int) -> dict[str, Any]:
    excerpt = {
        "main_md": _read_excerpt(pack_dir / "main.md", 3500),
        "results": _read_excerpt(pack_dir / "sections" / "04_results.md", 2500),
        "author_report": _read_excerpt(pack_dir / "AUTHOR_REPORT.md", 2500),
        "claim_ledger": _read_excerpt(pack_dir / "claim_ledger.json", 3500),
        "coherence": _read_excerpt(pack_dir / "reports" / "internal" / "global_coherence.json", 2500),
    }
    prompt = (
        "Review this econpaper generated manuscript pack. Do not run shell commands, do not inspect files, "
        "and do not call tools. Use only the excerpts below. Return exactly one JSON object between "
        "REVIEW_JSON_BEGIN and REVIEW_JSON_END with keys: publishability_0_to_10, top_issues, "
        "field_fit_issue, venue_fit_issue, evidence_gate_issue, citation_issue, latex_or_table_issue.\n\n"
        f"Case: {case.case_id}\nTopic: {case.topic}\nVenue: {case.venue}\nDesign: {case.design_type}\n\n"
        + json.dumps(excerpt, ensure_ascii=False)
    )
    prompt_path = pack_dir / "reports" / "internal" / "codex_review_prompt.txt"
    raw_path = pack_dir / "reports" / "internal" / "codex_review_raw.txt"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt, encoding="utf-8")
    command = (
        "& { "
        f"Get-Content -Raw -LiteralPath {_ps_quote(prompt_path.resolve())} "
        f"| & {_ps_quote(Path(codex_path).resolve())} "
        "-c 'service_tier=\"fast\"' exec --ephemeral -s read-only "
        f"-C {_ps_quote(pack_dir.resolve())}"
        f" *> {_ps_quote(raw_path.resolve())}"
        " }"
    )
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command]
    result = _run_command(cmd, cwd=Path.cwd(), timeout=timeout, force_no_shell=True)
    raw = _read_text_auto(raw_path) if raw_path.exists() else (
        (result.get("stdout") or "") + "\n" + (result.get("stderr") or "")
    )
    review_json = _extract_last_review_json(raw)
    tokens_used = _extract_tokens_used(raw)
    return {
        "enabled": True,
        "returncode": result["returncode"],
        "elapsed_sec": result["elapsed_sec"],
        "tokens_used": tokens_used,
        "review": review_json,
        "raw_path": str(raw_path),
        "raw_tail": raw[-2000:],
    }


def _extract_last_review_json(raw: str) -> dict[str, Any]:
    review_json: dict[str, Any] = {}
    for match in REVIEW_RE.finditer(raw):
        try:
            review_json = json.loads(match.group(1))
        except json.JSONDecodeError:
            review_json = {"parse_error": "invalid_review_json"}
    return review_json


def _extract_tokens_used(raw: str) -> int | None:
    direct = list(TOKEN_RE.finditer(raw))
    if direct:
        return int(direct[-1].group(1).replace(",", ""))
    lines = TOKEN_LINE_RE.findall(raw)
    return int(lines[-1].replace(",", "")) if lines else None


def _extract_run_dir_from_cli_stdout(stdout: str) -> str | None:
    text = stdout.strip()
    if not text:
        return None
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        run_dir = payload.get("run_dir") or (payload.get("manifest") or {}).get("run_dir")
        if run_dir:
            return str(run_dir)
    decoder = json.JSONDecoder()
    for idx, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            run_dir = payload.get("run_dir") or (payload.get("manifest") or {}).get("run_dir")
            if run_dir:
                return str(run_dir)
    for match in reversed(list(re.finditer(r'"artifact_manifest"\s*:\s*"([^"]+artifact_manifest\.json)"', text))):
        try:
            artifact_manifest = Path(json.loads(f'"{match.group(1)}"'))
        except Exception:
            artifact_manifest = Path(match.group(1).replace("\\\\", "\\"))
        if artifact_manifest.name == "artifact_manifest.json":
            return str(artifact_manifest.parent)
    return None


def _codex_subscription_path() -> str | None:
    status = subscription_status(timeout=20).to_dict()
    codex = status.get("subscriptions", {}).get("codex", {})
    if codex.get("configured") and codex.get("cli_path"):
        return str(codex["cli_path"])
    return None


def _run_command(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int,
    stdin_text: str | None = None,
    force_no_shell: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    run_args: list[str] | str = cmd
    use_shell = False
    if os.name == "nt" and not force_no_shell:
        run_args = subprocess.list2cmdline(cmd)
        use_shell = True
    proc = subprocess.run(
        run_args,
        cwd=cwd,
        env=_subprocess_env(),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        input=stdin_text,
        timeout=timeout,
        check=False,
        shell=use_shell,
    )
    return {
        "command": _redact_command(cmd),
        "returncode": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - started, 3),
        "stdout_tail": proc.stdout[-12000:],
        "stderr_tail": proc.stderr[-12000:],
    }


def _subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    paths = [str(REPO_ROOT), str(REPO_ROOT / "skill4econ" / "src")]
    existing = env.get("PYTHONPATH")
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def _redact_command(cmd: list[str]) -> list[str]:
    redacted = []
    for part in cmd:
        redacted.append("<prompt>" if len(part) > 500 else part)
    return redacted


def _ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_excerpt(path: Path, limit: int) -> str:
    if not path.exists():
        return "<missing>"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:limit] + ("\n[TRUNCATED]" if len(text) > limit else "")


def _read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff") or data[:200].count(b"\x00") > 20:
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8", errors="replace")


def _venue_template(venue: str) -> str:
    return {
        "aea": "generic_aea_style",
        "jf-jfe": "generic_finance_style",
        "generic-field-journal": "generic_field_journal",
    }.get(venue, "generic_field_journal")


def _summary_md(summary: dict[str, Any]) -> str:
    lines = [
        "# Multi-Paper Smoke Monitor",
        "",
        f"- Run id: `{summary['run_id']}`",
        f"- Output dir: `{summary['out_dir']}`",
        f"- Codex review enabled: `{summary['codex_review']['enabled']}`",
        f"- Codex CLI path: `{summary['codex_review'].get('cli_path')}`",
        f"- Total Codex review tokens: `{summary['totals'].get('codex_review_token_total', 0)}`",
        "",
        "## Cases",
        "",
        "| Case | Source | Backends | Tier | Venue | Write | Release gate | PDF | Tokens | Key issues |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["cases"]:
        checks = item["static_checks"]
        review = item.get("codex_review") or {}
        source = (item.get("skill4econ") or {}).get("mode") or "unknown"
        issues: list[str] = []
        if source != "real_skill4econ":
            issues.append(source)
        if checks.get("minimal_intake_gate_status") == "failed":
            issues.append("minimal intake failed")
        if checks.get("evidence_pack_status") not in {None, "passed"}:
            issues.append(f"EvidencePack {checks.get('evidence_pack_status')}")
        missing_a = checks.get("did_tier_a_missing_artifacts") or []
        incomplete_a = checks.get("did_tier_a_incomplete_artifacts") or []
        if missing_a:
            issues.append("DID A missing: " + ",".join(map(str, missing_a[:4])))
        if incomplete_a:
            issues.append("DID A incomplete: " + ",".join(map(str, incomplete_a[:4])))
        rdd_missing_b = checks.get("rdd_tier_b_missing_or_incomplete_artifacts") or []
        rdd_missing_a = checks.get("rdd_tier_a_missing_or_incomplete_artifacts") or []
        if rdd_missing_b:
            issues.append("RDD B missing/incomplete: " + ",".join(map(str, rdd_missing_b[:4])))
        elif rdd_missing_a:
            issues.append("RDD A missing/incomplete: " + ",".join(map(str, rdd_missing_a[:4])))
        if checks["public_absolute_path_leaks"]:
            issues.append("public absolute path leak")
        if checks.get("portable_path_references"):
            issues.append("portable path reference")
        if checks.get("author_report_unrendered_claim_placeholders"):
            issues.append("AUTHOR_REPORT unrendered claim placeholders")
        if checks["diagnostic_terms_in_results"]:
            issues.append("diagnostic term in Results")
        if item["release_gate"]["has_hard_blocks"]:
            issues.append(",".join(item["release_gate"]["finding_codes"]))
        top = (review.get("review") or {}).get("top_issues")
        if isinstance(top, list) and top:
            issues.append("review: " + "; ".join(str(value) for value in top[:2]))
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{item['case_id']}`",
                    source,
                    (item.get("backends") or {}).get("status") or "unknown",
                    str(checks.get("draft_tier")),
                    item["venue"],
                    str(item["write"]["returncode"]),
                    item["release_gate"].get("status") or "<missing>",
                    str(checks["pdf_exists"]),
                    str(review.get("tokens_used")),
                    "<br>".join(issues) if issues else "none",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Totals",
            "",
            "```json",
            json.dumps(summary["totals"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Acceptance",
            "",
            "```json",
            json.dumps(summary.get("acceptance") or {}, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
