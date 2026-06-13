from __future__ import annotations

import json
from pathlib import Path

from econpaper.intake import AUTHOR_INPUT_NEEDED
from econpaper.search.ingest import ingest_records, write_ingest_pack
from econpaper.search.records import parse_bibtex, parse_csv_records, parse_ris


_RIS_SAMPLE = """TY  - JOUR
AU  - Chen, Wei
AU  - Li, Hua
TI  - Low-Carbon City Pilots and Green Innovation
JO  - Journal of Environmental Economics and Management
PY  - 2021
VL  - 108
DO  - 10.1016/j.jeem.2021.102461
AB  - Uses staggered DID across pilot waves
 to study firm green patenting.
ER  -
TY  - JOUR
AU  - 王芳
TI  - 低碳城市试点与企业绿色创新
JO  - 经济研究
PY  - 2022
ER  -
"""

_BIB_SAMPLE = """@article{chen2021dup,
  title = {Low-Carbon City Pilots and Green Innovation},
  author = {Chen, Wei and Li, Hua},
  year = {2021},
  journal = {Journal of Environmental Economics and Management},
  doi = {10.1016/j.jeem.2021.102461}
}

@article{smith2020,
  title = {Carbon Pricing and Firm Investment},
  author = {Smith, John},
  year = {2020},
  journal = {American Economic Review}
}
"""


def test_parse_ris_handles_cnki_style_records() -> None:
    records = parse_ris(_RIS_SAMPLE)
    assert len(records) == 2
    english, chinese = records
    assert english.doi == "10.1016/j.jeem.2021.102461"
    assert "firm green patenting" in english.abstract  # continuation line merged
    assert chinese.language == "zh"
    assert chinese.journal == "经济研究"


def test_parse_csv_with_chinese_headers() -> None:
    csv_text = "篇名,作者,刊名,年份,DOI\n碳排放权交易与绿色转型,张三;李四,管理世界,2023,\n"
    records = parse_csv_records(csv_text)
    assert len(records) == 1
    assert records[0].language == "zh"
    assert records[0].authors == ["张三", "李四"]


def test_ingest_dedupes_across_formats_and_assigns_citekeys(tmp_path: Path) -> None:
    ris_path = tmp_path / "export.ris"
    ris_path.write_text(_RIS_SAMPLE, encoding="utf-8")
    bib_path = tmp_path / "zotero.bib"
    bib_path.write_text(_BIB_SAMPLE, encoding="utf-8")
    result = ingest_records([ris_path, bib_path])
    assert not result.has_hard_blocks
    # 4 raw records, the DOI duplicate merged -> 3 kept.
    assert len(result.records) == 3
    assert len(result.merges) == 1
    assert result.merges[0]["match_on"] == "doi"
    keys = {record.key for record in result.records}
    assert len(keys) == 3
    assert all(key.isascii() for key in keys)


def test_ingest_notes_skeleton_never_fakes_summaries(tmp_path: Path) -> None:
    ris_path = tmp_path / "export.ris"
    ris_path.write_text(_RIS_SAMPLE, encoding="utf-8")
    out_dir = tmp_path / "out"
    result = write_ingest_pack([ris_path], out_dir=out_dir)
    notes = json.loads((out_dir / "external_literature_notes.json").read_text(encoding="utf-8"))
    assert len(notes) == len(result.records)
    for note in notes:
        assert note["what_it_did"].startswith(AUTHOR_INPUT_NEEDED)
        assert note["relation_to_this_paper"].startswith(AUTHOR_INPUT_NEEDED)
        assert note["status"] == "needs_author_input"
        assert note["bibtex_entry"].startswith("@")
    refs_text = (out_dir / "refs.bib").read_text(encoding="utf-8")
    assert refs_text.count("@article") == len(result.records)
    assert (out_dir / "INGEST_REPORT.md").exists()


def test_ingest_gb18030_secondary_decode(tmp_path: Path) -> None:
    gbk_path = tmp_path / "cnki.csv"
    gbk_path.write_bytes("篇名,作者,年份\n环境规制与企业全要素生产率,赵六,2020\n".encode("gb18030"))
    result = ingest_records([gbk_path])
    assert not result.has_hard_blocks
    assert result.records[0].title == "环境规制与企业全要素生产率"


def test_ingest_missing_file_hard_blocks(tmp_path: Path) -> None:
    result = ingest_records([tmp_path / "nope.ris"])
    assert result.has_hard_blocks


def test_parse_bibtex_tolerates_nested_braces() -> None:
    text = "@article{key1,\n title = {The {DID} Estimator in {China}},\n author = {Doe, Jane},\n year = {2019}\n}"
    records = parse_bibtex(text)
    assert records[0].title == "The DID Estimator in China"
