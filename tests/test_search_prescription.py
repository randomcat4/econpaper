from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from econpaper.intake import AUTHOR_INPUT_NEEDED
from econpaper.search.prescription import build_search_prescription, write_search_prescription


def _topic_spec(tmp_path: Path) -> Path:
    spec = {
        "research_question": "低碳城市试点是否促进企业绿色创新？",
        "year_range": [2010, 2026],
        "concept_blocks": [
            {
                "id": "treatment",
                "label": "政策/处理",
                "terms": [
                    {"term": "low-carbon city pilot", "required": True},
                    "low carbon pilot policy",
                    {"term": "低碳城市试点", "required": True},
                    "低碳试点政策",
                ],
            },
            {
                "id": "outcome",
                "label": "结果变量",
                "terms": ["green innovation", "green patents", "绿色创新", "绿色专利"],
            },
            {
                "id": "identification",
                "label": "识别策略",
                "required": False,
                "terms": ["staggered DID", "多期双重差分"],
            },
        ],
        "anchor_papers": [{"citekey": "chen2021lowcarbon", "doi": "10.1016/j.jeem.2021.102461"}],
        "screening": {"include_criteria": ["2010 年后", "中国企业样本或跨国对照"]},
    }
    path = tmp_path / "topic_spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return path


def test_prescription_from_topic_spec_builds_all_three_query_cards(tmp_path: Path) -> None:
    result = build_search_prescription(topic_spec_path=_topic_spec(tmp_path))
    assert not result.has_hard_blocks
    prescription = result.prescription
    sources = {card["source"] for card in prescription["query_cards"]}
    assert sources == {"google_scholar", "web_of_science", "cnki"}
    cnki_card = next(card for card in prescription["query_cards"] if card["source"] == "cnki")
    assert cnki_card["query"].startswith("SU=")
    assert "低碳城市试点" in cnki_card["query"]
    wos_card = next(card for card in prescription["query_cards"] if card["source"] == "web_of_science")
    assert wos_card["query"].startswith("TS=(")
    assert " AND " in wos_card["query"]
    # Snowball plan keeps the anchor and the one-round rule.
    assert prescription["snowball_plan"]["anchor_papers"][0]["citekey"] == "chen2021lowcarbon"
    assert prescription["snowball_plan"]["rounds"] == 1
    # Stop rules carry the design defaults.
    stop = prescription["screening"]["stop_rules"]
    assert stop["per_query_max_results"] == 50
    assert stop["no_new_relevant_streak_stop"] == 20
    assert stop["target_relevant_records"] == [30, 60]


def test_prescription_derives_blocks_from_intake_profile(tmp_path: Path) -> None:
    intake = {
        "contribution_statement": "Staggered policy adoption affected firm investment.",
        "treatment_timing": {"treatment_name": "Policy adoption"},
        "author_declared_design": {
            "design_type": "staggered_did",
            "sample_scope": "US public firms, 2005-2020",
        },
        "variable_registry": [
            {"name": "investment_rate", "role": "outcome"},
            {"name": "policy_adopted", "role": "treatment"},
        ],
    }
    intake_path = tmp_path / "intake_profile.json"
    intake_path.write_text(json.dumps(intake), encoding="utf-8")
    result = build_search_prescription(intake_profile_path=intake_path)
    assert not result.has_hard_blocks
    blocks = {block["id"]: block for block in result.prescription["concept_blocks"]}
    assert "treatment" in blocks and "outcome" in blocks and "identification" in blocks
    identification_terms = [item["term"] for item in blocks["identification"]["terms_zh"]]
    assert "多期双重差分" in identification_terms  # non-literal zh glossary, not a direct translation
    # Missing Chinese terms for treatment/outcome are surfaced, not invented.
    missing = result.prescription["missing_author_inputs"]
    assert any("中文术语" in item for item in missing)


def test_prescription_without_inputs_hard_blocks() -> None:
    result = build_search_prescription()
    assert result.has_hard_blocks


def test_write_prescription_outputs_json_and_markdown(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = write_search_prescription(out_dir=out_dir, topic_spec_path=_topic_spec(tmp_path))
    assert not result.has_hard_blocks
    assert (out_dir / "search_prescription.json").exists()
    markdown = (out_dir / "SEARCH_PRESCRIPTION.md").read_text(encoding="utf-8")
    assert "## (c) 分源 query 卡" in markdown
    assert "停止规则" in markdown
    assert (out_dir / "reports" / "internal" / "search_prescription_build.json").exists()


def test_cli_search_prescribe(tmp_path: Path) -> None:
    out_dir = tmp_path / "cli_out"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "econpaper.cli",
            "search",
            "prescribe",
            "--topic-spec",
            str(_topic_spec(tmp_path)),
            "--out",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["prescription"]["tier"] == "l1"


def test_missing_terms_marked_author_input_needed(tmp_path: Path) -> None:
    spec = {"research_question": "", "concept_blocks": [{"id": "treatment", "terms": ["碳交易"]}]}
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    result = build_search_prescription(topic_spec_path=path)
    assert result.prescription["research_question"].startswith(AUTHOR_INPUT_NEEDED)
    assert any("English terms" in item for item in result.prescription["missing_author_inputs"])
