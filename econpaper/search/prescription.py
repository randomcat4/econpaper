"""L1 precision tier: prescription-driven search (Google Scholar + WoS + CNKI).

The system does not fetch anything at L1. It produces a search prescription —
concept blocks, bilingual term tables, per-source query cards, a snowball plan,
and screening/stop rules — that a human executes with their own institutional
access. Results flow back through `ingest.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..intake import AUTHOR_INPUT_NEEDED
from . import SEARCH_TIERS_VERSION
from .records import contains_cjk

PRESCRIPTION_FILENAME = "search_prescription.json"
PRESCRIPTION_REPORT_FILENAME = "SEARCH_PRESCRIPTION.md"

# Built-in bilingual glossary for common identification strategies. Direct
# translation fails for these (e.g. "staggered adoption" vs 多期双重差分),
# which is the single most common reason Chinese-side searches return nothing.
_DESIGN_TERMS: dict[str, dict[str, list[str]]] = {
    "staggered_did": {
        "en": ["staggered difference-in-differences", "staggered DID", "staggered adoption", "event study"],
        "zh": ["多期双重差分", "渐进双重差分", "渐进性试点", "事件研究"],
    },
    "did": {
        "en": ["difference-in-differences", "DID"],
        "zh": ["双重差分"],
    },
    "event_study": {
        "en": ["event study"],
        "zh": ["事件研究"],
    },
    "rdd": {
        "en": ["regression discontinuity", "RDD"],
        "zh": ["断点回归"],
    },
    "iv": {
        "en": ["instrumental variable", "IV estimation"],
        "zh": ["工具变量"],
    },
    "psm": {
        "en": ["propensity score matching", "PSM"],
        "zh": ["倾向得分匹配"],
    },
    "synthetic_control": {
        "en": ["synthetic control"],
        "zh": ["合成控制"],
    },
}

_DEFAULT_STOP_RULES = {
    "per_query_max_results": 50,
    "no_new_relevant_streak_stop": 20,
    "target_relevant_records": [30, 60],
    "snowball_rounds_before_confirmation": 1,
}

_SOURCE_ROLES = {
    "google_scholar": "召回 + 引文追踪（cited by / related articles）",
    "web_of_science": "精确布尔 + 期刊层级过滤 + 引文报告",
    "cnki": "中文文献 + 政策背景 + 国内试点细节",
}

_SEARCH_LOG_TEMPLATE = (
    "| 日期 | 源 | query 原文 | 命中数 | 看过条数 | 纳入数 | 备注 |\n"
    "|---|---|---|---|---|---|---|\n"
    "|  |  |  |  |  |  |  |\n"
)


@dataclass
class PrescriptionIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "path": self.path}


@dataclass
class PrescriptionBuildResult:
    prescription: dict[str, Any]
    status: str = "passed"
    issues: list[PrescriptionIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(PrescriptionIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "prescription": self.prescription,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def build_search_prescription(
    *,
    topic_spec_path: str | Path | None = None,
    intake_profile_path: str | Path | None = None,
) -> PrescriptionBuildResult:
    result = PrescriptionBuildResult(prescription={})
    spec = _load_json_or_yaml(topic_spec_path, result, "topic_spec") if topic_spec_path else {}
    intake = _load_intake(intake_profile_path, result) if intake_profile_path else {}
    if not spec and not intake:
        result.add_issue(
            "no_prescription_inputs",
            "hard_block",
            "A search prescription needs a topic spec and/or an intake profile; neither was usable.",
        )
        return result

    missing: list[str] = []
    research_question = str(
        spec.get("research_question")
        or intake.get("contribution_statement")
        or ""
    ).strip()
    if not research_question or research_question.startswith(AUTHOR_INPUT_NEEDED):
        missing.append("research question (one sentence)")
        research_question = f"{AUTHOR_INPUT_NEEDED}: research question"

    blocks = _concept_blocks(spec, intake, missing)
    if not blocks:
        result.add_issue(
            "no_concept_blocks",
            "hard_block",
            "Could not derive any concept block from the topic spec or intake profile.",
        )
        return result

    year_range = _year_range(spec)
    query_cards = _query_cards(blocks, year_range, missing)
    snowball = _snowball_plan(spec, missing)
    screening = _screening(spec, missing)

    result.prescription = {
        "version": SEARCH_TIERS_VERSION,
        "tier": "l1",
        "research_question": research_question,
        "year_range": year_range,
        "concept_blocks": blocks,
        "query_cards": query_cards,
        "snowball_plan": snowball,
        "screening": screening,
        "search_log_template": _SEARCH_LOG_TEMPLATE,
        "missing_author_inputs": _dedupe(missing),
        "reflow_contract": {
            "accepted_inputs": ["RIS", "BibTeX", "CSV (CNKI/GS export)", "Zotero-exported .bib"],
            "command": "econpaper search ingest --input <export-file> --out <dir>",
            "note": "回流后系统只做去重/规范化/notes 骨架；what_it_did 与 relation_to_this_paper 由作者填写。",
        },
    }
    if missing:
        result.add_issue(
            "prescription_needs_author_input",
            "flag",
            f"{len(_dedupe(missing))} prescription field(s) still need author input before execution.",
        )
    return result


def write_search_prescription(
    *,
    out_dir: str | Path,
    topic_spec_path: str | Path | None = None,
    intake_profile_path: str | Path | None = None,
) -> PrescriptionBuildResult:
    result = build_search_prescription(
        topic_spec_path=topic_spec_path,
        intake_profile_path=intake_profile_path,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    if result.prescription:
        (out_path / PRESCRIPTION_FILENAME).write_text(
            json.dumps(result.prescription, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_path / PRESCRIPTION_REPORT_FILENAME).write_text(_prescription_markdown(result.prescription), encoding="utf-8")
    (internal / "search_prescription_build.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


# ---------------------------------------------------------------------------
# Concept blocks
# ---------------------------------------------------------------------------

def _concept_blocks(spec: dict[str, Any], intake: dict[str, Any], missing: list[str]) -> list[dict[str, Any]]:
    raw_blocks = spec.get("concept_blocks")
    blocks: list[dict[str, Any]] = []
    if isinstance(raw_blocks, list) and raw_blocks:
        for index, entry in enumerate(raw_blocks, start=1):
            if not isinstance(entry, dict):
                continue
            block = _normalize_block(
                block_id=str(entry.get("id") or entry.get("role") or f"block_{index}"),
                label=str(entry.get("label") or entry.get("id") or f"block {index}"),
                raw_terms=list(entry.get("terms") or []) + list(entry.get("terms_en") or []) + list(entry.get("terms_zh") or []),
                required=bool(entry.get("required", True)),
                source="author_provided",
            )
            blocks.append(block)
    else:
        blocks = _blocks_from_intake(intake)
    for block in blocks:
        if not block["terms_en"]:
            missing.append(f"English terms for concept block `{block['id']}`")
        if not block["terms_zh"]:
            missing.append(f"中文术语 for concept block `{block['id']}`")
    return blocks


def _normalize_block(
    *, block_id: str, label: str, raw_terms: list[Any], required: bool, source: str
) -> dict[str, Any]:
    terms_en: list[dict[str, Any]] = []
    terms_zh: list[dict[str, Any]] = []
    for raw in raw_terms:
        if isinstance(raw, dict):
            term = str(raw.get("term") or "").strip()
            term_required = bool(raw.get("required", False))
        else:
            term = str(raw).strip()
            term_required = False
        if not term:
            continue
        bucket = terms_zh if contains_cjk(term) else terms_en
        if all(existing["term"] != term for existing in bucket):
            bucket.append({"term": term, "required": term_required})
    for bucket in (terms_en, terms_zh):
        if bucket and not any(item["required"] for item in bucket):
            bucket[0]["required"] = True
    return {
        "id": block_id,
        "label": label,
        "required": required,
        "terms_en": terms_en,
        "terms_zh": terms_zh,
        "source": source,
    }


def _blocks_from_intake(intake: dict[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    timing = intake.get("treatment_timing") or {}
    treatment = str(timing.get("treatment_name") or "").strip()
    if treatment and not treatment.startswith(AUTHOR_INPUT_NEEDED):
        blocks.append(
            _normalize_block(
                block_id="treatment",
                label="政策/处理 (treatment)",
                raw_terms=[{"term": treatment, "required": True}],
                required=True,
                source="derived_from_intake",
            )
        )
    outcome_terms: list[str] = []
    for row in intake.get("variable_registry") or []:
        if isinstance(row, dict) and "outcome" in str(row.get("role", "")):
            name = str(row.get("name") or "").strip()
            if name and not name.startswith(AUTHOR_INPUT_NEEDED):
                outcome_terms.append(name.replace("_", " "))
    if outcome_terms:
        blocks.append(
            _normalize_block(
                block_id="outcome",
                label="结果变量 (outcome)",
                raw_terms=outcome_terms,
                required=True,
                source="derived_from_intake",
            )
        )
    design = intake.get("author_declared_design") or {}
    design_type = str(design.get("design_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    glossary = _DESIGN_TERMS.get(design_type)
    if glossary:
        blocks.append(
            _normalize_block(
                block_id="identification",
                label="识别策略 (identification)",
                raw_terms=glossary["en"] + glossary["zh"],
                required=False,
                source="derived_from_intake",
            )
        )
    sample_scope = str(design.get("sample_scope") or "").strip()
    if sample_scope and not sample_scope.startswith(AUTHOR_INPUT_NEEDED):
        blocks.append(
            _normalize_block(
                block_id="population",
                label="对象与范围 (population/region)",
                raw_terms=[sample_scope],
                required=False,
                source="derived_from_intake",
            )
        )
    return blocks


# ---------------------------------------------------------------------------
# Query cards
# ---------------------------------------------------------------------------

def _terms(block: dict[str, Any], language: str, limit: int) -> list[str]:
    bucket = block["terms_en"] if language == "en" else block["terms_zh"]
    ordered = [item["term"] for item in bucket if item["required"]] + [
        item["term"] for item in bucket if not item["required"]
    ]
    return ordered[:limit]


def _query_cards(blocks: list[dict[str, Any]], year_range: list[int] | None, missing: list[str]) -> list[dict[str, Any]]:
    required_blocks = [block for block in blocks if block["required"]] or blocks[:2]
    optional_blocks = [block for block in blocks if not block["required"]]
    cards: list[dict[str, Any]] = []
    year_note = (
        f"年份区间：{year_range[0]}–{year_range[1]}（GS 用 Custom range；WoS 用 PY=；CNKI 用发表时间）"
        if year_range
        else "年份区间：作者按研究窗口设定"
    )

    en_core = [_terms(block, "en", 2) for block in required_blocks if _terms(block, "en", 2)]
    if len(en_core) >= 2:
        broad = " ".join(f'"{terms[0]}"' for terms in en_core)
        cards.append(
            {
                "source": "google_scholar",
                "role": _SOURCE_ROLES["google_scholar"],
                "language": "en",
                "query": broad,
                "notes": [
                    "布尔能力弱：靠短语引号收口；每个概念组合只出 1–2 条宽 query。",
                    "命中锚点论文后改用 cited by / related articles 追踪（见滚雪球计划）。",
                    year_note,
                ],
            }
        )
        cards.append(
            {
                "source": "google_scholar",
                "role": _SOURCE_ROLES["google_scholar"],
                "language": "en",
                "query": f'intitle:"{en_core[0][0]}" ' + " ".join(f'"{terms[0]}"' for terms in en_core[1:]),
                "notes": ["intitle: 收紧第一概念块，降低前 50 条噪音。", year_note],
            }
        )
        ts_clauses = [
            "TS=(" + " OR ".join(f'"{term}"' for term in terms) + ")" for terms in en_core
        ]
        optional_en = [_terms(block, "en", 2) for block in optional_blocks if _terms(block, "en", 2)]
        if optional_en:
            ts_clauses.append("TS=(" + " OR ".join(f'"{term}"' for term in optional_en[0]) + ")")
        cards.append(
            {
                "source": "web_of_science",
                "role": _SOURCE_ROLES["web_of_science"],
                "language": "en",
                "query": " AND ".join(ts_clauses),
                "notes": [
                    "Refine: WoS Category = Economics（必要时加 Business, Finance / Environmental Studies）。",
                    "用 JCR 分区与引文报告收口；导出含 abstract 的 RIS。",
                    "WoS 收不到 working paper：NBER/SSRN 阶段文献回到 GS 卡补。",
                    year_note,
                ],
            }
        )
    else:
        missing.append("at least two concept blocks with English terms (treatment + outcome) for GS/WoS query cards")

    zh_core = [_terms(block, "zh", 3) for block in required_blocks if _terms(block, "zh", 3)]
    if len(zh_core) >= 2:
        su_clauses = ["(" + "+".join(f"'{term}'" for term in terms) + ")" for terms in zh_core]
        cards.append(
            {
                "source": "cnki",
                "role": _SOURCE_ROLES["cnki"],
                "language": "zh",
                "query": "SU=" + "*".join(su_clauses),
                "notes": [
                    "专业检索语法：SU=主题；同义词用 + 并联，概念块之间用 * 相交。",
                    "来源类别用 CSSCI / 北大核心收口；导出 RIS 或自定义 CSV（含摘要）。",
                    "政策文件改用『篇名』精确检索政策全名。",
                    year_note,
                ],
            }
        )
    else:
        missing.append("中文术语覆盖至少两个核心概念块（CNKI query 卡）")
    return cards


def _snowball_plan(spec: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    anchors_raw = spec.get("anchor_papers") or []
    anchors: list[dict[str, str]] = []
    for entry in anchors_raw if isinstance(anchors_raw, list) else []:
        if isinstance(entry, str):
            anchors.append({"title": entry.strip()})
        elif isinstance(entry, dict):
            anchor = {
                key: str(entry.get(key)).strip()
                for key in ("citekey", "title", "doi")
                if entry.get(key)
            }
            if anchor:
                anchors.append(anchor)
    if not anchors:
        missing.append("1–3 anchor papers for the snowball plan")
    return {
        "anchor_papers": anchors,
        "backward": "锚点 references 里按概念块筛（题录层面判断即可）。",
        "forward": "GS 与 WoS 各做一次 cited-by，按年份倒序取前 30 条。",
        "rounds": _DEFAULT_STOP_RULES["snowball_rounds_before_confirmation"],
        "round_rule": "滚一轮即停；新锚点需作者确认后才滚第二轮。",
    }


def _screening(spec: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    screening_raw = spec.get("screening") if isinstance(spec.get("screening"), dict) else {}
    include = [str(item).strip() for item in screening_raw.get("include_criteria") or [] if str(item).strip()]
    exclude = [str(item).strip() for item in screening_raw.get("exclude_criteria") or [] if str(item).strip()]
    if not include:
        missing.append("inclusion criteria judgeable at the bibliographic-record level (year, country, method, journal tier)")
        include = [f"{AUTHOR_INPUT_NEEDED}: 纳入标准（年份、国家、方法、期刊层级等题录层面可判断项）"]
    if not exclude:
        exclude = ["与研究问题无关的纯综述/评论（除非作为锚点）"]
    stop_rules = dict(_DEFAULT_STOP_RULES)
    for key in stop_rules:
        if key in screening_raw:
            stop_rules[key] = screening_raw[key]
    return {"include_criteria": include, "exclude_criteria": exclude, "stop_rules": stop_rules}


# ---------------------------------------------------------------------------
# Helpers and markdown rendering
# ---------------------------------------------------------------------------

def _year_range(spec: dict[str, Any]) -> list[int] | None:
    raw = spec.get("year_range")
    if isinstance(raw, list) and len(raw) == 2:
        try:
            return [int(raw[0]), int(raw[1])]
        except (TypeError, ValueError):
            return None
    return None


def _load_json_or_yaml(path: str | Path | None, result: PrescriptionBuildResult, name: str) -> dict[str, Any]:
    if path is None:
        return {}
    source = Path(path)
    if not source.exists():
        result.add_issue("missing_input_file", "hard_block", f"{name} file does not exist: {source}", str(source))
        return {}
    text = source.read_text(encoding="utf-8-sig")
    if source.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore

            payload = yaml.safe_load(text) or {}
        except Exception as exc:
            result.add_issue("invalid_yaml", "hard_block", f"Could not parse {name} YAML: {exc}", str(source))
            return {}
    else:
        try:
            payload = json.loads(text)
        except Exception as exc:
            result.add_issue("invalid_json", "hard_block", f"Could not parse {name} JSON: {exc}", str(source))
            return {}
    return payload if isinstance(payload, dict) else {}


def _load_intake(path: str | Path | None, result: PrescriptionBuildResult) -> dict[str, Any]:
    payload = _load_json_or_yaml(path, result, "intake_profile")
    if "intake_profile" in payload and isinstance(payload["intake_profile"], dict):
        return payload["intake_profile"]
    return payload


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _prescription_markdown(prescription: dict[str, Any]) -> str:
    lines = [
        "# SEARCH PRESCRIPTION (L1 精准档)",
        "",
        f"研究问题：{prescription['research_question']}",
        "",
        "执行原则：系统不负责『搜到』，本处方负责『怎么搜』。三源分工执行，回流走",
        f"`{prescription['reflow_contract']['command']}`。",
        "",
        "## (a) 概念块分解 + (b) 中英术语扩展表",
        "",
    ]
    for block in prescription["concept_blocks"]:
        lines.append(f"### {block['label']} (`{block['id']}`, {'必含' if block['required'] else '可选'})")
        lines.append("")
        lines.append("| 语言 | 术语 | 必含 |")
        lines.append("|---|---|---|")
        for language, bucket in (("en", block["terms_en"]), ("zh", block["terms_zh"])):
            if not bucket:
                lines.append(f"| {language} | {AUTHOR_INPUT_NEEDED} | — |")
                continue
            for item in bucket:
                lines.append(f"| {language} | {item['term']} | {'是' if item['required'] else '否'} |")
        lines.append("")
    lines.extend(["## (c) 分源 query 卡", ""])
    for index, card in enumerate(prescription["query_cards"], start=1):
        lines.append(f"### Query {index}: {card['source']} ({card['language']})")
        lines.append("")
        lines.append(f"分工：{card['role']}")
        lines.append("")
        lines.append("```text")
        lines.append(card["query"])
        lines.append("```")
        lines.extend(f"- {note}" for note in card["notes"])
        lines.append("")
    snowball = prescription["snowball_plan"]
    lines.extend(["## (d) 种子文献滚雪球计划", ""])
    if snowball["anchor_papers"]:
        for anchor in snowball["anchor_papers"]:
            label = anchor.get("citekey") or anchor.get("title") or anchor.get("doi")
            lines.append(f"- 锚点：{label}")
    else:
        lines.append(f"- {AUTHOR_INPUT_NEEDED}: 1–3 篇锚点论文")
    lines.extend(
        [
            f"- 向后：{snowball['backward']}",
            f"- 向前：{snowball['forward']}",
            f"- 轮次规则：{snowball['round_rule']}",
            "",
            "## (e) 筛选标准 + 停止规则",
            "",
            "纳入标准：",
        ]
    )
    lines.extend(f"- {item}" for item in prescription["screening"]["include_criteria"])
    lines.append("")
    lines.append("排除标准：")
    lines.extend(f"- {item}" for item in prescription["screening"]["exclude_criteria"])
    stop = prescription["screening"]["stop_rules"]
    lines.extend(
        [
            "",
            "停止规则：",
            f"- 每条 query 只看前 {stop['per_query_max_results']} 条；",
            f"- 连续 {stop['no_new_relevant_streak_stop']} 条无新增相关项即停；",
            f"- 三源合计相关项达到 {stop['target_relevant_records'][0]}–{stop['target_relevant_records'][1]} 篇题录即停。",
            "",
            "## 检索日志模板",
            "",
            prescription["search_log_template"],
        ]
    )
    missing = prescription.get("missing_author_inputs") or []
    lines.extend(["## 待作者补充", ""])
    if missing:
        lines.extend(f"- {item}" for item in missing)
    else:
        lines.append("- 无。")
    return "\n".join(lines) + "\n"
