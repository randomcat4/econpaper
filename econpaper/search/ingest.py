"""L1 reflow interface: ingest user-collected records into the citation-safe path.

Takes RIS/BibTeX/CSV exports (GS, WoS, CNKI, Zotero), dedupes, writes a
normalized `refs.bib`, and emits a structured-notes skeleton in which
`what_it_did` / `relation_to_this_paper` stay `[AUTHOR_INPUT_NEEDED]` until the
author fills them. L1 never writes literature prose (03 hard rule).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..intake import AUTHOR_INPUT_NEEDED
from . import SEARCH_TIERS_VERSION
from .records import (
    BibRecord,
    assign_citekeys,
    dedupe_records,
    parse_records_file,
    records_to_bibtex,
    to_bibtex,
)

NOTES_FILENAME = "external_literature_notes.json"
REFS_FILENAME = "refs.bib"


@dataclass
class IngestIssue:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "path": self.path}


@dataclass
class IngestResult:
    records: list[BibRecord] = field(default_factory=list)
    merges: list[dict[str, Any]] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    status: str = "passed"
    issues: list[IngestIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, path: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(IngestIssue(code=code, severity=severity, message=message, path=path))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "record_count": len(self.records),
            "merged_duplicates": self.merges,
            "records": [record.to_dict() for record in self.records],
            "issues": [issue.to_dict() for issue in self.issues],
        }


def ingest_records(input_paths: list[str | Path], *, created_by: str = "author_l1_reflow") -> IngestResult:
    result = IngestResult()
    raw_records: list[BibRecord] = []
    for raw_path in input_paths:
        path = Path(raw_path)
        if not path.exists():
            result.add_issue("missing_input_file", "hard_block", f"Input file does not exist: {path}", str(path))
            continue
        text = _read_tolerant(path, result)
        if text is None:
            continue
        parsed = parse_records_file(text, path.name)
        if not parsed:
            result.add_issue(
                "no_records_parsed",
                "flag",
                f"No bibliographic records were parsed from {path.name}; check the export format.",
                str(path),
            )
            continue
        raw_records.extend(parsed)
    if not raw_records:
        if not result.has_hard_blocks:
            result.add_issue("no_records", "hard_block", "No records were parsed from any input file.")
        return result
    records, merges = dedupe_records(raw_records)
    assign_citekeys(records)
    result.records = records
    result.merges = merges
    result.notes = [structured_note_skeleton(record, created_by=created_by) for record in records]
    return result


def write_ingest_pack(
    input_paths: list[str | Path],
    *,
    out_dir: str | Path,
    created_by: str = "author_l1_reflow",
) -> IngestResult:
    result = ingest_records(input_paths, created_by=created_by)
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    if result.records:
        (out_path / REFS_FILENAME).write_text(records_to_bibtex(result.records), encoding="utf-8")
        (out_path / NOTES_FILENAME).write_text(
            json.dumps(result.notes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (out_path / "INGEST_REPORT.md").write_text(_ingest_report(result), encoding="utf-8")
    (internal / "search_ingest_report.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def structured_note_skeleton(
    record: BibRecord,
    *,
    created_by: str,
    what_it_did: str | None = None,
    confidence: str = "low",
) -> dict[str, Any]:
    """Structured note per the 03 external-literature contract.

    A skeleton note is `needs_author_input` until the author supplies
    `what_it_did` / `relation_to_this_paper`; fake summaries are never
    generated to fill the gap.
    """
    if record.doi:
        source_identifier, source_type = record.doi, "doi"
    elif record.url:
        source_identifier, source_type = record.url, "url"
    else:
        source_identifier, source_type = record.source_file or "author_supplied_record", "manual"
    filled = bool(what_it_did and what_it_did.strip())
    return {
        "paper_key": record.key,
        "bibtex_entry": to_bibtex(record),
        "what_it_did": what_it_did.strip() if filled else f"{AUTHOR_INPUT_NEEDED}: 一句话概括该文做了什么",
        "relation_to_this_paper": f"{AUTHOR_INPUT_NEEDED}: 本文与该文的关系/差异",
        "source_url_or_doi": source_identifier,
        "source_type": source_type,
        "created_by": created_by,
        "confidence": confidence if filled else "low",
        "status": "abstract_excerpt_unconfirmed" if filled else "needs_author_input",
        "language": record.language or "en",
    }


def _read_tolerant(path: Path, result: IngestResult) -> str | None:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    result.add_issue(
        "undecodable_input",
        "hard_block",
        f"Could not decode {path.name} as UTF-8 or GB18030; re-export with UTF-8 encoding.",
        str(path),
    )
    return None


def _ingest_report(result: IngestResult) -> str:
    zh_count = sum(1 for record in result.records if record.language == "zh")
    lines = [
        "# INGEST REPORT (L1 回流)",
        "",
        f"- 纳入题录：`{len(result.records)}`（中文 `{zh_count}` / 其他 `{len(result.records) - zh_count}`）",
        f"- 合并重复：`{len(result.merges)}`",
        f"- 输出：`{REFS_FILENAME}`（规范化）与 `{NOTES_FILENAME}`（notes 骨架）",
        "",
        "## 下一步（作者必做）",
        "",
        f"- 为每条 note 填写 `what_it_did` 与 `relation_to_this_paper`；骨架值为 `{AUTHOR_INPUT_NEEDED}`，",
        "  未填写的 note 不会被写作链当作文献支撑使用。",
        "- 如需引用核验与元数据补全，运行 `econpaper search verify --refs refs.bib --out <dir>`。",
        "",
        "## 题录清单",
        "",
        "| citekey | 年份 | 语言 | 题名 |",
        "|---|---|---|---|",
    ]
    for record in sorted(result.records, key=lambda item: item.key):
        lines.append(f"| `{record.key}` | {record.year or '—'} | {record.language or 'en'} | {record.title} |")
    if result.merges:
        lines.extend(["", "## 合并明细", ""])
        for merge in result.merges:
            lines.append(
                f"- 按 `{merge['match_on']}` 合并：保留《{merge['kept_title']}》，丢弃来自 "
                f"`{merge['dropped_source']}` 的重复条目。"
            )
    if result.issues:
        lines.extend(["", "## 问题", ""])
        for issue in result.issues:
            lines.append(f"- `{issue.code}` ({issue.severity}): {issue.message}")
    return "\n".join(lines) + "\n"
