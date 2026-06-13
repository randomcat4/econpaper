from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from econpaper.search.deep_search import (
    build_deep_search_plan,
    run_deep_search,
    write_deep_search_pack,
)
from econpaper.search.router import recommend_tier


def _prescription() -> dict[str, Any]:
    return {
        "research_question": "低碳城市试点是否促进企业绿色创新？",
        "concept_blocks": [
            {
                "id": "treatment",
                "label": "政策/处理",
                "required": True,
                "terms_en": [{"term": "low-carbon city pilot", "required": True}],
                "terms_zh": [{"term": "低碳城市试点", "required": True}],
            },
            {
                "id": "outcome",
                "label": "结果变量",
                "required": True,
                "terms_en": [{"term": "green innovation", "required": True}, {"term": "green patents", "required": False}],
                "terms_zh": [{"term": "绿色创新", "required": True}],
            },
            {
                "id": "identification",
                "label": "识别策略",
                "required": False,
                "terms_en": [{"term": "staggered DID", "required": True}],
                "terms_zh": [{"term": "多期双重差分", "required": True}],
            },
        ],
        "snowball_plan": {"anchor_papers": []},
    }


def _fake_fetcher(url: str) -> dict[str, Any] | None:
    if "search=" in url:
        return {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "display_name": "Low-Carbon City Pilots and Green Innovation",
                    "publication_year": 2021,
                    "doi": "https://doi.org/10.1/a",
                    "cited_by_count": 50,
                    "authorships": [{"author": {"display_name": "Chen, Wei"}}],
                    "abstract_inverted_index": {"Staggered": [0], "DID": [1], "evidence.": [2]},
                }
            ]
        }
    return None


def test_plan_only_without_confirmation_spends_nothing() -> None:
    result = run_deep_search(prescription=_prescription(), plan_confirmed=False, fetcher=_fake_fetcher)
    assert result.status == "awaiting_plan_confirmation"
    assert result.api_calls_used == 0
    assert result.rounds_run == 0
    plan = result.plan
    assert 2 <= len(plan["clarification_questions"]) <= 4
    assert plan["subquestions"], "plan must decompose into subquestions"
    sq = plan["subquestions"][0]
    assert sq["queries_en"] and sq["queries_zh"], "bilingual queries are mandatory at L3"
    assert "Sci-Hub" in plan["source_whitelist_note"] or "Sci-Hub" in str(plan)


def test_confirmed_run_produces_bilingual_coverage_audit() -> None:
    result = run_deep_search(prescription=_prescription(), plan_confirmed=True, fetcher=_fake_fetcher)
    assert result.status == "passed"
    assert result.rounds_run >= 1
    assert result.records
    assert result.stop_reason in {"saturated", "round_budget"}
    # Coverage matrix covers every subquestion x language cell.
    cells = {(cell["subquestion"], cell["language"]) for cell in result.coverage_matrix}
    for sq in result.plan["subquestions"]:
        assert (sq["id"], "en") in cells and (sq["id"], "zh") in cells
    # Chinese empty cells are explained (manual CNKI execution), not silently dropped.
    zh_cells = [cell for cell in result.coverage_matrix if cell["language"] == "zh" and cell["hits"] == 0]
    assert zh_cells
    assert all("explanation" in cell for cell in zh_cells)
    assert any(cell.get("action_needed") == "manual_cnki_execution" for cell in zh_cells)


def test_time_budget_gate_stops_loop() -> None:
    ticks = iter([0.0, 10_000.0, 20_000.0, 30_000.0, 40_000.0])

    def clock() -> float:
        return next(ticks)

    result = run_deep_search(
        prescription=_prescription(),
        plan_confirmed=True,
        fetcher=_fake_fetcher,
        time_budget_seconds=60,
        clock=clock,
    )
    assert result.stop_reason == "time_budget"


def test_api_budget_gate() -> None:
    result = run_deep_search(
        prescription=_prescription(),
        plan_confirmed=True,
        fetcher=_fake_fetcher,
        max_calls=1,
    )
    assert result.api_calls_used <= 1
    assert result.stop_reason in {"api_call_budget", "saturated", "round_budget"}


def test_failure_hard_blocks_without_substitute_result() -> None:
    def broken_fetcher(url: str) -> dict[str, Any] | None:
        raise RuntimeError("network exploded")

    result = run_deep_search(prescription=_prescription(), plan_confirmed=True, fetcher=broken_fetcher)
    assert result.degraded_to is None
    assert result.has_hard_blocks
    assert "deep_search_failed" in {issue.code for issue in result.issues}
    assert result.plan  # the L1-style plan always survives


def test_chinese_reflow_merges_into_loop(tmp_path: Path) -> None:
    ris = tmp_path / "cnki.ris"
    ris.write_text(
        "TY  - JOUR\nAU  - 王芳\nTI  - 低碳城市试点与绿色创新的多期双重差分检验\nJO  - 经济研究\nPY  - 2022\nER  -\n",
        encoding="utf-8",
    )
    result = run_deep_search(
        prescription=_prescription(),
        plan_confirmed=True,
        fetcher=_fake_fetcher,
        extra_records_paths=[ris],
    )
    zh_records = [record for record in result.records if record.language == "zh"]
    assert zh_records, "reflowed CNKI records must enter the deduped bibliography"
    zh_hits = [cell for cell in result.coverage_matrix if cell["language"] == "zh" and cell["hits"] > 0]
    assert zh_hits


def test_write_pack_memo_every_line_sourced(tmp_path: Path) -> None:
    path = tmp_path / "search_prescription.json"
    path.write_text(json.dumps(_prescription(), ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    result = write_deep_search_pack(
        out_dir=out_dir,
        prescription_path=path,
        plan_confirmed=True,
        fetcher=_fake_fetcher,
    )
    assert result.records
    memo = (out_dir / "EVIDENCE_MEMO.md").read_text(encoding="utf-8")
    for line in memo.splitlines():
        if line.startswith("- "):
            assert "[src:" in line, f"unsourced memo line: {line}"
    assert "检索完整性自查" in memo
    notes = json.loads((out_dir / "external_literature_notes.json").read_text(encoding="utf-8"))
    assert all(note["created_by"] == "econpaper_search_l3_deep" for note in notes)
    assert (out_dir / "refs.bib").exists()
    assert (out_dir / "DEEP_SEARCH_PLAN.md").exists()


def test_plan_markdown_written_even_without_confirmation(tmp_path: Path) -> None:
    path = tmp_path / "search_prescription.json"
    path.write_text(json.dumps(_prescription(), ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"
    result = write_deep_search_pack(out_dir=out_dir, prescription_path=path, plan_confirmed=False)
    assert result.status == "awaiting_plan_confirmation"
    plan_md = (out_dir / "DEEP_SEARCH_PLAN.md").read_text(encoding="utf-8")
    assert "澄清问题" in plan_md
    assert not (out_dir / "EVIDENCE_MEMO.md").exists()


def test_router_scenarios() -> None:
    assert recommend_tier("作者已有 refs.bib 只需核验补元数据").tier == "l2_verify"
    assert recommend_tier("写国内政策评估论文，需要中文文献和政策背景，预算敏感").tier == "l1"
    assert recommend_tier("英文 working paper 定位，快速摸清引文图谱").tier == "l2"
    assert recommend_tier("投稿前的系统性文献定位，审稿人质疑漏了文献").tier == "l3"
    assert recommend_tier("开题阶段不确定方向先摸底").tier == "l3_plan_only"
    assert recommend_tier("随便聊聊").tier == "l1"  # default tier is L1
