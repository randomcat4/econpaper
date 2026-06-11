"""Minimal AER/JFE end-to-end mock PoC checks."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.run_econ_paper import parse_args, run_econ_paper


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SECTION_HEADINGS = (
    "Introduction",
    "Data",
    "Empirical Strategy",
    "Results",
    "Robustness",
    "Conclusion",
)


async def _run_mock(request_path: str, out: Path):
    args = parse_args([request_path, "--out", str(out), "--mock-llm", "--no-pdf"])
    return await run_econ_paper(args, repo_root=ROOT)


def _all_output_text(out: Path) -> str:
    pieces = []
    for path in out.rglob("*"):
        if path.is_file():
            pieces.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(pieces)


@pytest.mark.asyncio
async def test_aer_minimal_poc_writes_structure_and_file_backed_figure(tmp_path):
    out = tmp_path / "aer_minimal"
    summary = await _run_mock("examples/econ/aer_minimal_request.yaml", out)

    for filename in (
        "events.jsonl",
        "request.normalized.json",
        "manifest.normalized.json",
        "venue.normalized.json",
        "main.tex",
    ):
        assert (out / filename).is_file()
    assert Path(summary["main_tex"]).is_file()

    main_tex = (out / "main.tex").read_text(encoding="utf-8")
    for heading in REQUIRED_SECTION_HEADINGS:
        assert f"\\section{{{heading}}}" in main_tex
    assert "\\section{Experiment}" not in main_tex
    assert "\\section{Experiments}" not in main_tex

    results_start = main_tex.index("\\section{Results}")
    robustness_start = main_tex.index("\\section{Robustness}")
    results_block = main_tex[results_start:robustness_start]
    assert "\\begin{figure}" in results_block
    assert "\\label{fig:event_study_main}" in results_block
    assert "generated_figures" not in main_tex

    all_output = _all_output_text(out)
    assert not re.search(r"sk-[A-Za-z0-9]", all_output)


@pytest.mark.asyncio
async def test_jfe_minimal_poc_preserves_finance_venue_hints(tmp_path):
    out = tmp_path / "jfe_minimal"
    await _run_mock("examples/finance/jfe_minimal_request.yaml", out)

    venue = json.loads((out / "venue.normalized.json").read_text(encoding="utf-8"))
    assert venue["name"] == "journal-of-financial-economics"
    assert venue["anonymous"] is True
    assert venue["double_spacing"] is True
    assert venue["min_font_pt"] == 12
    assert venue["required_sections"] == list(REQUIRED_SECTION_HEADINGS)

    main_tex = (out / "main.tex").read_text(encoding="utf-8")
    assert "\\author{Anonymous Manuscript}" in main_tex
    assert "% double_spacing: True" in main_tex
    assert "% min_font_pt: 12" in main_tex
    for heading in REQUIRED_SECTION_HEADINGS:
        assert f"\\section{{{heading}}}" in main_tex
