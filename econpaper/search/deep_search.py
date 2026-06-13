"""L3 deep-research tier: bilingual, full-coverage agentic search loop.

Control flow borrowed from GPT Deep Research / Grok DeepSearch:

    plan (clarify + confirm) -> parallel fan-out -> re-rank -> land full texts
      -> read -> extract gaps -> second-round queries -> ... -> saturation or
      budget exhaustion -> synthesis

Hard properties enforced here:
- the plan is shown first and nothing is spent until it is confirmed;
- three budget gates (rounds, API calls, wall-clock) stop the loop loudly;
- every line of the evidence memo carries a source identifier;
- the coverage audit matrix (subquestion x language) explains every empty cell;
- failures are reported as hard boundaries, not hidden behind substitute output.

The English side runs on the L2 open-API layer. The Chinese side has no legal
open API: CNKI query cards are emitted for browser-side execution, and CNKI
exports can be fed back through `extra_records_paths` between rounds.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..intake import AUTHOR_INPUT_NEEDED
from . import SEARCH_TIERS_VERSION
from .ingest import structured_note_skeleton
from .open_search import run_open_search
from .records import (
    BibRecord,
    assign_citekeys,
    dedupe_records,
    parse_records_file,
    records_to_bibtex,
)
from .verify import Fetcher

DEFAULT_MAX_ROUNDS = 3
DEFAULT_MAX_CALLS = 40
DEFAULT_TIME_BUDGET_SECONDS = 1800  # design §3.4: 30-minute hard stop

PLAN_FILENAME = "deep_search_plan.json"
PLAN_REPORT_FILENAME = "DEEP_SEARCH_PLAN.md"
MEMO_FILENAME = "EVIDENCE_MEMO.md"


@dataclass
class DeepSearchIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class DeepSearchResult:
    plan: dict[str, Any] = field(default_factory=dict)
    records: list[BibRecord] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    coverage_matrix: list[dict[str, Any]] = field(default_factory=list)
    rounds_run: int = 0
    api_calls_used: int = 0
    stop_reason: str = ""
    degraded_to: str | None = None
    status: str = "passed"
    issues: list[DeepSearchIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(DeepSearchIssue(code=code, severity=severity, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "stop_reason": self.stop_reason,
            "rounds_run": self.rounds_run,
            "api_calls_used": self.api_calls_used,
            "degraded_to": self.degraded_to,
            "plan": self.plan,
            "record_count": len(self.records),
            "coverage_matrix": self.coverage_matrix,
            "issues": [issue.to_dict() for issue in self.issues],
        }


# ---------------------------------------------------------------------------
# Phase A: plan (clarifications + bilingual prescription); spend nothing yet
# ---------------------------------------------------------------------------

def build_deep_search_plan(prescription: dict[str, Any]) -> dict[str, Any]:
    subquestions = _subquestions(prescription)
    clarifications = _clarification_questions(prescription)
    return {
        "version": SEARCH_TIERS_VERSION,
        "tier": "l3",
        "research_question": prescription.get("research_question", ""),
        "clarification_questions": clarifications,
        "subquestions": subquestions,
        "languages": ["en", "zh"],
        "source_assignment": {
            "en": ["openalex_api (L2 layer)", "crossref (verification)", "web search (agent-side)"],
            "zh": ["cnki_query_cards (browser-side, reflow via `search ingest`)", "policy-text web search (gov sites)"],
        },
        "source_whitelist_note": "无 Sci-Hub 类 workflow；WoS Expanded/Scopus 仅在用户提供 license key 时启用。",
        "budgets": {
            "max_rounds": DEFAULT_MAX_ROUNDS,
            "max_api_calls": DEFAULT_MAX_CALLS,
            "time_budget_seconds": DEFAULT_TIME_BUDGET_SECONDS,
        },
        "confirmation_required": True,
    }


def _subquestions(prescription: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = prescription.get("concept_blocks", [])
    required = [block for block in blocks if block.get("required")] or blocks[:2]
    optional = [block for block in blocks if not block.get("required")]
    subquestions: list[dict[str, Any]] = []

    def terms(block: dict[str, Any], language: str, limit: int = 3) -> list[str]:
        bucket = block.get("terms_en" if language == "en" else "terms_zh") or []
        ordered = [item["term"] for item in bucket if item.get("required")] + [
            item["term"] for item in bucket if not item.get("required")
        ]
        return ordered[:limit]

    if len(required) >= 2:
        core_en = [terms(block, "en") for block in required]
        core_zh = [terms(block, "zh") for block in required]
        subquestions.append(
            {
                "id": "sq_core_effect",
                "question": "核心效应：处理对结果变量的因果证据有哪些？",
                "queries_en": [" ".join(group[0] for group in core_en if group)] if all(core_en) else [],
                "queries_zh": [" ".join(group[0] for group in core_zh if group)] if all(core_zh) else [],
                "variant_terms_en": [term for group in core_en for term in group[1:]],
                "variant_terms_zh": [term for group in core_zh for term in group[1:]],
            }
        )
    for block in optional:
        en_terms = terms(block, "en")
        zh_terms = terms(block, "zh")
        anchor_en = terms(required[0], "en") if required else []
        anchor_zh = terms(required[0], "zh") if required else []
        subquestions.append(
            {
                "id": f"sq_{block.get('id', 'block')}",
                "question": f"{block.get('label', block.get('id'))} 维度的相关文献与方法争论。",
                "queries_en": [f"{anchor_en[0]} {en_terms[0]}"] if anchor_en and en_terms else [],
                "queries_zh": [f"{anchor_zh[0]} {zh_terms[0]}"] if anchor_zh and zh_terms else [],
                "variant_terms_en": en_terms[1:],
                "variant_terms_zh": zh_terms[1:],
            }
        )
    if not subquestions and required:
        block = required[0]
        subquestions.append(
            {
                "id": "sq_core_topic",
                "question": "主题综览：该政策/现象的核心文献。",
                "queries_en": terms(block, "en", 1),
                "queries_zh": terms(block, "zh", 1),
                "variant_terms_en": terms(block, "en")[1:],
                "variant_terms_zh": terms(block, "zh")[1:],
            }
        )
    return subquestions


def _clarification_questions(prescription: dict[str, Any]) -> list[str]:
    questions: list[str] = []
    if not prescription.get("year_range"):
        questions.append("时间窗：综述覆盖哪一年份区间？（影响每个源的年份过滤）")
    blocks = prescription.get("concept_blocks", [])
    if not any(block.get("id") == "population" for block in blocks):
        questions.append("地域/对象范围：只看中国证据，还是中外对照？")
    if not any(block.get("id") == "identification" for block in blocks):
        questions.append("方法范围：只收因果识别类研究，还是包含相关性/结构模型？")
    questions.append("综述用途：投稿前系统定位、开题摸底，还是回应审稿人？（决定饱和标准）")
    return questions[:4]


# ---------------------------------------------------------------------------
# Phase B + C: fan-out loop and synthesis
# ---------------------------------------------------------------------------

def run_deep_search(
    *,
    prescription: dict[str, Any],
    plan_confirmed: bool = False,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_calls: int = DEFAULT_MAX_CALLS,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
    extra_records_paths: list[str | Path] | None = None,
    clock: Any = time.monotonic,
) -> DeepSearchResult:
    result = DeepSearchResult()
    result.plan = build_deep_search_plan(prescription)
    result.plan["budgets"] = {
        "max_rounds": max_rounds,
        "max_api_calls": max_calls,
        "time_budget_seconds": time_budget_seconds,
    }
    if not plan_confirmed:
        result.stop_reason = "awaiting_plan_confirmation"
        result.status = "awaiting_plan_confirmation"
        result.add_issue(
            "plan_not_confirmed",
            "flag",
            "Deep search burns budget only after the plan is confirmed; review the plan and re-run with --confirm-plan.",
        )
        return result
    if offline:
        result.stop_reason = "offline_not_allowed"
        result.add_issue(
            "offline_not_allowed",
            "hard_block",
            "Confirmed L3 deep search requires live source access; offline mode only supports plan review.",
        )
        return result

    try:
        _run_loop(
            result,
            prescription,
            fetcher=fetcher,
            offline=offline,
            mailto=mailto,
            max_rounds=max_rounds,
            max_calls=max_calls,
            time_budget_seconds=time_budget_seconds,
            extra_records_paths=extra_records_paths or [],
            clock=clock,
        )
    except Exception as exc:
        result.stop_reason = result.stop_reason or "internal_error"
        result.add_issue(
            "deep_search_failed",
            "hard_block",
            f"Deep search stopped after an internal error ({exc}); no substitute result is claimed.",
        )
    return result


def _run_loop(
    result: DeepSearchResult,
    prescription: dict[str, Any],
    *,
    fetcher: Fetcher | None,
    offline: bool,
    mailto: str | None,
    max_rounds: int,
    max_calls: int,
    time_budget_seconds: float,
    extra_records_paths: list[str | Path],
    clock: Any,
) -> None:
    start = clock()
    subquestions = result.plan["subquestions"]
    hits: dict[str, dict[str, list[BibRecord]]] = {
        sq["id"]: {"en": [], "zh": []} for sq in subquestions
    }
    pending_en: dict[str, list[str]] = {sq["id"]: list(sq["queries_en"]) for sq in subquestions}
    zh_cards: dict[str, list[str]] = {sq["id"]: list(sq["queries_zh"]) for sq in subquestions}

    # Chinese-side reflow: CNKI/Wanfang exports fed in between rounds.
    extra_records: list[BibRecord] = []
    for raw_path in extra_records_paths:
        path = Path(raw_path)
        if not path.exists():
            result.add_issue("missing_extra_records", "flag", f"Extra records file does not exist: {path}")
            continue
        extra_records.extend(parse_records_file(path.read_text(encoding="utf-8-sig"), path.name))

    stop_reason = "saturated"
    for round_index in range(max_rounds):
        if clock() - start > time_budget_seconds:
            stop_reason = "time_budget"
            break
        if result.api_calls_used >= max_calls:
            stop_reason = "api_call_budget"
            break
        round_queries = {sq_id: queries for sq_id, queries in pending_en.items() if queries}
        if not round_queries and round_index > 0:
            stop_reason = "saturated"
            break
        ran_any = False
        for sq_id, queries in round_queries.items():
            if result.api_calls_used >= max_calls:
                stop_reason = "api_call_budget"
                break
            search = run_open_search(
                queries=queries,
                fetcher=fetcher,
                offline=offline,
                mailto=mailto,
                max_calls=max_calls - result.api_calls_used,
            )
            ran_any = True
            result.api_calls_used += search.api_calls_used
            if search.has_hard_blocks:
                result.stop_reason = search.stop_reason or "l2_boundary"
                for issue in search.issues:
                    if issue.severity == "hard_block":
                        result.add_issue(
                            "l2_boundary",
                            "hard_block",
                            f"Subquestion `{sq_id}` hit an L2 boundary: {issue.message}",
                        )
                return
            for record in search.records:
                record.extra_fields.setdefault("subquestion", sq_id)
            hits[sq_id]["en"].extend(search.records)
            pending_en[sq_id] = []
        result.rounds_run = round_index + 1
        if not ran_any:
            stop_reason = "saturated"
            break
        # Gap-driven refinement: zero-hit cells get remaining term variants next round.
        for sq in subquestions:
            sq_id = sq["id"]
            if not hits[sq_id]["en"] and sq.get("variant_terms_en") and not pending_en[sq_id]:
                variants = sq["variant_terms_en"][:2]
                if variants:
                    pending_en[sq_id] = [" ".join(variants)]
                    sq["variant_terms_en"] = sq["variant_terms_en"][2:]
    else:
        stop_reason = "round_budget"
    result.stop_reason = stop_reason

    # Assign reflowed Chinese-side records to subquestions by term match.
    for record in extra_records:
        assigned = False
        for sq in subquestions:
            terms = [term for query in sq["queries_zh"] for term in query.split()] + sq.get("variant_terms_zh", [])
            if any(term and term in record.title for term in terms):
                record.extra_fields.setdefault("subquestion", sq["id"])
                hits[sq["id"]]["zh" if record.language == "zh" else "en"].append(record)
                assigned = True
                break
        if not assigned and subquestions:
            record.extra_fields.setdefault("subquestion", subquestions[0]["id"])
            hits[subquestions[0]["id"]]["zh" if record.language == "zh" else "en"].append(record)

    # Cross-language dedupe and synthesis.
    all_records = [record for per_sq in hits.values() for bucket in per_sq.values() for record in bucket]
    deduped, _merges = dedupe_records(all_records)
    assign_citekeys(deduped)
    result.records = deduped
    result.notes = [
        structured_note_skeleton(
            record,
            created_by="econpaper_search_l3_deep",
            what_it_did=(f"[ABSTRACT EXCERPT, unverified] {record.abstract.strip()[:600]}" if record.abstract.strip() else None),
            confidence="low",
        )
        for record in deduped
    ]
    result.coverage_matrix = _coverage_matrix(subquestions, hits, zh_cards, offline)


def _coverage_matrix(
    subquestions: list[dict[str, Any]],
    hits: dict[str, dict[str, list[BibRecord]]],
    zh_cards: dict[str, list[str]],
    offline: bool,
) -> list[dict[str, Any]]:
    matrix: list[dict[str, Any]] = []
    for sq in subquestions:
        sq_id = sq["id"]
        for language in ("en", "zh"):
            count = len(hits[sq_id][language])
            cell: dict[str, Any] = {"subquestion": sq_id, "language": language, "hits": count}
            if count == 0:
                if language == "zh":
                    cards = zh_cards.get(sq_id, [])
                    cell["explanation"] = (
                        "中文侧无开放 API：需浏览器侧执行 CNKI query 卡后经 `search ingest` 回流。"
                        + (f" 待执行 query：{'；'.join(cards)}" if cards else " 该子问题缺中文术语，先补术语表。")
                    )
                    cell["action_needed"] = "manual_cnki_execution" if cards else "supply_zh_terms"
                elif offline:
                    cell["explanation"] = "离线运行未触发英文 API 检索。"
                    cell["action_needed"] = "rerun_online"
                else:
                    cell["explanation"] = "英文侧零命中：要么该方向确属文献空白，要么需要换术语补搜。"
                    cell["action_needed"] = "confirm_gap_or_research"
            matrix.append(cell)
    return matrix


# ---------------------------------------------------------------------------
# Output pack
# ---------------------------------------------------------------------------

def write_deep_search_pack(
    *,
    out_dir: str | Path,
    prescription_path: str | Path,
    plan_confirmed: bool = False,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    max_calls: int = DEFAULT_MAX_CALLS,
    time_budget_seconds: float = DEFAULT_TIME_BUDGET_SECONDS,
    extra_records_paths: list[str | Path] | None = None,
) -> DeepSearchResult:
    path = Path(prescription_path)
    if not path.exists():
        result = DeepSearchResult()
        result.add_issue("missing_prescription", "hard_block", f"Prescription file does not exist: {path}")
        return result
    prescription = json.loads(path.read_text(encoding="utf-8-sig"))
    result = run_deep_search(
        prescription=prescription,
        plan_confirmed=plan_confirmed,
        fetcher=fetcher,
        offline=offline,
        mailto=mailto,
        max_rounds=max_rounds,
        max_calls=max_calls,
        time_budget_seconds=time_budget_seconds,
        extra_records_paths=extra_records_paths,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (out_path / PLAN_FILENAME).write_text(
        json.dumps(result.plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_path / PLAN_REPORT_FILENAME).write_text(_plan_markdown(result.plan), encoding="utf-8")
    (internal / "deep_search_report.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if result.records:
        (out_path / "refs.bib").write_text(records_to_bibtex(result.records), encoding="utf-8")
        (out_path / "external_literature_notes.json").write_text(
            json.dumps(result.notes, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        memo = build_evidence_memo(result)
        _assert_every_line_sourced(memo)
        (out_path / MEMO_FILENAME).write_text(memo, encoding="utf-8")
    return result


def build_evidence_memo(result: DeepSearchResult) -> str:
    """Evidence memo skeleton: every claim line carries a source identifier.

    This is author input for `literature_notes.md`, never manuscript prose;
    Related Literature is still generated from structured notes downstream.
    """
    lines = [
        "# EVIDENCE MEMO (L3 综述底稿 — 作者输入，非正文)",
        "",
        f"<!-- 状态：{result.stop_reason}; 轮次 {result.rounds_run}; API 调用 {result.api_calls_used} -->",
        "",
        "## 候选证据（按子问题组织，逐条挂源）",
        "",
    ]
    sq_lookup = {sq["id"]: sq["question"] for sq in result.plan.get("subquestions", [])}
    first_sq = next(iter(sq_lookup), "")
    for sq_id, question in sq_lookup.items():
        lines.append(f"### {sq_id}: {question}")
        lines.append("")
        cell_records = [
            record
            for record in result.records
            if record.extra_fields.get("subquestion", first_sq) == sq_id
        ]
        listed = 0
        for record in cell_records:
            source_id = record.doi or record.extra_fields.get("openalex_id") or record.url or record.source_file
            if not source_id:
                continue
            excerpt = record.abstract.strip()[:200]
            suffix = f" — {excerpt}" if excerpt else ""
            lines.append(f"- [{record.key}] {record.title} ({record.year or 'n.d.'}){suffix} [src:{source_id}]")
            listed += 1
            if listed >= 10:
                break
        if listed == 0:
            lines.append(f"- （无已挂源候选；见覆盖审计矩阵） [src:coverage_matrix:{sq_id}]")
        lines.append("")
    lines.extend(["## 矛盾点与文献空白（待作者确认）", ""])
    for cell in result.coverage_matrix:
        if cell.get("hits", 0) == 0:
            lines.append(
                f"- 空白：`{cell['subquestion']}` × `{cell['language']}` — {cell['explanation']} "
                f"[src:coverage_matrix:{cell['subquestion']}]"
            )
    lines.extend(
        [
            "",
            "## 检索完整性自查（覆盖审计）",
            "",
            "| 子问题 | 语言 | 命中数 | 空格子处理 |",
            "|---|---|---|---|",
        ]
    )
    for cell in result.coverage_matrix:
        explanation = cell.get("explanation", "—")
        lines.append(f"| {cell['subquestion']} | {cell['language']} | {cell['hits']} | {explanation} |")
    return "\n".join(lines) + "\n"


def _assert_every_line_sourced(memo: str) -> None:
    """Grok-style rule: no unsourced claim bullet may appear in the memo."""
    for line in memo.splitlines():
        if line.startswith("- ") and "[src:" not in line:
            raise AssertionError(f"Evidence memo bullet without a source identifier: {line}")


def _plan_markdown(plan: dict[str, Any]) -> str:
    lines = [
        "# DEEP SEARCH PLAN (L3)",
        "",
        f"研究问题：{plan.get('research_question') or AUTHOR_INPUT_NEEDED}",
        "",
        "## 开跑前澄清问题（请逐条回答后 --confirm-plan）",
        "",
    ]
    lines.extend(f"{index}. {question}" for index, question in enumerate(plan["clarification_questions"], start=1))
    lines.extend(["", "## 子问题分解与双语检索分工", ""])
    for sq in plan["subquestions"]:
        lines.append(f"### {sq['id']}: {sq['question']}")
        lines.append("")
        lines.append(f"- 英文 query：{'；'.join(sq['queries_en']) if sq['queries_en'] else '（缺英文术语）'}")
        lines.append(f"- 中文 query：{'；'.join(sq['queries_zh']) if sq['queries_zh'] else '（缺中文术语）'}")
        lines.append("")
    budgets = plan["budgets"]
    lines.extend(
        [
            "## 预算三闸",
            "",
            f"- 轮次上限：{budgets['max_rounds']}",
            f"- API 调用上限：{budgets['max_api_calls']}",
            f"- 时间硬停：{budgets['time_budget_seconds']} 秒",
            "",
            f"## 源白名单\n\n- {plan['source_whitelist_note']}",
            "",
        ]
    )
    return "\n".join(lines) + "\n"
