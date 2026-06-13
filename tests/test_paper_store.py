from __future__ import annotations

import json
from pathlib import Path

from econpaper.search.paper_store import (
    add_paper,
    build_struct,
    list_papers,
    load_meta,
    outline,
    read_section,
    search_store,
)


_PAPER_MD = """# Low-Carbon City Pilots and Green Innovation

## 1 Introduction

This paper studies pilot policies.

## 5 Results

### 5.2 Heterogeneity

Larger firms respond more strongly to the pilot policy.

| group | effect |
|---|---|
| large | 0.12 |
| small | 0.03 |

## 6 Conclusion

Figure 3 shows the event study.
"""


def _add_sample(tmp_path: Path, **overrides) -> Path:
    store = tmp_path / "paper_store"
    md = tmp_path / "converted.md"
    md.write_text(_PAPER_MD, encoding="utf-8")
    pdf = tmp_path / "raw.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    kwargs = dict(
        citekey="chen2021lowcarbon",
        title_zh="低碳城市试点与企业绿色创新",
        title_en="Low-Carbon City Pilots and Green Innovation",
        pdf_path=pdf,
        paper_md_path=md,
        source_url="https://doi.org/10.1016/j.jeem.2021.102461",
        converter="mineru",
        converter_version="2.1.0",
    )
    kwargs.update(overrides)
    result = add_paper(store, **kwargs)
    assert not result.has_hard_blocks, [issue.to_dict() for issue in result.issues]
    return store


def test_add_paper_layout_and_bilingual_pdf_name(tmp_path: Path) -> None:
    store = _add_sample(tmp_path)
    paper_dir = store / "chen2021lowcarbon"
    meta = load_meta(store, "chen2021lowcarbon")
    assert meta["status"] == "full_text"
    assert meta["converter"] == {"tool": "mineru", "version": "2.1.0"}
    pdf_name = meta["files"]["pdf"]
    assert pdf_name.startswith("低碳城市试点与企业绿色创新_Low-Carbon-City-Pilots")
    assert (paper_dir / pdf_name).exists()
    assert (paper_dir / "paper.md").exists()
    assert (paper_dir / "paper.struct.json").exists()


def test_short_title_truncation_and_single_language(tmp_path: Path) -> None:
    long_en = "An Extremely Long Title " * 10
    store = _add_sample(tmp_path, citekey="long2020paper", title_zh="", title_en=long_en)
    meta = load_meta(store, "long2020paper")
    pdf_name = meta["files"]["pdf"]
    assert len(pdf_name) <= 40 + len(".pdf")
    assert "_" not in pdf_name  # single-language title: no machine-translated counterpart
    assert meta["title_en"] == long_en  # full title preserved in meta.json


def test_struct_outline_tables_figures() -> None:
    struct = build_struct(_PAPER_MD)
    anchors = [section["anchor"] for section in struct["outline"]]
    assert "5.2" in anchors and "1" in anchors
    assert len(struct["tables"]) == 1
    assert any("Figure 3" in figure["text"] for figure in struct["figures"])


def test_read_section_by_anchor_and_ref(tmp_path: Path) -> None:
    store = _add_sample(tmp_path)
    section = read_section(store, "chen2021lowcarbon", "5.2")
    assert section is not None
    assert section["anchor"] == "chen2021lowcarbon#5.2"
    assert "Larger firms respond" in section["text"]
    # citekey#anchor refs from notes resolve too.
    by_ref = read_section(store, "chen2021lowcarbon", "chen2021lowcarbon#5.2")
    assert by_ref is not None and by_ref["title"] == section["title"]
    by_title = read_section(store, "chen2021lowcarbon", "conclusion")
    assert by_title is not None and by_title["anchor"].endswith("#6")


def test_search_store_returns_section_anchors(tmp_path: Path) -> None:
    store = _add_sample(tmp_path)
    hits = search_store(store, "pilot policy")
    assert hits
    assert hits[0]["citekey"] == "chen2021lowcarbon"
    assert hits[0]["anchor"].startswith("chen2021lowcarbon#")


def test_pdf_without_text_layer_records_boundary(tmp_path: Path) -> None:
    store = tmp_path / "store"
    pdf = tmp_path / "raw.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    result = add_paper(store, citekey="nomd2022", title_en="No Text Layer Yet", pdf_path=pdf)
    assert result.meta["status"] == "pdf_no_text_layer"
    assert any(issue.code == "no_text_layer" for issue in result.issues)
    assert not result.has_hard_blocks


def test_invalid_citekey_hard_blocks(tmp_path: Path) -> None:
    result = add_paper(tmp_path / "store", citekey="Bad Key!", title_en="x")
    assert result.has_hard_blocks


def test_list_papers(tmp_path: Path) -> None:
    store = _add_sample(tmp_path)
    papers = list_papers(store)
    assert [paper["citekey"] for paper in papers] == ["chen2021lowcarbon"]
    assert outline(store, "chen2021lowcarbon")
