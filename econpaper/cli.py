from __future__ import annotations

import argparse
import json
from pathlib import Path

from .auth import auth_status, login_provider, subscription_status, verify_provider, verify_subscription
from .claim_ledger import write_claim_ledger
from .coherence import write_global_coherence
from .compile_pack import compile_pack
from .design_profiler import write_design_profile
from .evidence import write_evidence_ledger
from .external_table_importer import write_external_table_import
from .incremental_rerun import write_incremental_rerun
from .intake import write_intake_profile
from .linting import run_lint
from .numeric_renderer import write_numeric_rendering
from .oneclick import run_oneclick
from .quality_suite import write_quality_suite_manifest
from .release_gate import write_release_gate
from .run_validation import write_run_validation
from .search import paper_store as paper_store_mod
from .search.boundary_probe import run_boundary_probe
from .search.deep_search import write_deep_search_pack
from .search.ingest import write_ingest_pack
from .search.open_search import write_open_search_pack
from .search.prescription import write_search_prescription
from .search.router import recommend_tier
from .search.verify import write_verification_report
from .section_writer import write_sections
from .table_generator import write_publication_table
from .venue import resolve_venue
from .write_pack import write_manuscript_pack


def _cmd_validate_run(args: argparse.Namespace) -> int:
    report = write_run_validation(args.run_dir, args.out)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.automatic_claims_allowed else 1


def _cmd_lint(args: argparse.Namespace) -> int:
    report = run_lint(
        args.draft,
        run_dir=args.run_dir,
        refs_path=args.refs,
        out_dir=args.out,
        author_overrides_path=args.author_overrides,
    )
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 1 if report.has_hard_blocks else 0


def _cmd_intake(args: argparse.Namespace) -> int:
    result = write_intake_profile(
        out_dir=args.out,
        answers_path=args.answers,
        spec_path=args.spec,
        research_context_path=args.research_context,
        literature_notes_path=args.literature_notes,
        target_venue=args.target_venue,
        preferred_contribution=args.preferred_contribution,
        project_title=args.project_title,
        field=args.field,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_evidence(args: argparse.Namespace) -> int:
    result = write_evidence_ledger(
        run_dir=args.run_dir,
        out_dir=args.out,
        intake_profile_path=args.intake_profile,
        model_table_paths=args.model_table,
        summary_stats_path=args.summary_stats,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_import_table(args: argparse.Namespace) -> int:
    result = write_external_table_import(
        args.input,
        out_dir=args.out,
        source_format=args.format,
        model_id=args.model_id,
        include_intercept=args.include_intercept,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_render_numbers(args: argparse.Namespace) -> int:
    result = write_numeric_rendering(
        args.template,
        evidence_ledger_path=args.evidence_ledger,
        slots_path=args.slots,
        out_dir=args.out,
        allow_raw_numbers=args.allow_raw_numbers,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_tables(args: argparse.Namespace) -> int:
    star_policy = args.star_policy
    if star_policy is None:
        star_policy = resolve_venue(args.venue).star_policy
    result = write_publication_table(
        evidence_ledger_path=args.evidence_ledger,
        out_dir=args.out,
        variable_labels_path=args.variable_labels,
        model_metadata_path=args.model_metadata,
        caption=args.caption,
        label=args.label,
        star_policy=star_policy,
        table_name=args.table_name,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_claims(args: argparse.Namespace) -> int:
    result = write_claim_ledger(
        evidence_ledger_path=args.evidence_ledger,
        out_dir=args.out,
        intake_profile_path=args.intake_profile,
        citation_safety_report_path=args.citation_safety_report,
        design_profile_path=args.design_profile,
        run_validation_path=args.run_validation,
        author_overrides_path=args.author_overrides,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_sections(args: argparse.Namespace) -> int:
    result = write_sections(
        claim_ledger_path=args.claim_ledger,
        intake_profile_path=args.intake_profile,
        citation_index_path=args.citation_index,
        table_path=args.table_path,
        out_dir=args.out,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_coherence(args: argparse.Namespace) -> int:
    result = write_global_coherence(
        sections_dir=args.sections_dir,
        claim_ledger_path=args.claim_ledger,
        table_paths=args.table_path,
        out_dir=args.out,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_rerun(args: argparse.Namespace) -> int:
    result = write_incremental_rerun(
        previous_pack_dir=args.previous_pack,
        updated_pack_dir=args.updated_pack,
        out_dir=args.out,
        allow_regenerate_protected=args.allow_regenerate_protected,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_release_gate(args: argparse.Namespace) -> int:
    result = write_release_gate(
        pack_dir=args.pack_dir,
        human_eval_path=args.human_eval,
        out_dir=args.out,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_design(args: argparse.Namespace) -> int:
    result = write_design_profile(
        intake_profile_path=args.intake_profile,
        evidence_ledger_path=args.evidence_ledger,
        run_validation_path=args.run_validation,
        author_amendments_path=args.author_amendments,
        out_dir=args.out,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_compile(args: argparse.Namespace) -> int:
    result = compile_pack(
        args.pack_dir,
        venue=args.venue,
        out_dir=args.out,
        latex_command=args.latex_command,
        max_attempts=args.max_attempts,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_write(args: argparse.Namespace) -> int:
    result = write_manuscript_pack(
        run_dir=args.run_dir,
        intake_profile_path=args.intake,
        refs_path=args.refs,
        venue=args.venue,
        out_dir=args.out,
        latex_command=args.latex_command,
        model_table_paths=args.model_table,
        mode=args.mode,
        human_eval_path=args.human_eval,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_quality_suite(args: argparse.Namespace) -> int:
    result = write_quality_suite_manifest(out_dir=args.out)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_oneclick(args: argparse.Namespace) -> int:
    result = run_oneclick(
        case_id=args.case,
        out_root=args.out_root,
        run_dir=args.run_dir,
        raw_data_dir=args.raw_data_dir,
        intake_profile_path=args.intake,
        answers_path=args.answers,
        spec_path=args.spec,
        refs_path=args.refs,
        venue=args.venue,
        latex_command=args.latex_command,
        model_table_paths=args.model_table,
        summary_stats_path=args.summary_stats,
        human_eval_path=args.human_eval,
        target_venue=args.target_venue,
        preferred_contribution=args.preferred_contribution,
        project_title=args.project_title,
        field=args.field,
        skip_codex_review=args.skip_codex_review,
        codex_timeout=args.codex_timeout,
        require_auth=not args.no_auth,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_prescribe(args: argparse.Namespace) -> int:
    result = write_search_prescription(
        out_dir=args.out,
        topic_spec_path=args.topic_spec,
        intake_profile_path=args.intake,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_ingest(args: argparse.Namespace) -> int:
    result = write_ingest_pack(args.input, out_dir=args.out, created_by=args.created_by)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_verify(args: argparse.Namespace) -> int:
    result = write_verification_report(
        args.refs,
        out_dir=args.out,
        offline=args.offline,
        mailto=args.mailto,
        max_calls=args.max_calls,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_open(args: argparse.Namespace) -> int:
    result = write_open_search_pack(
        out_dir=args.out,
        prescription_path=args.prescription,
        queries=args.query,
        anchor_dois=args.anchor_doi,
        offline=args.offline,
        mailto=args.mailto,
        max_calls=args.max_calls,
        max_results=args.max_results,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_deep(args: argparse.Namespace) -> int:
    result = write_deep_search_pack(
        out_dir=args.out,
        prescription_path=args.prescription,
        plan_confirmed=args.confirm_plan,
        offline=args.offline,
        mailto=args.mailto,
        max_rounds=args.max_rounds,
        max_calls=args.max_calls,
        time_budget_seconds=args.time_budget,
        extra_records_paths=args.extra_records,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_search_route(args: argparse.Namespace) -> int:
    result = recommend_tier(args.scenario)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0


def _cmd_search_boundary_probe(args: argparse.Namespace) -> int:
    result = run_boundary_probe(
        out_dir=args.out,
        local_pdf_dir=args.local_pdf_dir,
        papers_per_trial=args.papers_per_trial,
        trials=args.trials,
        codex_timeout=args.codex_timeout,
        codex_cli=args.codex_cli,
        trial_ids=args.trial_id,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_paper_store_add(args: argparse.Namespace) -> int:
    result = paper_store_mod.add_paper(
        args.store,
        citekey=args.citekey,
        title_en=args.title_en or "",
        title_zh=args.title_zh or "",
        pdf_path=args.pdf,
        paper_md_path=args.paper_md,
        source_url=args.source_url or "",
        license_note=args.license_note or "",
        converter=args.converter or "",
        converter_version=args.converter_version or "",
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_paper_store_list(args: argparse.Namespace) -> int:
    print(json.dumps(paper_store_mod.list_papers(args.store), ensure_ascii=False, indent=2))
    return 0


def _cmd_paper_store_outline(args: argparse.Namespace) -> int:
    print(json.dumps(paper_store_mod.outline(args.store, args.citekey), ensure_ascii=False, indent=2))
    return 0


def _cmd_paper_store_read(args: argparse.Namespace) -> int:
    section = paper_store_mod.read_section(args.store, args.citekey, args.section)
    if section is None:
        print(json.dumps({"error": f"section not found: {args.citekey}#{args.section}"}, ensure_ascii=False))
        return 1
    print(json.dumps(section, ensure_ascii=False, indent=2))
    return 0


def _cmd_paper_store_find(args: argparse.Namespace) -> int:
    hits = paper_store_mod.search_store(args.store, args.query, max_hits=args.max_hits)
    print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0


def _cmd_auth_login(args: argparse.Namespace) -> int:
    result = login_provider(
        args.provider,
        api_key=args.api_key,
        api_key_env=args.api_key_env,
        auth_file=args.auth_file,
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_auth_status(args: argparse.Namespace) -> int:
    result = auth_status(auth_file=args.auth_file)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_auth_verify(args: argparse.Namespace) -> int:
    result = verify_provider(args.provider, auth_file=args.auth_file, timeout=args.timeout)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_auth_subscription_status(args: argparse.Namespace) -> int:
    result = subscription_status(timeout=args.timeout)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def _cmd_auth_verify_subscription(args: argparse.Namespace) -> int:
    result = verify_subscription(args.provider, timeout=args.timeout)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 1 if result.has_hard_blocks else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="econpaper")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_run = sub.add_parser(
        "validate-run",
        help="Validate a skill4econ run directory with v3 fail-closed semantics.",
    )
    validate_run.add_argument("--run-dir", required=True, type=Path)
    validate_run.add_argument("--out", required=True, type=Path)
    validate_run.set_defaults(func=_cmd_validate_run)

    lint = sub.add_parser(
        "lint",
        help="Lint a TeX or Markdown manuscript draft against v3 evidence and citation safety gates.",
    )
    lint.add_argument("draft", type=Path)
    lint.add_argument("--run-dir", required=True, type=Path)
    lint.add_argument("--refs", required=True, type=Path)
    lint.add_argument("--out", required=True, type=Path)
    lint.add_argument("--author-overrides", type=Path)
    lint.set_defaults(func=_cmd_lint)

    intake = sub.add_parser(
        "intake",
        help="Build a v3 intake_profile.json from author-supplied interview answers.",
    )
    intake.add_argument("--answers", type=Path, help="Structured interview answers in JSON or YAML.")
    intake.add_argument("--spec", type=Path, help="Optional author spec in JSON or YAML.")
    intake.add_argument("--research-context", type=Path, help="Optional author-provided research_context.md.")
    intake.add_argument("--literature-notes", type=Path, help="Optional author-provided literature_notes.md.")
    intake.add_argument("--target-venue", help="Target venue override.")
    intake.add_argument("--preferred-contribution", help="Author's preferred one-sentence contribution.")
    intake.add_argument("--project-title", help="Working title override.")
    intake.add_argument("--field", help="Field override.")
    intake.add_argument("--out", required=True, type=Path)
    intake.set_defaults(func=_cmd_intake)

    evidence = sub.add_parser(
        "evidence",
        help="Build a v3 cell-level evidence_ledger.json from structured skill4econ model tables.",
    )
    evidence.add_argument("--run-dir", required=True, type=Path)
    evidence.add_argument("--out", required=True, type=Path)
    evidence.add_argument("--intake-profile", type=Path)
    evidence.add_argument(
        "--model-table",
        action="append",
        type=Path,
        help="Structured model_table.csv/json. May be passed multiple times; defaults to discovery in run-dir.",
    )
    evidence.add_argument("--summary-stats", type=Path)
    evidence.set_defaults(func=_cmd_evidence)

    import_table = sub.add_parser(
        "import-table",
        help="Import common Stata, R, Python/statsmodels, CSV, or LaTeX regression tables into structured model_table.csv.",
    )
    import_table.add_argument("--input", required=True, type=Path)
    import_table.add_argument("--out", required=True, type=Path)
    import_table.add_argument("--format", default="auto", choices=["auto", "stata", "r", "python", "latex", "csv"])
    import_table.add_argument("--model-id", help="Override the imported model id for single-model text outputs.")
    import_table.add_argument("--include-intercept", action="store_true", help="Keep intercept/constant rows; skipped by default.")
    import_table.set_defaults(func=_cmd_import_table)

    render_numbers = sub.add_parser(
        "render-numbers",
        help="Render manuscript numeric placeholders deterministically from an evidence ledger.",
    )
    render_numbers.add_argument("--template", required=True, type=Path)
    render_numbers.add_argument("--evidence-ledger", required=True, type=Path)
    render_numbers.add_argument("--slots", type=Path, help="JSON mapping placeholders to evidence items.")
    render_numbers.add_argument("--out", required=True, type=Path)
    render_numbers.add_argument(
        "--allow-raw-numbers",
        action="store_true",
        help="Permit raw numeric prose in the template. Intended only for migration/debugging.",
    )
    render_numbers.set_defaults(func=_cmd_render_numbers)

    tables = sub.add_parser(
        "tables",
        help="Generate publication-ready booktabs and Markdown tables from evidence ledger cells.",
    )
    tables.add_argument("--evidence-ledger", required=True, type=Path)
    tables.add_argument("--out", required=True, type=Path)
    tables.add_argument("--variable-labels", type=Path)
    tables.add_argument("--model-metadata", type=Path)
    tables.add_argument("--caption", default="Main Results")
    tables.add_argument("--label", default="tab:main_results")
    tables.add_argument("--venue", default="generic-field-journal")
    tables.add_argument("--star-policy", choices=["conventional", "none"])
    tables.add_argument("--table-name", default="table_main")
    tables.set_defaults(func=_cmd_tables)

    claims = sub.add_parser(
        "claims",
        help="Build a v3 claim_ledger.json with gates, placeholders, and author overrides.",
    )
    claims.add_argument("--evidence-ledger", required=True, type=Path)
    claims.add_argument("--out", required=True, type=Path)
    claims.add_argument("--intake-profile", type=Path)
    claims.add_argument("--citation-safety-report", type=Path)
    claims.add_argument("--design-profile", type=Path)
    claims.add_argument("--run-validation", type=Path)
    claims.add_argument("--author-overrides", type=Path)
    claims.set_defaults(func=_cmd_claims)

    sections = sub.add_parser(
        "sections",
        help="Generate deterministic v3 manuscript section skeletons from intake and claim ledger inputs.",
    )
    sections.add_argument("--claim-ledger", required=True, type=Path)
    sections.add_argument("--intake-profile", required=True, type=Path)
    sections.add_argument("--citation-index", type=Path)
    sections.add_argument("--table-path", type=Path)
    sections.add_argument("--out", required=True, type=Path)
    sections.set_defaults(func=_cmd_sections)

    coherence = sub.add_parser(
        "coherence",
        help="Run global manuscript coherence checks and build consolidated AUTHOR_REPORT.md.",
    )
    coherence.add_argument("--sections-dir", required=True, type=Path)
    coherence.add_argument("--claim-ledger", required=True, type=Path)
    coherence.add_argument("--table-path", action="append", type=Path)
    coherence.add_argument("--out", required=True, type=Path)
    coherence.set_defaults(func=_cmd_coherence)

    rerun = sub.add_parser(
        "rerun",
        help="Create an incremental rerun pack with claim-status diffs and protected-section handling.",
    )
    rerun.add_argument("--previous-pack", required=True, type=Path)
    rerun.add_argument("--updated-pack", required=True, type=Path)
    rerun.add_argument("--out", required=True, type=Path)
    rerun.add_argument("--allow-regenerate-protected", action="store_true")
    rerun.set_defaults(func=_cmd_rerun)

    release_gate = sub.add_parser(
        "release-gate",
        help="Run v3 automated and human-evaluation release gate checks.",
    )
    release_gate.add_argument("--pack-dir", required=True, type=Path)
    release_gate.add_argument("--human-eval", type=Path)
    release_gate.add_argument("--out", required=True, type=Path)
    release_gate.set_defaults(func=_cmd_release_gate)

    design = sub.add_parser(
        "design",
        help="Build a declare-and-confirm v3 design_profile.json from intake and artifacts.",
    )
    design.add_argument("--intake-profile", required=True, type=Path)
    design.add_argument("--evidence-ledger", type=Path)
    design.add_argument("--run-validation", type=Path)
    design.add_argument("--author-amendments", type=Path)
    design.add_argument("--out", required=True, type=Path)
    design.set_defaults(func=_cmd_design)

    compile_cmd = sub.add_parser(
        "compile",
        help="Assemble main.md/main.tex and run the v3 LaTeX compile loop with markdown fallback.",
    )
    compile_cmd.add_argument("pack_dir", type=Path)
    compile_cmd.add_argument("--venue", default="generic-field-journal")
    compile_cmd.add_argument("--out", type=Path)
    compile_cmd.add_argument("--latex-command", default="auto")
    compile_cmd.add_argument("--max-attempts", type=int, default=2)
    compile_cmd.set_defaults(func=_cmd_compile)

    write = sub.add_parser(
        "write",
        help="Generate a v3 manuscript pack from a skill4econ run, intake profile, bibliography, and venue.",
    )
    write.add_argument("--run-dir", required=True, type=Path)
    write.add_argument("--intake", required=True, type=Path)
    write.add_argument("--refs", required=True, type=Path)
    write.add_argument("--venue", default="generic-field-journal")
    write.add_argument("--out", required=True, type=Path)
    write.add_argument("--latex-command", default="auto")
    write.add_argument(
        "--mode",
        choices=["draft", "strict"],
        default="draft",
        help="draft emits the highest reachable tier; strict fails unless the pack reaches Tier A.",
    )
    write.add_argument(
        "--model-table",
        action="append",
        type=Path,
        help="Structured model_table.csv/json, including output from `econpaper import-table`. May be passed multiple times.",
    )
    write.add_argument("--human-eval", type=Path, help="Human-evaluation JSON required for strict release-gate checks.")
    write.set_defaults(func=_cmd_write)

    quality_suite = sub.add_parser(
        "quality-suite",
        help="Emit the v3 false-confidence and Q-series quality-suite manifest.",
    )
    quality_suite.add_argument("--out", required=True, type=Path)
    quality_suite.set_defaults(func=_cmd_quality_suite)

    oneclick = sub.add_parser(
        "oneclick",
        help="Run an auth-gated end-to-end pipeline for a registered case or custom project inputs.",
    )
    oneclick.add_argument("--case", help="Registered smoke case id, or a custom project id when custom inputs are supplied.")
    oneclick.add_argument("--out-root", type=Path, default=Path("reports") / "oneclick")
    oneclick.add_argument("--run-dir", type=Path, help="Existing skill4econ run directory.")
    oneclick.add_argument(
        "--raw-data-dir",
        type=Path,
        help="Raw-data-only directory. This is inventoried and fail-closed unless a valid run/model table is also supplied.",
    )
    oneclick.add_argument("--intake", type=Path, help="Existing econpaper intake_profile.json.")
    oneclick.add_argument("--answers", type=Path, help="Author answers JSON/YAML used to build intake_profile.json.")
    oneclick.add_argument("--spec", type=Path, help="Author project spec JSON/YAML used to build intake_profile.json.")
    oneclick.add_argument("--refs", type=Path, help="BibTeX references file.")
    oneclick.add_argument("--venue", default="generic-field-journal")
    oneclick.add_argument("--target-venue", help="Target venue override when building intake.")
    oneclick.add_argument("--preferred-contribution", help="Contribution statement override when building intake.")
    oneclick.add_argument("--project-title", help="Working title override when building intake.")
    oneclick.add_argument("--field", help="Field override when building intake.")
    oneclick.add_argument("--latex-command", default="auto")
    oneclick.add_argument(
        "--model-table",
        action="append",
        type=Path,
        help="Structured model_table.csv/json. May be passed multiple times.",
    )
    oneclick.add_argument("--summary-stats", type=Path)
    oneclick.add_argument("--human-eval", type=Path)
    oneclick.add_argument("--skip-codex-review", action="store_true")
    oneclick.add_argument("--codex-timeout", type=int, default=180)
    oneclick.add_argument("--no-auth", action="store_true", help="Developer-only escape hatch for offline tests; normal runs should not use it.")
    oneclick.set_defaults(func=_cmd_oneclick)

    search = sub.add_parser(
        "search",
        help="Three-tier literature search: L1 prescription, L2 open-API verify/retrieve, L3 deep search.",
    )
    search_sub = search.add_subparsers(dest="search_command", required=True)

    prescribe = search_sub.add_parser(
        "prescribe",
        help="L1: build a search prescription (concept blocks, bilingual terms, GS/WoS/CNKI query cards).",
    )
    prescribe.add_argument("--topic-spec", type=Path, help="Topic spec JSON/YAML with concept blocks and anchors.")
    prescribe.add_argument("--intake", type=Path, help="Existing intake_profile.json to derive concept blocks from.")
    prescribe.add_argument("--out", required=True, type=Path)
    prescribe.set_defaults(func=_cmd_search_prescribe)

    ingest = search_sub.add_parser(
        "ingest",
        help="L1 reflow: dedupe RIS/BibTeX/CSV exports into normalized refs.bib + structured-notes skeleton.",
    )
    ingest.add_argument("--input", action="append", required=True, type=Path, help="Export file; repeatable.")
    ingest.add_argument("--created-by", default="author_l1_reflow")
    ingest.add_argument("--out", required=True, type=Path)
    ingest.set_defaults(func=_cmd_search_ingest)

    verify = search_sub.add_parser(
        "verify",
        help="L2: verify each refs.bib entry exists via Crossref/OpenAlex and normalize metadata.",
    )
    verify.add_argument("--refs", required=True, type=Path)
    verify.add_argument("--out", required=True, type=Path)
    verify.add_argument("--offline", action="store_true", help="No API calls; entries become unverified_offline.")
    verify.add_argument("--mailto", help="Contact email for Crossref polite pool / OpenAlex.")
    verify.add_argument("--max-calls", type=int, default=50)
    verify.set_defaults(func=_cmd_search_verify)

    open_cmd = search_sub.add_parser(
        "open",
        help="L2: execute English query cards on OpenAlex/arXiv with snowball and fail-closed budget/source boundaries.",
    )
    open_cmd.add_argument("--prescription", type=Path, help="search_prescription.json from `search prescribe`.")
    open_cmd.add_argument("--query", action="append", help="Raw keyword query; repeatable.")
    open_cmd.add_argument("--anchor-doi", action="append", help="Anchor paper DOI for snowball; repeatable.")
    open_cmd.add_argument("--out", required=True, type=Path)
    open_cmd.add_argument("--offline", action="store_true")
    open_cmd.add_argument("--mailto")
    open_cmd.add_argument("--max-calls", type=int, default=20)
    open_cmd.add_argument("--max-results", type=int, default=100)
    open_cmd.set_defaults(func=_cmd_search_open)

    deep = search_sub.add_parser(
        "deep",
        help="L3: bilingual deep-search loop (plan-confirm, fan-out rounds, coverage audit, evidence memo).",
    )
    deep.add_argument("--prescription", required=True, type=Path)
    deep.add_argument("--out", required=True, type=Path)
    deep.add_argument("--confirm-plan", action="store_true", help="Spend budget; without this only the plan is written.")
    deep.add_argument("--offline", action="store_true")
    deep.add_argument("--mailto")
    deep.add_argument("--max-rounds", type=int, default=3)
    deep.add_argument("--max-calls", type=int, default=40)
    deep.add_argument("--time-budget", type=float, default=1800.0, help="Hard wall-clock stop in seconds.")
    deep.add_argument(
        "--extra-records",
        action="append",
        type=Path,
        help="CNKI/Wanfang export reflowed into the bilingual loop; repeatable.",
    )
    deep.set_defaults(func=_cmd_search_deep)

    route = search_sub.add_parser("route", help="Recommend a search tier for a scenario (default L1; never auto-upgrades).")
    route.add_argument("--scenario", required=True, help="Free-text scenario description.")
    route.set_defaults(func=_cmd_search_route)

    boundary_probe = search_sub.add_parser(
        "boundary-probe",
        help="Auth-gated live boundary test: external Codex child probes arXiv/local PDFs/site access and writes a capability report.",
    )
    boundary_probe.add_argument("--out", required=True, type=Path)
    boundary_probe.add_argument("--local-pdf-dir", type=Path, default=Path(r"D:\论文库中文1pdf"))
    boundary_probe.add_argument("--papers-per-trial", type=int, default=30)
    boundary_probe.add_argument("--trials", type=int, default=3)
    boundary_probe.add_argument("--codex-timeout", type=int, default=900)
    boundary_probe.add_argument("--codex-cli", type=Path, help="Explicit real Codex CLI path; normally discovered from auth status.")
    boundary_probe.add_argument("--trial-id", action="append", help="Run only this boundary trial id; repeatable.")
    boundary_probe.set_defaults(func=_cmd_search_boundary_probe)

    paper_store = sub.add_parser(
        "paper-store",
        help="Local Paper Store: land legally obtained PDFs/markdown and read them by section.",
    )
    store_sub = paper_store.add_subparsers(dest="paper_store_command", required=True)

    store_add = store_sub.add_parser("add", help="Land a paper (PDF and/or converted paper.md) under its citekey.")
    store_add.add_argument("--store", required=True, type=Path)
    store_add.add_argument("--citekey", required=True)
    store_add.add_argument("--title-en")
    store_add.add_argument("--title-zh")
    store_add.add_argument("--pdf", type=Path)
    store_add.add_argument("--paper-md", type=Path, help="LLM-readable Markdown produced by MinerU/Marker/PyMuPDF.")
    store_add.add_argument("--source-url")
    store_add.add_argument("--license-note")
    store_add.add_argument("--converter", help="Tool that produced paper.md (e.g. mineru).")
    store_add.add_argument("--converter-version")
    store_add.set_defaults(func=_cmd_paper_store_add)

    store_list = store_sub.add_parser("list", help="List stored papers with status.")
    store_list.add_argument("--store", required=True, type=Path)
    store_list.set_defaults(func=_cmd_paper_store_list)

    store_outline = store_sub.add_parser("outline", help="Show a paper's heading tree from paper.struct.json.")
    store_outline.add_argument("--store", required=True, type=Path)
    store_outline.add_argument("--citekey", required=True)
    store_outline.set_defaults(func=_cmd_paper_store_outline)

    store_read = store_sub.add_parser("read", help="Read one section by anchor (e.g. 5.2) or title substring.")
    store_read.add_argument("--store", required=True, type=Path)
    store_read.add_argument("--citekey", required=True)
    store_read.add_argument("--section", required=True)
    store_read.set_defaults(func=_cmd_paper_store_read)

    store_find = store_sub.add_parser("find", help="Keyword search across stored paper.md text layers.")
    store_find.add_argument("--store", required=True, type=Path)
    store_find.add_argument("--query", required=True)
    store_find.add_argument("--max-hits", type=int, default=20)
    store_find.set_defaults(func=_cmd_paper_store_find)

    auth = sub.add_parser(
        "auth",
        help="Manage API-key and subscription CLI authentication for live verification.",
    )
    auth_sub = auth.add_subparsers(dest="auth_command", required=True)

    auth_login = auth_sub.add_parser(
        "login",
        help="Persist a usable auth source for OpenAI or Claude.",
    )
    auth_login.add_argument("provider", choices=["openai", "claude", "anthropic"])
    auth_login.add_argument("--api-key", help="API key to store in the local auth file. The key is never printed.")
    auth_login.add_argument("--api-key-env", help="Environment variable containing the API key.")
    auth_login.add_argument("--auth-file", type=Path, help="Override the auth file path.")
    auth_login.set_defaults(func=_cmd_auth_login)

    auth_status_cmd = auth_sub.add_parser(
        "status",
        help="Show redacted OpenAI and Claude auth configuration status.",
    )
    auth_status_cmd.add_argument("--auth-file", type=Path, help="Override the auth file path.")
    auth_status_cmd.set_defaults(func=_cmd_auth_status)

    auth_verify = auth_sub.add_parser(
        "verify",
        help="Make a live provider request to verify configured authentication.",
    )
    auth_verify.add_argument("provider", choices=["openai", "claude", "anthropic"])
    auth_verify.add_argument("--auth-file", type=Path, help="Override the auth file path.")
    auth_verify.add_argument("--timeout", type=float, default=30.0)
    auth_verify.set_defaults(func=_cmd_auth_verify)

    auth_subscription_status = auth_sub.add_parser(
        "subscription-status",
        help="Show redacted Codex/ChatGPT and Claude Code subscription login status.",
    )
    auth_subscription_status.add_argument("--timeout", type=float, default=15.0)
    auth_subscription_status.set_defaults(func=_cmd_auth_subscription_status)

    auth_verify_subscription = auth_sub.add_parser(
        "verify-subscription",
        help="Verify a subscription-backed CLI login without using API keys or local fallbacks.",
    )
    auth_verify_subscription.add_argument(
        "provider",
        choices=["codex", "chatgpt", "openai-codex", "claude-code", "claude_code", "claude-subscription"],
    )
    auth_verify_subscription.add_argument("--timeout", type=float, default=15.0)
    auth_verify_subscription.set_defaults(func=_cmd_auth_verify_subscription)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
