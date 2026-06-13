"""Paper Store: local landing zone for legally obtained full texts.

Layout (one folder per citekey, the same primary key as refs.bib and
structured notes):

    paper_store/
      chen2021lowcarbon/
        中文短题_English-Short-Title.pdf
        paper.md            # LLM-readable full text (converted externally)
        paper.struct.json   # outline / section offsets / table+figure inventory
        meta.json           # record + source URL + retrieval time + converter info

Conversion (PDF -> Markdown) is delegated to external tools (MinerU / Marker /
PyMuPDF); the store records which tool produced `paper.md`. A paper without a
text layer is recorded explicitly as `pdf_no_text_layer` or `bibrecord_only` so
downstream readers cannot mistake it for full-text evidence.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import SEARCH_TIERS_VERSION

META_FILENAME = "meta.json"
PAPER_MD_FILENAME = "paper.md"
STRUCT_FILENAME = "paper.struct.json"

_SHORT_TITLE_MAX_CHARS = 40
_MAX_PATH_LENGTH = 259  # Windows MAX_PATH guard
_CITEKEY_PATTERN = re.compile(r"^[a-z0-9_-]+$")


@dataclass
class PaperStoreIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class PaperStoreResult:
    citekey: str = ""
    paper_dir: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    status: str = "passed"
    issues: list[PaperStoreIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(PaperStoreIssue(code=code, severity=severity, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "citekey": self.citekey,
            "paper_dir": self.paper_dir,
            "meta": self.meta,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def add_paper(
    store_dir: str | Path,
    *,
    citekey: str,
    title_en: str = "",
    title_zh: str = "",
    pdf_path: str | Path | None = None,
    paper_md_path: str | Path | None = None,
    source_url: str = "",
    license_note: str = "",
    converter: str = "",
    converter_version: str = "",
    bib_fields: dict[str, Any] | None = None,
    machine_translated_titles: dict[str, str] | None = None,
) -> PaperStoreResult:
    result = PaperStoreResult(citekey=citekey)
    if not _CITEKEY_PATTERN.fullmatch(citekey):
        result.add_issue(
            "invalid_citekey",
            "hard_block",
            f"citekey `{citekey}` must be stable ASCII (lowercase letters, digits, _ or -): it is the primary key.",
        )
        return result
    if not title_en and not title_zh:
        result.add_issue("missing_titles", "hard_block", "At least one of title_en / title_zh is required.")
        return result

    store = Path(store_dir)
    paper_dir = store / citekey
    paper_dir.mkdir(parents=True, exist_ok=True)
    result.paper_dir = str(paper_dir)

    files: dict[str, str | None] = {"pdf": None, "paper_md": None, "struct": None}

    if pdf_path is not None:
        source_pdf = Path(pdf_path)
        if not source_pdf.exists():
            result.add_issue("missing_pdf", "hard_block", f"PDF does not exist: {source_pdf}")
            return result
        pdf_name = _pdf_filename(title_zh, title_en, paper_dir)
        shutil.copyfile(source_pdf, paper_dir / pdf_name)
        files["pdf"] = pdf_name

    struct: dict[str, Any] | None = None
    if paper_md_path is not None:
        source_md = Path(paper_md_path)
        if not source_md.exists():
            result.add_issue("missing_paper_md", "hard_block", f"paper.md source does not exist: {source_md}")
            return result
        markdown_text = source_md.read_text(encoding="utf-8-sig")
        (paper_dir / PAPER_MD_FILENAME).write_text(markdown_text, encoding="utf-8")
        files["paper_md"] = PAPER_MD_FILENAME
        struct = build_struct(markdown_text)
        (paper_dir / STRUCT_FILENAME).write_text(
            json.dumps(struct, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        files["struct"] = STRUCT_FILENAME

    if files["paper_md"]:
        status = "full_text"
    elif files["pdf"]:
        status = "pdf_no_text_layer"
        result.add_issue(
            "no_text_layer",
            "flag",
            "PDF landed without an LLM-readable text layer; convert with MinerU/Marker and re-add. "
            "Structured notes for this paper stay at abstract-level confidence.",
        )
    else:
        status = "bibrecord_only"

    meta = {
        "version": SEARCH_TIERS_VERSION,
        "citekey": citekey,
        "title_zh": title_zh,
        "title_en": title_en,
        "machine_translated_titles": machine_translated_titles or {},
        "source_url": source_url,
        "license_note": license_note,
        "retrieved_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "converter": {"tool": converter, "version": converter_version},
        "files": files,
        "status": status,
        "bib_fields": bib_fields or {},
        "section_count": len(struct["outline"]) if struct else 0,
    }
    (paper_dir / META_FILENAME).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    result.meta = meta
    return result


def _short_title(title: str) -> str:
    text = unicodedata.normalize("NFKC", title)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:_SHORT_TITLE_MAX_CHARS].rstrip("-_.")


def _pdf_filename(title_zh: str, title_en: str, paper_dir: Path) -> str:
    parts = [part for part in (_short_title(title_zh), _short_title(title_en)) if part]
    name = "_".join(parts) + ".pdf"
    # Keep the full path inside the Windows MAX_PATH limit; full titles live in meta.json.
    overshoot = len(str(paper_dir / name)) - _MAX_PATH_LENGTH
    if overshoot > 0:
        stem = name[: -len(".pdf")]
        name = stem[: max(8, len(stem) - overshoot)] + ".pdf"
    return name


# ---------------------------------------------------------------------------
# Structure cache (paper.struct.json)
# ---------------------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_SECTION_NUMBER = re.compile(r"^(\d+(?:\.\d+)*)[.)]?\s+")


def build_struct(markdown_text: str) -> dict[str, Any]:
    lines = markdown_text.splitlines()
    outline: list[dict[str, Any]] = []
    for line_index, line in enumerate(lines):
        match = _HEADING.match(line)
        if not match:
            continue
        title = match.group(2).strip()
        number_match = _SECTION_NUMBER.match(title)
        anchor = number_match.group(1) if number_match else _slug(title)
        outline.append(
            {
                "anchor": anchor,
                "title": title,
                "level": len(match.group(1)),
                "line_start": line_index,
                "line_end": len(lines),
            }
        )
    for index, section in enumerate(outline):
        for later in outline[index + 1 :]:
            if later["level"] <= section["level"]:
                section["line_end"] = later["line_start"]
                break
    tables = [
        {"line_start": start, "line_end": end}
        for start, end in _pipe_table_spans(lines)
    ]
    figures = [
        {"line": line_index, "text": line.strip()[:120]}
        for line_index, line in enumerate(lines)
        if re.match(r"^\s*(!\[|figure\s+\d|图\s*\d)", line, flags=re.IGNORECASE)
    ]
    return {
        "version": SEARCH_TIERS_VERSION,
        "line_count": len(lines),
        "outline": outline,
        "tables": tables,
        "figures": figures,
    }


def _pipe_table_spans(lines: list[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for line_index, line in enumerate(lines):
        is_row = line.strip().startswith("|") and line.strip().endswith("|")
        if is_row and start is None:
            start = line_index
        elif not is_row and start is not None:
            if line_index - start >= 2:
                spans.append((start, line_index))
            start = None
    if start is not None and len(lines) - start >= 2:
        spans.append((start, len(lines)))
    return spans


def _slug(title: str) -> str:
    text = unicodedata.normalize("NFKC", title).lower()
    text = re.sub(r"[^0-9a-z一-鿿]+", "-", text)
    return text.strip("-")[:60] or "section"


# ---------------------------------------------------------------------------
# Reading interface: outline / read section / search (never swallow whole PDFs)
# ---------------------------------------------------------------------------

def load_meta(store_dir: str | Path, citekey: str) -> dict[str, Any] | None:
    meta_path = Path(store_dir) / citekey / META_FILENAME
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def list_papers(store_dir: str | Path) -> list[dict[str, Any]]:
    store = Path(store_dir)
    papers = []
    if not store.exists():
        return papers
    for child in sorted(store.iterdir()):
        if child.is_dir() and (child / META_FILENAME).exists():
            meta = json.loads((child / META_FILENAME).read_text(encoding="utf-8"))
            papers.append(
                {
                    "citekey": meta.get("citekey", child.name),
                    "status": meta.get("status", "unknown"),
                    "title_en": meta.get("title_en", ""),
                    "title_zh": meta.get("title_zh", ""),
                }
            )
    return papers


def outline(store_dir: str | Path, citekey: str) -> list[dict[str, Any]]:
    struct_path = Path(store_dir) / citekey / STRUCT_FILENAME
    if not struct_path.exists():
        return []
    struct = json.loads(struct_path.read_text(encoding="utf-8"))
    return struct.get("outline", [])


def read_section(store_dir: str | Path, citekey: str, section: str) -> dict[str, Any] | None:
    """Read one section by anchor (`5.2`), title substring, or `citekey#anchor` ref."""
    if "#" in section:
        _, _, section = section.partition("#")
    paper_dir = Path(store_dir) / citekey
    md_path = paper_dir / PAPER_MD_FILENAME
    if not md_path.exists():
        return None
    sections = outline(store_dir, citekey)
    wanted = section.strip().lower()
    chosen = None
    for candidate in sections:
        if str(candidate["anchor"]).lower() == wanted:
            chosen = candidate
            break
    if chosen is None:
        for candidate in sections:
            if wanted in str(candidate["title"]).lower():
                chosen = candidate
                break
    if chosen is None:
        return None
    lines = md_path.read_text(encoding="utf-8").splitlines()
    text = "\n".join(lines[chosen["line_start"] : chosen["line_end"]])
    return {
        "citekey": citekey,
        "anchor": f"{citekey}#{chosen['anchor']}",
        "title": chosen["title"],
        "text": text,
    }


def search_store(
    store_dir: str | Path,
    query: str,
    *,
    context_chars: int = 160,
    max_hits: int = 20,
) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    needle = query.lower()
    for paper in list_papers(store_dir):
        citekey = paper["citekey"]
        md_path = Path(store_dir) / citekey / PAPER_MD_FILENAME
        if not md_path.exists():
            continue
        text = md_path.read_text(encoding="utf-8")
        lower = text.lower()
        sections = outline(store_dir, citekey)
        line_offsets = _line_offsets(text)
        position = 0
        while len(hits) < max_hits:
            found = lower.find(needle, position)
            if found < 0:
                break
            start = max(0, found - context_chars)
            end = min(len(text), found + len(query) + context_chars)
            hits.append(
                {
                    "citekey": citekey,
                    "anchor": _anchor_for_offset(found, sections, line_offsets, citekey),
                    "context": text[start:end].replace("\n", " "),
                }
            )
            position = found + len(query)
        if len(hits) >= max_hits:
            break
    return hits


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for line in text.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def _anchor_for_offset(offset: int, sections: list[dict[str, Any]], line_offsets: list[int], citekey: str) -> str:
    line_number = 0
    for index, start in enumerate(line_offsets):
        if start > offset:
            line_number = index - 1
            break
    else:
        line_number = len(line_offsets) - 1
    current = ""
    for section in sections:
        if section["line_start"] <= line_number:
            current = section["anchor"]
        else:
            break
    return f"{citekey}#{current}" if current else citekey
