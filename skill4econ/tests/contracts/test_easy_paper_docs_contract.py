from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_CONTRACT = ROOT / "docs" / "ARTIFACT_CONTRACT.md"
AGENT_USAGE = ROOT / "docs" / "AGENT_USAGE.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_artifact_contract_documents_easy_paper_export_boundary() -> None:
    text = _read(ARTIFACT_CONTRACT)

    assert "Downstream EasyPaper Export" in text
    assert "export/adapter" in text
    for artifact in (
        "artifact_manifest.json",
        "status.json",
        "manifest.json",
        "reviewer_risk.json",
        "audit.json",
        "model_table.csv",
        "validation_report.json",
    ):
        assert artifact in text


def test_easy_paper_handoff_risks_are_not_claims() -> None:
    combined = "\n".join([_read(ARTIFACT_CONTRACT), _read(AGENT_USAGE)])

    for status in ("failed", "missing_dependency", "interface_only", "parser-only"):
        assert status in combined
    assert "handoff risks, not empirical claims" in combined
    assert "paper_ready" in combined
    assert "main_estimate" in combined
    assert "claimable status" in combined


def test_agent_usage_documents_finance_gap_and_source_checkout_smoke() -> None:
    text = _read(AGENT_USAGE)

    assert "Finance tier-1 gaps remain adapter specs" in text
    assert "validated artifacts" in text
    assert 'PYTHONPATH = "src"' in text
    assert "python -m skill4econ.cli smoke --suite contracts --strict" in text
