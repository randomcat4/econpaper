from __future__ import annotations

import argparse
import json
from pathlib import Path

from .intake import write_intake_profile
from .linting import run_lint
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
