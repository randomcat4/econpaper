from __future__ import annotations

import argparse
import csv
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
        method="did_twfe_event",
        design_type="staggered DID with event-study diagnostics",
        estimand="average treatment effect of carbon-market exposure on plant-level CO2 intensity",
        unit="plant-year",
        sample="manufacturing plants in regulated and neighboring provinces, 2010-2022",
        treatment="pilot carbon market coverage",
        timing_type="staggered adoption",
        anticipation_window="two years before market launch",
        event_time_unit="year",
        contribution="The paper quantifies how carbon-market exposure changes manufacturing emissions intensity while keeping treatment timing explicit.",
        motivation="Carbon markets are central to climate policy, but authors need a transparent bridge between estimated effects and economically interpretable emissions magnitudes.",
        context="Pilot carbon markets were launched in waves across provinces, creating staggered exposure across similar manufacturing plants.",
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

    codex_path = None if args.skip_codex_review else _codex_subscription_path()
    summary: dict[str, Any] = {
        "version": "v3.0",
        "run_id": run_id,
        "out_dir": str(root),
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
        "author_report_unrendered_claim_placeholder_cases": [
            item["case_id"]
            for item in summary["cases"]
            if item["static_checks"].get("author_report_unrendered_claim_placeholders")
        ],
        "diagnostic_claim_bleed_cases": [
            item["case_id"] for item in summary["cases"] if item["static_checks"]["diagnostic_terms_in_results"]
        ],
    }

    summary_path = root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "summary.md").write_text(_summary_md(summary), encoding="utf-8")
    args.out_root.mkdir(parents=True, exist_ok=True)
    (args.out_root / "latest_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out_root / "latest_summary.md").write_text(_summary_md(summary), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "tokens": token_total}, ensure_ascii=False, indent=2))
    return 0


def _run_case(*, case: SmokeCase, root: Path, codex_path: str | None, codex_timeout: int) -> dict[str, Any]:
    case_dir = root / case.case_id
    inputs_dir = case_dir / "inputs"
    run_dir = inputs_dir / "skill4econ_run"
    pack_dir = case_dir / "manuscript_pack"
    gate_dir = case_dir / "release_gate"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_case_inputs(case, run_dir, inputs_dir)

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
        },
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


def _write_case_inputs(case: SmokeCase, run_dir: Path, inputs_dir: Path) -> None:
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

    intake = {
        "project": {"title_working": case.topic, "field": case.field, "target_venue": case.venue},
        "author_declared_design": {
            "design_type": case.design_type,
            "declared_by_author": True,
            "estimand": case.estimand,
            "unit_of_observation": case.unit,
            "sample_scope": case.sample,
        },
        "treatment_timing": {
            "treatment_name": case.treatment,
            "timing_type": case.timing_type,
            "anticipation_window": case.anticipation_window,
            "event_time_unit": case.event_time_unit,
        },
        "institutional_context": [{"fact": case.context, "source": "author", "confidence": "author_provided"}],
        "contribution_statement": case.contribution,
        "research_motivation": case.motivation,
        "outcome_magnitude_context": [
            {
                "variable": case.main_term,
                "unit": case.unit_label,
                "mean": case.mean,
                "sd": case.sd,
                "meaningful_benchmark": case.benchmark,
            }
        ],
    }
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
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-3000:],
    }


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
        "| Case | Venue | Write | Release gate | PDF | Tokens | Key issues |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in summary["cases"]:
        checks = item["static_checks"]
        review = item.get("codex_review") or {}
        issues: list[str] = []
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
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
