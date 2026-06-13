from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from econpaper.search.open_search import run_open_search, write_open_search_pack


def _work(title: str, *, doi: str = "", year: int = 2021, citations: int = 10, abstract: str = "") -> dict[str, Any]:
    inverted: dict[str, list[int]] = {}
    for index, word in enumerate(abstract.split()):
        inverted.setdefault(word, []).append(index)
    return {
        "id": f"https://openalex.org/W{abs(hash(title)) % 10**8}",
        "display_name": title,
        "publication_year": year,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "cited_by_count": citations,
        "authorships": [{"author": {"display_name": "Chen, Wei"}}],
        "primary_location": {"source": {"display_name": "JEEM"}},
        "open_access": {"oa_url": "https://example.org/oa.pdf"},
        "abstract_inverted_index": inverted or None,
        "referenced_works": ["https://openalex.org/W111", "https://openalex.org/W222"],
    }


def _arxiv_feed() -> dict[str, Any]:
    return {
        "_raw": """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <updated>2024-01-01T00:00:00Z</updated>
    <published>2024-01-01T00:00:00Z</published>
    <title>Carbon Policy and Machine Learning Forecasts</title>
    <summary>Studies carbon policy evidence with open preprint metadata.</summary>
    <author><name>Jane Doe</name></author>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2401.00001v1" rel="related" type="application/pdf"/>
  </entry>
</feed>"""
    }


def _fake_fetcher(url: str) -> dict[str, Any] | None:
    if "export.arxiv.org" in url:
        return _arxiv_feed()
    if "search=" in url:
        return {
            "results": [
                _work("Low-Carbon City Pilots and Green Innovation", doi="10.1/a", citations=120,
                      abstract="Uses staggered DID to study green patents"),
                _work("Carbon Pricing and Investment", doi="10.1/b", citations=5),
            ]
        }
    if "/works/doi:" in url:
        return _work("Anchor Paper", doi="10.1/anchor")
    if "filter=cites:" in url:
        return {"results": [_work("Citing Paper", doi="10.1/c", year=2023, citations=2)]}
    if "filter=openalex_id:" in url:
        return {"results": [_work("Referenced Classic", doi="10.1/d", year=2015, citations=900)]}
    return None


def test_open_search_runs_queries_and_ranks(tmp_path: Path) -> None:
    result = run_open_search(queries=["low carbon city pilot green innovation"], fetcher=_fake_fetcher)
    assert not result.has_hard_blocks
    assert result.degraded_to is None
    assert len(result.candidates) == 3
    # Citation-weighted ranking puts the 120-citation paper first.
    assert result.candidates[0]["title"].startswith("Low-Carbon")
    assert result.candidates[0]["oa_url"] == "https://example.org/oa.pdf"
    assert any(candidate["found_via"] == "arxiv_search" for candidate in result.candidates)
    # Abstract reconstructed from the inverted index lands in the note excerpt.
    note = result.notes[0]
    assert note["what_it_did"].startswith("[ABSTRACT EXCERPT, unverified]")
    assert "staggered DID" in note["what_it_did"]
    assert note["confidence"] == "low"
    assert note["created_by"] == "econpaper_search_l2_openapi"


def test_open_search_snowball_from_anchor_doi() -> None:
    result = run_open_search(anchor_dois=["10.1/anchor"], fetcher=_fake_fetcher)
    vias = {candidate["found_via"] for candidate in result.candidates}
    assert "snowball_forward" in vias
    assert "snowball_backward" in vias


def test_open_search_offline_hard_blocks() -> None:
    result = run_open_search(queries=["anything"], offline=True)
    assert result.degraded_to is None
    assert result.stop_reason == "offline_not_allowed"
    assert result.api_calls_used == 0
    assert result.has_hard_blocks


def test_open_search_budget_hard_blocks_with_partial_candidates() -> None:
    result = run_open_search(
        queries=["q1", "q2", "q3"],
        fetcher=_fake_fetcher,
        max_calls=1,
    )
    assert result.api_calls_used == 1
    assert result.degraded_to is None
    assert result.stop_reason == "api_call_budget"
    assert result.has_hard_blocks
    assert result.candidates  # partial results kept


def test_open_search_without_inputs_hard_blocks() -> None:
    result = run_open_search()
    assert result.has_hard_blocks


def test_open_search_uses_prescription_query_cards(tmp_path: Path) -> None:
    prescription = {
        "query_cards": [
            {"source": "google_scholar", "language": "en", "query": '"low-carbon city pilot" "green innovation"'},
            {"source": "cnki", "language": "zh", "query": "SU=('低碳城市试点')*('绿色创新')"},
        ],
        "snowball_plan": {"anchor_papers": [{"doi": "10.1/anchor"}]},
    }
    path = tmp_path / "search_prescription.json"
    path.write_text(json.dumps(prescription, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    result = write_open_search_pack(out_dir=out_dir, prescription_path=path, fetcher=_fake_fetcher)
    # Only English cards become API queries; CNKI stays human-side.
    queries = [entry["query"] for entry in result.queries_run]
    assert any("low-carbon city pilot" in query for query in queries)
    assert all("SU=" not in query for query in queries)
    assert (out_dir / "refs.candidates.bib").exists()
    notes = json.loads((out_dir / "external_literature_notes.json").read_text(encoding="utf-8"))
    assert notes
    report = json.loads(
        (out_dir / "reports" / "internal" / "open_search_report.json").read_text(encoding="utf-8")
    )
    assert report["candidate_count"] == len(notes)
