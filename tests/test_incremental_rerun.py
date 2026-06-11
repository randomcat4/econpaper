from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.incremental_rerun import run_incremental_rerun, write_incremental_rerun


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _pack(root: Path, *, status: str, protected: bool = False, result_text: str = "Updated result.") -> Path:
    root.mkdir(parents=True)
    _write_json(
        root / "claim_ledger.json",
        {
            "version": "v3.0",
            "status": "passed",
            "claims": [
                {
                    "claim_id": "claim_main_001",
                    "status": status,
                    "gate_reasons": [] if status == "safe" else ["twfe_only_for_staggered_did"],
                }
            ],
        },
    )
    _write_json(root / "evidence_ledger.json", {"version": "v3.0", "evidence_items": []})
    sections = root / "sections"
    sections.mkdir()
    if protected:
        text = (
            "# Results\n\n"
            "<!-- ECONPAPER:PROTECTED START id=author_para_1 -->\n"
            "Author-edited result paragraph.\n"
            "<!-- ECONPAPER:PROTECTED END -->\n"
        )
    else:
        text = f"# Results\n\n{result_text}\n"
    (sections / "04_results.md").write_text(text, encoding="utf-8")
    (sections / "02_data.md").write_text("# Data\n", encoding="utf-8")
    return root


def test_claim_status_changes_are_diffed(tmp_path: Path) -> None:
    previous = _pack(tmp_path / "previous", status="flag_and_confirm")
    updated = _pack(tmp_path / "updated", status="safe")
    result = run_incremental_rerun(previous_pack_dir=previous, updated_pack_dir=updated)
    assert result.has_hard_blocks is False
    assert result.diff["claim_status_changes"] == [
        {
            "claim_id": "claim_main_001",
            "before": "flag_and_confirm",
            "after": "safe",
            "before_reasons": ["twfe_only_for_staggered_did"],
            "after_reasons": [],
        }
    ]


def test_protected_section_is_preserved_and_suggestion_written(tmp_path: Path) -> None:
    previous = _pack(tmp_path / "previous", status="flag_and_confirm", protected=True)
    updated = _pack(tmp_path / "updated", status="safe", result_text="Regenerated result paragraph.")
    out = tmp_path / "rerun"
    result = write_incremental_rerun(previous_pack_dir=previous, updated_pack_dir=updated, out_dir=out)
    assert result.has_hard_blocks is False
    assert "Author-edited result paragraph." in (out / "sections" / "04_results.md").read_text(encoding="utf-8")
    assert "Regenerated result paragraph." in (out / "suggestions" / "04_results.md").read_text(encoding="utf-8")
    assert result.diff["protected_sections"][0]["action"] == "preserve_previous_write_suggestion"


def test_allow_regenerate_protected_overwrites_with_audit(tmp_path: Path) -> None:
    previous = _pack(tmp_path / "previous", status="flag_and_confirm", protected=True)
    updated = _pack(tmp_path / "updated", status="safe", result_text="Regenerated result paragraph.")
    out = tmp_path / "rerun"
    result = write_incremental_rerun(
        previous_pack_dir=previous,
        updated_pack_dir=updated,
        out_dir=out,
        allow_regenerate_protected=True,
    )
    assert "Regenerated result paragraph." in (out / "sections" / "04_results.md").read_text(encoding="utf-8")
    assert not (out / "suggestions" / "04_results.md").exists()
    assert result.diff["protected_sections"][0]["action"] == "regenerated_with_explicit_permission"


def test_missing_updated_claim_ledger_is_hard_block(tmp_path: Path) -> None:
    previous = _pack(tmp_path / "previous", status="safe")
    updated = tmp_path / "updated"
    updated.mkdir()
    (updated / "sections").mkdir()
    result = run_incremental_rerun(previous_pack_dir=previous, updated_pack_dir=updated)
    assert result.has_hard_blocks is True
    assert "updated_claim_ledger_missing" in {issue.code for issue in result.issues}


def test_cli_writes_rerun_diff_and_report(tmp_path: Path) -> None:
    previous = _pack(tmp_path / "previous", status="flag_and_confirm", protected=True)
    updated = _pack(tmp_path / "updated", status="safe")
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "rerun",
            "--previous-pack",
            str(previous),
            "--updated-pack",
            str(updated),
            "--out",
            str(out),
        ],
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert (out / "reports" / "internal" / "rerun_diff.json").exists()
    assert (out / "AUTHOR_REPORT.md").exists()
    assert (out / "claim_ledger.json").exists()
