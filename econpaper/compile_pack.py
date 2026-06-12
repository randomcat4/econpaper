from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .section_writer import WRITING_ORDER
from .venue import resolve_venue


COMPILE_VERSION = "v3.0"


@dataclass
class CompileIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "path": self.path}


@dataclass
class CompileResult:
    status: str = "passed"
    main_pdf: str | None = None
    main_tex: str | None = None
    main_md: str | None = None
    report: dict[str, Any] = field(default_factory=dict)
    issues: list[CompileIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(CompileIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": COMPILE_VERSION,
            "status": self.status,
            "main_pdf": self.main_pdf,
            "main_tex": self.main_tex,
            "main_md": self.main_md,
            "report": self.report,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def compile_pack(
    pack_dir: str | Path,
    *,
    venue: str | None = None,
    out_dir: str | Path | None = None,
    latex_command: str = "pdflatex",
    max_attempts: int = 2,
) -> CompileResult:
    source = Path(pack_dir)
    target = Path(out_dir) if out_dir else source
    result = CompileResult(report={"attempts": [], "repairs": [], "venue": resolve_venue(venue).to_dict()})
    if not source.exists():
        result.add_issue("pack_dir_missing", "hard_block", f"Pack directory does not exist: {source}", str(source))
        return result
    if target.resolve() != source.resolve():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    profile = resolve_venue(venue)
    main_md = _assemble_main_md(target)
    main_tex = _assemble_main_tex(target, profile)
    result.main_md = str(main_md)
    result.main_tex = str(main_tex)

    command_path = shutil.which(latex_command)
    if not command_path:
        result.status = "fallback"
        result.add_issue("latex_command_unavailable", "style_advice", f"LaTeX command `{latex_command}` is unavailable; markdown fallback produced.")
        _write_outputs(target, result)
        return result

    for attempt in range(1, max_attempts + 1):
        proc = subprocess.run(
            [command_path, "-interaction=nonstopmode", "main.tex"],
            cwd=target,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=60,
        )
        result.report["attempts"].append(
            {
                "attempt": attempt,
                "returncode": proc.returncode,
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
            }
        )
        pdf = target / "main.pdf"
        if proc.returncode == 0 and pdf.exists():
            result.main_pdf = str(pdf)
            result.status = "passed"
            _write_outputs(target, result)
            return result
        if attempt < max_attempts:
            repaired = _repair_common_latex(main_tex)
            if repaired:
                result.report["repairs"].append(repaired)
            else:
                break
    result.status = "fallback"
    result.add_issue("latex_compile_failed", "style_advice", "LaTeX compile did not produce main.pdf; markdown fallback remains available.", str(main_tex))
    _write_outputs(target, result)
    return result


def _assemble_main_md(pack_dir: Path) -> Path:
    sections = pack_dir / "sections"
    lines: list[str] = []
    for filename in WRITING_ORDER:
        path = sections / filename
        if path.exists():
            lines.append(path.read_text(encoding="utf-8").strip())
            lines.append("")
    if not lines:
        lines.append("# Manuscript")
        lines.append("")
        lines.append("[AUTHOR_INPUT_NEEDED: sections]")
    target = pack_dir / "main.md"
    target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return target


def _assemble_main_tex(pack_dir: Path, profile) -> Path:
    sections = pack_dir / "sections"
    body: list[str] = []
    for filename in WRITING_ORDER:
        path = sections / filename
        if path.exists():
            body.append(_markdown_to_latex(path.read_text(encoding="utf-8")))
    table_inputs = []
    for table in sorted((pack_dir / "tables").glob("*.tex")) if (pack_dir / "tables").exists() else []:
        table_inputs.append(f"\\input{{{table.relative_to(pack_dir).as_posix()}}}")
    lines = [
        "\\documentclass[11pt]{article}",
        "\\usepackage[margin=1in]{geometry}",
        "\\usepackage{booktabs}",
        "\\usepackage{hyperref}",
        "\\usepackage{" + profile.citation_package + "}",
        "\\title{Manuscript Draft}",
        "\\author{}",
        "\\date{}",
        "\\begin{document}",
        "\\maketitle",
        f"% Venue template: {profile.template_name}; scope: formatting and templates only.",
        *body,
        *table_inputs,
        "\\end{document}",
        "",
    ]
    target = pack_dir / "main.tex"
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def _markdown_to_latex(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            lines.append("\\section{" + _latex_escape(line[2:]) + "}")
        elif line.startswith("## "):
            lines.append("\\subsection{" + _latex_escape(line[3:]) + "}")
        elif line.startswith("- "):
            lines.append("\\noindent{}\\textbullet{} " + _latex_escape(line[2:]) + "\\\\")
        elif line:
            lines.append(_latex_escape(line) + "\n")
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": "\\textbackslash{}",
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde{}",
        "^": "\\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in str(text))


def _repair_common_latex(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    repaired = text.replace("\\usepackage{natbib}", "\\usepackage{natbib}\n\\setcitestyle{authoryear}")
    if repaired != text:
        path.write_text(repaired, encoding="utf-8")
        return "added_natbib_citation_style"
    return None


def _write_outputs(pack_dir: Path, result: CompileResult) -> None:
    internal = pack_dir / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "compile_report.json").write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    _write_author_report(pack_dir, result)


def _write_author_report(pack_dir: Path, result: CompileResult) -> None:
    report_path = pack_dir / "AUTHOR_REPORT.md"
    existing = report_path.read_text(encoding="utf-8") if report_path.exists() else "# AUTHOR_REPORT\n"
    lines = [
        existing.rstrip(),
        "",
        "## Compile Status",
        "",
        f"- Status: `{result.status}`",
        "- main.md: available.",
        "- main.tex: available.",
    ]
    if result.main_pdf:
        lines.append("- main.pdf: produced.")
    else:
        lines.append("- main.pdf: not produced; markdown fallback is available.")
    if result.issues:
        lines.append("")
        lines.append("### Compile Memo")
        for issue in result.issues:
            lines.append(f"- `{issue.code}` ({issue.severity}): {issue.message}")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
