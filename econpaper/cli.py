from __future__ import annotations

import argparse
import json
from pathlib import Path

from .run_validation import write_run_validation


def _cmd_validate_run(args: argparse.Namespace) -> int:
    report = write_run_validation(args.run_dir, args.out)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.automatic_claims_allowed else 1


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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
