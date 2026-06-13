from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from econpaper.search.verify import (
    STATUS_DOI_NOT_FOUND,
    STATUS_MISMATCH,
    STATUS_OFFLINE,
    STATUS_TITLE_NOT_FOUND,
    STATUS_VERIFIED,
    verify_references,
    write_verification_report,
)


_REFS = """@article{good2021,
  title = {Low-Carbon City Pilots and Green Innovation},
  author = {Chen, Wei},
  year = {2021},
  doi = {10.1016/j.jeem.2021.102461}
}

@article{fake2030,
  title = {A Paper That Does Not Exist},
  author = {Nobody, X},
  year = {2030},
  doi = {10.9999/fabricated.404}
}

@article{notitlematch2019,
  title = {Some Extremely Obscure Working Paper Title},
  author = {Doe, Jane},
  year = {2019}
}

@article{zhang2022zh,
  title = {碳排放权交易与企业绿色转型},
  author = {张三},
  year = {2022},
  language = {zh}
}
"""


def _fake_fetcher(url: str) -> dict[str, Any] | None:
    if "10.1016" in url:
        return {
            "message": {
                "title": ["Low-Carbon City Pilots and Green Innovation"],
                "container-title": ["Journal of Environmental Economics and Management"],
                "published-print": {"date-parts": [[2021]]},
            }
        }
    if "10.9999" in url:
        return None  # Crossref 404
    if "query.bibliographic" in url:
        return {"message": {"items": []}}
    if "openalex" in url:
        return {"results": []}
    return None


def _write_refs(tmp_path: Path) -> Path:
    refs = tmp_path / "refs.bib"
    refs.write_text(_REFS, encoding="utf-8")
    return refs


def test_verification_statuses_and_hard_block_for_fabricated_doi(tmp_path: Path) -> None:
    result = verify_references(_write_refs(tmp_path), fetcher=_fake_fetcher)
    by_key = {entry["paper_key"]: entry for entry in result.entries}
    assert by_key["good2021"]["status"] == STATUS_VERIFIED
    assert by_key["fake2030"]["status"] == STATUS_DOI_NOT_FOUND
    assert by_key["notitlematch2019"]["status"] == STATUS_TITLE_NOT_FOUND
    # Chinese entries without DOI are not burned against APIs nor flagged suspicious.
    assert by_key["zhang2022zh"]["status"] == STATUS_OFFLINE
    # Fabricated DOI is the non-overridable fake-citation signal.
    assert result.has_hard_blocks
    hard = [issue for issue in result.issues if issue.severity == "hard_block"]
    assert hard[0].paper_key == "fake2030"
    # Unconfirmed title is flag-and-confirm, not a block.
    flags = [issue for issue in result.issues if issue.severity == "flag"]
    assert any(issue.paper_key == "notitlematch2019" for issue in flags)


def test_verification_enriches_missing_metadata(tmp_path: Path) -> None:
    result = verify_references(_write_refs(tmp_path), fetcher=_fake_fetcher)
    good = next(record for record in result.records if record.key == "good2021")
    assert good.journal == "Journal of Environmental Economics and Management"
    entry = next(entry for entry in result.entries if entry["paper_key"] == "good2021")
    assert "journal" in entry["enriched_fields"]


def test_offline_mode_hard_blocks_without_guessing(tmp_path: Path) -> None:
    result = verify_references(_write_refs(tmp_path), offline=True)
    assert result.api_calls_used == 0
    assert all(entry["status"] == STATUS_OFFLINE for entry in result.entries)
    assert result.has_hard_blocks
    assert "offline_not_allowed" in {issue.code for issue in result.issues}


def test_call_budget_skips_remaining_entries(tmp_path: Path) -> None:
    calls: list[str] = []

    def counting_fetcher(url: str) -> dict[str, Any] | None:
        calls.append(url)
        return _fake_fetcher(url)

    result = verify_references(_write_refs(tmp_path), fetcher=counting_fetcher, max_calls=1)
    assert result.api_calls_used == 1
    statuses = {entry["paper_key"]: entry["status"] for entry in result.entries}
    assert statuses["good2021"] == STATUS_VERIFIED
    assert statuses["fake2030"] == "skipped_budget"


def test_metadata_mismatch_flagged(tmp_path: Path) -> None:
    refs = tmp_path / "refs.bib"
    refs.write_text(
        "@article{wrong2021,\n title = {A Totally Different Subject Entirely},\n"
        " author = {Chen, Wei},\n year = {1999},\n doi = {10.1016/j.jeem.2021.102461}\n}\n",
        encoding="utf-8",
    )
    result = verify_references(refs, fetcher=_fake_fetcher)
    assert result.entries[0]["status"] == STATUS_MISMATCH
    assert not result.has_hard_blocks  # mismatch is flag-and-confirm


def test_write_verification_report_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = write_verification_report(_write_refs(tmp_path), out_dir=out_dir, fetcher=_fake_fetcher)
    report_path = out_dir / "reports" / "internal" / "citation_verification_report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["summary"][STATUS_VERIFIED] == 1
    assert (out_dir / "refs.normalized.bib").exists()
    assert result.summary()[STATUS_DOI_NOT_FOUND] == 1
