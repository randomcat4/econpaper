"""Auth-gated boundary probes for live literature access.

This module deliberately runs a *separate* Codex CLI child process. The current
process is only the observer: it prepares prompts, verifies subscription auth,
captures raw output, and records what the child process says it could and could
not obtain without publisher-site login state.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..auth import subscription_status
from . import SEARCH_TIERS_VERSION

DEFAULT_LOCAL_PDF_DIR = Path(r"D:\论文库中文1pdf")
DEFAULT_TRIALS = 3
DEFAULT_PAPERS_PER_TRIAL = 30
DEFAULT_TIMEOUT_SECONDS = 900

BOUNDARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "trial_id",
        "conditions",
        "selected_papers",
        "attempts",
        "aggregate",
        "capability_boundaries",
        "recommendations",
    ],
    "properties": {
        "trial_id": {"type": "string"},
        "conditions": {"type": "array", "items": {"type": "string"}},
        "selected_papers": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["slot", "source_type", "title", "identifier", "language", "local_path", "url", "reason_selected"],
                "properties": {
                    "slot": {"type": "integer"},
                    "source_type": {"type": "string"},
                    "title": {"type": "string"},
                    "identifier": {"type": "string"},
                    "language": {"type": "string"},
                    "local_path": {"type": "string"},
                    "url": {"type": "string"},
                    "reason_selected": {"type": "string"},
                },
            },
        },
        "attempts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "paper_slot",
                    "action",
                    "method",
                    "target",
                    "outcome",
                    "evidence",
                    "http_status",
                    "content_type",
                    "bytes_read",
                    "artifact_created",
                    "boundary",
                ],
                "properties": {
                    "paper_slot": {"type": "integer"},
                    "action": {"type": "string"},
                    "method": {"type": "string"},
                    "target": {"type": "string"},
                    "outcome": {"type": "string"},
                    "evidence": {"type": "string"},
                    "http_status": {"type": ["integer", "null"]},
                    "content_type": {"type": "string"},
                    "bytes_read": {"type": ["integer", "null"]},
                    "artifact_created": {"type": "boolean"},
                    "boundary": {"type": "string"},
                },
            },
        },
        "aggregate": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "papers_selected",
                "arxiv_count",
                "local_pdf_count",
                "metadata_obtained_count",
                "pdf_obtained_count",
                "text_extracted_count",
                "login_required_count",
                "paywall_count",
                "captcha_count",
                "no_login_boundary_summary",
            ],
            "properties": {
                "papers_selected": {"type": "integer"},
                "arxiv_count": {"type": "integer"},
                "local_pdf_count": {"type": "integer"},
                "metadata_obtained_count": {"type": "integer"},
                "pdf_obtained_count": {"type": "integer"},
                "text_extracted_count": {"type": "integer"},
                "login_required_count": {"type": "integer"},
                "paywall_count": {"type": "integer"},
                "captcha_count": {"type": "integer"},
                "no_login_boundary_summary": {"type": "string"},
            },
        },
        "capability_boundaries": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
}


@dataclass
class BoundaryProbeIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "path": self.path}


@dataclass
class BoundaryProbeResult:
    out_dir: str
    trials: list[dict[str, Any]] = field(default_factory=list)
    status: str = "passed"
    codex_cli: str | None = None
    issues: list[BoundaryProbeIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(BoundaryProbeIssue(code, severity, message, path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "out_dir": self.out_dir,
            "codex_cli": self.codex_cli,
            "trial_count": len(self.trials),
            "trials": self.trials,
            "issues": [issue.to_dict() for issue in self.issues],
        }


CommandRunner = Callable[[list[str], Path, int], subprocess.CompletedProcess[str]]
SubscriptionChecker = Callable[[], dict[str, Any]]


def run_boundary_probe(
    *,
    out_dir: str | Path,
    local_pdf_dir: str | Path = DEFAULT_LOCAL_PDF_DIR,
    papers_per_trial: int = DEFAULT_PAPERS_PER_TRIAL,
    trials: int = DEFAULT_TRIALS,
    codex_timeout: int = DEFAULT_TIMEOUT_SECONDS,
    codex_cli: str | Path | None = None,
    trial_ids: list[str] | None = None,
    command_runner: CommandRunner | None = None,
    subscription_checker: SubscriptionChecker | None = None,
) -> BoundaryProbeResult:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    result = BoundaryProbeResult(out_dir=str(out_path))
    if papers_per_trial < 1:
        result.add_issue("invalid_sample_size", "hard_block", "--papers-per-trial must be >= 1.")
        _write_outputs(out_path, result)
        return result
    if trials < 1:
        result.add_issue("invalid_trial_count", "hard_block", "--trials must be >= 1.")
        _write_outputs(out_path, result)
        return result

    auth_payload = (subscription_checker or _subscription_payload)()
    codex_path = str(codex_cli) if codex_cli else _codex_cli_from_auth(auth_payload)
    if not codex_path:
        result.add_issue(
            "subscription_auth_missing",
            "hard_block",
            "No usable Codex/ChatGPT subscription CLI was detected; boundary probes must not fall back to local logic.",
        )
        _write_outputs(out_path, result, auth_payload=auth_payload)
        return result
    result.codex_cli = codex_path

    local_inventory = _local_pdf_inventory(Path(local_pdf_dir), max_items=max(120, papers_per_trial * 4))
    planned_trials = _trial_specs(trials, papers_per_trial)
    if trial_ids:
        allowed = set(trial_ids)
        planned_trials = [trial for trial in planned_trials if trial["trial_id"] in allowed]
        missing = sorted(allowed - {trial["trial_id"] for trial in planned_trials})
        if missing:
            result.add_issue("unknown_trial_id", "hard_block", f"Unknown trial id(s): {', '.join(missing)}")
            _write_outputs(out_path, result, auth_payload=auth_payload)
            return result
    plan = {
        "created_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "local_pdf_dir": str(local_pdf_dir),
        "papers_per_trial": papers_per_trial,
        "trials": planned_trials,
        "local_pdf_inventory_preview": local_inventory,
    }
    (out_path / "boundary_probe_plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    schema_path = out_path / "boundary_probe_output_schema.json"
    schema_path.write_text(json.dumps(BOUNDARY_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8")

    runner = command_runner or _run_command
    for trial in plan["trials"]:
        trial_dir = out_path / trial["trial_id"]
        trial_dir.mkdir(parents=True, exist_ok=True)
        prompt = _trial_prompt(
            trial=trial,
            local_pdf_dir=Path(local_pdf_dir),
            local_inventory=local_inventory,
            papers_per_trial=papers_per_trial,
        )
        prompt_path = trial_dir / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        final_path = trial_dir / "final.json"
        raw_path = trial_dir / "raw.txt"
        cmd = [
            codex_path,
            "-c",
            'service_tier="fast"',
            "--search",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--dangerously-bypass-approvals-and-sandbox",
            "-C",
            str(Path.cwd()),
            "--output-schema",
            str(schema_path),
            "-o",
            str(final_path),
            prompt,
        ]
        started = time.perf_counter()
        try:
            proc = runner(cmd, Path.cwd(), codex_timeout)
        except subprocess.TimeoutExpired as exc:
            proc = subprocess.CompletedProcess(
                args=cmd,
                returncode=124,
                stdout=(exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")),
                stderr=(exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")) + f"\nTIMEOUT after {codex_timeout} seconds",
            )
        elapsed = round(time.perf_counter() - started, 3)
        raw = (proc.stdout or "") + ("\n" if proc.stdout and proc.stderr else "") + (proc.stderr or "")
        raw_path.write_text(raw, encoding="utf-8", errors="replace")
        parsed = _load_json(final_path)
        trial_report = {
            "trial_id": trial["trial_id"],
            "returncode": proc.returncode,
            "elapsed_sec": elapsed,
            "prompt_path": str(prompt_path),
            "raw_path": str(raw_path),
            "final_path": str(final_path),
            "parsed_final": parsed,
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
        (trial_dir / "trial_report.json").write_text(
            json.dumps(trial_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        result.trials.append(trial_report)
        if proc.returncode != 0:
            code = "codex_child_timeout" if proc.returncode == 124 else "codex_child_failed"
            result.add_issue(
                code,
                "hard_block",
                f"External Codex child process failed for {trial['trial_id']} with exit {proc.returncode}.",
                str(raw_path),
            )
        if not parsed:
            result.add_issue(
                "codex_child_missing_json",
                "hard_block",
                f"External Codex child did not produce schema-valid JSON for {trial['trial_id']}.",
                str(final_path),
            )
    _write_outputs(out_path, result, auth_payload=auth_payload)
    return result


def _subscription_payload() -> dict[str, Any]:
    return subscription_status(timeout=20).to_dict()


def _codex_cli_from_auth(auth_payload: dict[str, Any]) -> str | None:
    codex = ((auth_payload.get("subscriptions") or {}).get("codex") or {})
    if codex.get("configured") and codex.get("cli_path"):
        return str(codex["cli_path"])
    return None


def _local_pdf_inventory(local_pdf_dir: Path, *, max_items: int) -> list[dict[str, Any]]:
    if not local_pdf_dir.exists():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(local_pdf_dir.rglob("*.pdf")):
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append({"path": str(path), "name": path.name, "bytes": stat.st_size})
        if len(items) >= max_items:
            break
    return items


def _trial_specs(trials: int, papers_per_trial: int) -> list[dict[str, Any]]:
    base = [
        {
            "trial_id": "mixed_arxiv_local_30",
            "conditions": [
                f"select exactly {papers_per_trial} papers unless a hard access boundary prevents it",
                "mix arXiv English papers and local Chinese PDFs",
                "record metadata, PDF, and text-extraction outcomes separately",
            ],
        },
        {
            "trial_id": "no_login_access_boundary",
            "conditions": [
                f"select exactly {papers_per_trial} papers across arXiv, DOI/publisher pages, and local PDFs",
                "actually visit accessible pages or URLs without publisher login",
                "classify paywall, login, captcha, robots, redirect, and direct PDF outcomes",
                "cap publisher/DOI page probes at 10 papers and 60 total HTTP requests; stop probing after about 8 minutes and summarize the boundary",
            ],
        },
        {
            "trial_id": "paper_store_contract_boundary",
            "conditions": [
                f"select exactly {papers_per_trial} papers and test whether each could become a Paper Store item",
                "distinguish bibrecord_only, pdf_no_text_layer, and full_text-ready states",
                "do not use Sci-Hub or any non-whitelisted source",
            ],
        },
    ]
    if trials <= len(base):
        return base[:trials]
    extra = []
    for index in range(trials - len(base)):
        extra.append(
            {
                "trial_id": f"replicate_boundary_{index + 1}",
                "conditions": [
                    f"repeat the mixed 30-paper boundary probe, sample size {papers_per_trial}",
                    "change query terms and local PDF choices from previous trials",
                    "report variance in what can be obtained without login",
                ],
            }
        )
    return base + extra


def _trial_prompt(
    *,
    trial: dict[str, Any],
    local_pdf_dir: Path,
    local_inventory: list[dict[str, Any]],
    papers_per_trial: int,
) -> str:
    inventory_text = json.dumps(local_inventory[:120], ensure_ascii=False, indent=2)
    return (
        "You are an external Codex child process being tested by econpaper. "
        "Do not edit repository files. Do not inspect this repo except for the local PDF path listed below. "
        "Use a compact PowerShell or Python script for batch probing; do not do one long manual tool sequence per paper. "
        "Do not use Sci-Hub, shadow libraries, credential theft, or publisher login bypasses. "
        "You may run shell commands and make normal web requests/browser-style visits when available. "
        "The parent process is only observing your output.\n\n"
        f"Trial id: {trial['trial_id']}\n"
        "Conditions:\n"
        + "\n".join(f"- {condition}" for condition in trial["conditions"])
        + "\n\n"
        f"Required sample size: {papers_per_trial}. Choose from live arXiv plus local PDFs under: {local_pdf_dir}\n"
        "Local PDF inventory preview (you may inspect the directory yourself too):\n"
        f"{inventory_text}\n\n"
        "Required actions:\n"
        "- Pick a mixed Chinese/English set; include arXiv papers and local Chinese PDFs when possible.\n"
        "- Actually attempt metadata access, page access, direct PDF access, and text/Paper Store readiness checks when legally possible.\n"
        "- Keep probes lightweight: prefer arXiv API, HTTP HEAD/GET with Range or small byte caps, and local PDF first-page/text checks; avoid full PDF downloads unless the file is already local or trivially small.\n"
        "- For arXiv, use live arXiv metadata/API or pages, not fabricated examples. Good query pools include econ.EM, econ.GN, q-fin, and climate/finance/economics terms.\n"
        "- For publisher/DOI sites without login state, record the concrete boundary instead of trying to bypass it.\n"
        "- Record whether a real PDF, only metadata/abstract, or only a local file handle was obtainable.\n"
        "- Finish quickly. If an access class is slow or blocked, record the boundary and continue.\n"
        "- Return exactly one JSON object matching the provided output schema. No prose outside JSON.\n"
    )


def _run_command(cmd: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_outputs(out_path: Path, result: BoundaryProbeResult, *, auth_payload: dict[str, Any] | None = None) -> None:
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    if auth_payload is not None:
        (internal / "boundary_probe_auth_status.json").write_text(
            json.dumps(auth_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    payload = result.to_dict()
    (internal / "boundary_probe_report.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_path / "BOUNDARY_PROBE_REPORT.md").write_text(_summary_markdown(payload), encoding="utf-8")


def _summary_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Literature Access Boundary Probe",
        "",
        f"- Status: `{payload['status']}`",
        f"- Codex CLI: `{payload.get('codex_cli')}`",
        f"- Trials: `{payload.get('trial_count')}`",
        "",
        "| Trial | Return code | Parsed JSON | Key aggregate |",
        "|---|---:|---:|---|",
    ]
    for trial in payload.get("trials", []):
        aggregate = ((trial.get("parsed_final") or {}).get("aggregate") or {})
        key = {
            "papers": aggregate.get("papers_selected"),
            "pdf": aggregate.get("pdf_obtained_count"),
            "text": aggregate.get("text_extracted_count"),
            "login": aggregate.get("login_required_count"),
            "paywall": aggregate.get("paywall_count"),
        }
        lines.append(
            f"| `{trial.get('trial_id')}` | {trial.get('returncode')} | "
            f"{bool(trial.get('parsed_final'))} | `{json.dumps(key, ensure_ascii=False)}` |"
        )
    if payload.get("issues"):
        lines.extend(["", "## Issues", ""])
        for issue in payload["issues"]:
            lines.append(f"- `{issue['code']}` ({issue['severity']}): {issue['message']}")
    return "\n".join(lines) + "\n"
