from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .core import Skill4EconError, failure_manifest, make_run_context, read_spec, write_audit, write_manifest
from .contracts.agent_status import is_claimable_agent_status
from .python_wrappers import PYTHON_METHODS
from .stata_wrappers import STATA_METHODS
from .validation import write_validation_report
from .validation.report import render_validation_summary
from .workflows import WORKFLOWS


P1_ONLY = {
    "dynamic_spatial_durbin",
    "psm_did",
    "green_innovation_network_spillover",
    "sfa_external_adapter",
    "dea_external_adapter",
    "malmquist_external_adapter",
    "dowhy_adapter",
    "causalml_adapter",
    "lightgbm_finance",
    "patent_text_pipeline",
    "remote_sensing_pipeline",
}


def _state_from_args(args: argparse.Namespace) -> str:
    flags = [name for name in ("plan", "dry_run", "audit", "run") if getattr(args, name)]
    if len(flags) > 1:
        raise Skill4EconError("Choose only one of --plan, --dry-run, --audit, --run.")
    if not flags:
        return "run"
    return flags[0].replace("_", "-")


def _handler(engine: str, method: str):
    if engine == "python":
        return PYTHON_METHODS.get(method)
    if engine == "stata":
        return STATA_METHODS.get(method)
    return None


def _strict_agent_exit(manifest: dict[str, Any], strict_agent: bool) -> int:
    if not strict_agent:
        return 0
    return 0 if is_claimable_agent_status(manifest.get("agent_status")) else 1


def run(args: argparse.Namespace) -> int:
    state = _state_from_args(args)
    spec = read_spec(Path(args.spec)) if args.spec else {}
    if args.spec:
        spec["_spec_path"] = str(Path(args.spec).resolve())
    ctx = make_run_context(args.method, args.engine, spec, state, args.output)
    if args.method in P1_ONLY:
        write_audit(
            ctx,
            "interface_only",
            [
                f"{args.method} is intentionally P1/P2 interface-only tonight.",
                "If needed, ask GPT-5.5 Pro for an honest difficulty assessment before implementation.",
            ],
        )
        result = write_manifest(ctx, "interface_only")
        print(ctx.run_dir)
        return _strict_agent_exit(result, bool(getattr(args, "strict_agent", False)))
    handler = _handler(args.engine, args.method)
    if handler is None:
        raise Skill4EconError(f"Unknown method for engine={args.engine}: {args.method}")
    try:
        result = handler(ctx)
    except Exception as exc:
        result = failure_manifest(ctx, exc)
        print(json.dumps({"run_dir": str(ctx.run_dir), "manifest": result}, ensure_ascii=False))
        return 2
    print(json.dumps({"run_dir": str(ctx.run_dir), "manifest": result}, ensure_ascii=False))
    return _strict_agent_exit(result, bool(getattr(args, "strict_agent", False)))


def run_workflow(args: argparse.Namespace) -> int:
    state = _state_from_args(args)
    spec = read_spec(Path(args.spec)) if args.spec else {}
    if args.spec:
        spec["_spec_path"] = str(Path(args.spec).resolve())
    handler = WORKFLOWS.get(args.name)
    if handler is None:
        raise Skill4EconError(f"Unknown workflow: {args.name}")
    ctx = make_run_context(args.name, "workflow", spec, state, args.output)
    try:
        result = handler(ctx)
    except Exception as exc:
        result = failure_manifest(ctx, exc)
        print(json.dumps({"run_dir": str(ctx.run_dir), "manifest": result}, ensure_ascii=False))
        return 2
    print(json.dumps({"run_dir": str(ctx.run_dir), "manifest": result}, ensure_ascii=False))
    return _strict_agent_exit(result, bool(getattr(args, "strict_agent", False)))


def validate_run(args: argparse.Namespace) -> int:
    report = write_validation_report(Path(args.run_dir), strict=bool(args.strict))
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.status == "passed" else 1


def _print_validated_payload(payload: dict[str, Any], strict: bool) -> int:
    run_dir = Path(str(payload.get("run_dir") or payload.get("manifest", {}).get("run_dir") or ""))
    report = write_validation_report(run_dir, strict=strict)
    payload["validation"] = report.to_dict()
    print(json.dumps(payload, ensure_ascii=False))
    print(render_validation_summary(report), file=sys.stderr)
    return 0 if report.status == "passed" else 1


def validate_method(args: argparse.Namespace) -> int:
    state = _state_from_args(args)
    spec = read_spec(Path(args.spec)) if args.spec else {}
    if args.spec:
        spec["_spec_path"] = str(Path(args.spec).resolve())
    ctx = make_run_context(args.method, args.engine, spec, state, args.output)
    handler = _handler(args.engine, args.method)
    if handler is None:
        raise Skill4EconError(f"Unknown method for engine={args.engine}: {args.method}")
    try:
        manifest = handler(ctx)
    except Exception as exc:
        manifest = failure_manifest(ctx, exc)
    return _print_validated_payload({"run_dir": str(ctx.run_dir), "manifest": manifest}, bool(args.strict))


def validate_workflow(args: argparse.Namespace) -> int:
    state = _state_from_args(args)
    spec = read_spec(Path(args.spec)) if args.spec else {}
    if args.spec:
        spec["_spec_path"] = str(Path(args.spec).resolve())
    handler = WORKFLOWS.get(args.name)
    if handler is None:
        raise Skill4EconError(f"Unknown workflow: {args.name}")
    ctx = make_run_context(args.name, "workflow", spec, state, args.output)
    manifest = handler(ctx)
    return _print_validated_payload({"run_dir": str(ctx.run_dir), "manifest": manifest}, bool(args.strict))


def list_methods(_: argparse.Namespace) -> int:
    payload: dict[str, Any] = {
        "python": sorted(PYTHON_METHODS),
        "stata": sorted(STATA_METHODS),
        "interface_only": sorted(P1_ONLY),
        "workflows": sorted(WORKFLOWS),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def smoke(args: argparse.Namespace) -> int:
    from .devtools.smoke import run_smoke_suite

    report = run_smoke_suite(args.suite, strict=bool(args.strict), timeout=args.timeout)
    print(json.dumps({k: report[k] for k in ["status", "suite", "checks", "failed", "skipped"]}, ensure_ascii=False))
    return 0 if report.get("status") == "ok" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="skill4econ")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--spec", help="Path to JSON/YAML spec.")
    run_parser.add_argument("--engine", choices=["python", "stata"], default="python")
    run_parser.add_argument("--method", required=True)
    run_parser.add_argument("--output", help="Output base directory.")
    run_parser.add_argument("--plan", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    run_parser.add_argument("--audit", action="store_true")
    run_parser.add_argument("--run", action="store_true")
    run_parser.add_argument("--strict-agent", action="store_true")
    run_parser.set_defaults(func=run)
    workflow_parser = sub.add_parser("workflow")
    workflow_parser.add_argument("--name", required=True, choices=sorted(WORKFLOWS))
    workflow_parser.add_argument("--spec", required=True, help="Path to JSON/YAML workflow spec.")
    workflow_parser.add_argument("--output", help="Output base directory.")
    workflow_parser.add_argument("--plan", action="store_true")
    workflow_parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    workflow_parser.add_argument("--audit", action="store_true")
    workflow_parser.add_argument("--run", action="store_true")
    workflow_parser.add_argument("--strict-agent", action="store_true")
    workflow_parser.set_defaults(func=run_workflow)
    list_parser = sub.add_parser("list")
    list_parser.set_defaults(func=list_methods)
    smoke_parser = sub.add_parser("smoke")
    smoke_parser.add_argument(
        "--suite",
        choices=["all", "spatial", "did", "psm", "contracts", "backend-contract", "live-backend", "flagship-slow"],
        default="all",
    )
    smoke_parser.add_argument("--strict", action="store_true")
    smoke_parser.add_argument("--timeout", type=int, default=None)
    smoke_parser.set_defaults(func=smoke)
    validate_run_parser = sub.add_parser("validate-run")
    validate_run_parser.add_argument("--run-dir", required=True)
    validate_run_parser.add_argument("--strict", action="store_true")
    validate_run_parser.set_defaults(func=validate_run)
    validate_method_parser = sub.add_parser("validate-method")
    validate_method_parser.add_argument("--spec", help="Path to JSON/YAML spec.")
    validate_method_parser.add_argument("--engine", choices=["python", "stata"], default="python")
    validate_method_parser.add_argument("--method", required=True)
    validate_method_parser.add_argument("--output", help="Output base directory.")
    validate_method_parser.add_argument("--plan", action="store_true")
    validate_method_parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    validate_method_parser.add_argument("--audit", action="store_true")
    validate_method_parser.add_argument("--run", action="store_true")
    validate_method_parser.add_argument("--strict", action="store_true")
    validate_method_parser.set_defaults(func=validate_method)
    validate_workflow_parser = sub.add_parser("validate-workflow")
    validate_workflow_parser.add_argument("--name", required=True, choices=sorted(WORKFLOWS))
    validate_workflow_parser.add_argument("--spec", required=True, help="Path to JSON/YAML workflow spec.")
    validate_workflow_parser.add_argument("--output", help="Output base directory.")
    validate_workflow_parser.add_argument("--plan", action="store_true")
    validate_workflow_parser.add_argument("--dry-run", action="store_true", dest="dry_run")
    validate_workflow_parser.add_argument("--audit", action="store_true")
    validate_workflow_parser.add_argument("--run", action="store_true")
    validate_workflow_parser.add_argument("--strict", action="store_true")
    validate_workflow_parser.set_defaults(func=validate_workflow)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Skill4EconError as exc:
        print(f"skill4econ error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
