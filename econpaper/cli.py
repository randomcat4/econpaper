from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import write_evidence_ledger
from .intake import write_intake_profile
from .linting import run_lint
from .numeric_renderer import write_numeric_rendering
from .run_validation import write_run_validation


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
