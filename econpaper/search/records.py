"""Shared bibliographic record handling for the search tiers.

Tolerant parsing of BibTeX / RIS / CSV exports (including dirty CNKI and
Google Scholar exports), stable ASCII citekey generation, DOI/title-based
deduplication, and normalized BibTeX emission.
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


_DOI_PATTERN = re.compile(r"10\.\d{4,9}/[^\s\"'<>{}]+", re.IGNORECASE)
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "how", "in", "into", "is", "it", "of", "on", "or", "the", "their", "this",
    "to", "what", "when", "with",
}


@dataclass
class BibRecord:
    key: str = ""
    entry_type: str = "article"
    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: str = ""
    journal: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    language: str = ""
    extra_fields: dict[str, str] = field(default_factory=dict)
    source_file: str = ""
    source_format: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "entry_type": self.entry_type,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "volume": self.volume,
            "number": self.number,
            "pages": self.pages,
            "doi": self.doi,
            "url": self.url,
            "abstract": self.abstract,
            "language": self.language,
            "source_file": self.source_file,
            "source_format": self.source_format,
        }


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip()
    text = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)\s*", "", text, flags=re.IGNORECASE)
    match = _DOI_PATTERN.search(text)
    return match.group(0).rstrip(".,;)") .lower() if match else ""


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).lower()
    text = re.sub(r"[^0-9a-z一-鿿]+", " ", text)
    return " ".join(text.split())


def contains_cjk(text: str) -> bool:
    return any("一" <= char <= "鿿" for char in text)


def _ascii_slug(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def make_citekey(record: BibRecord, taken: set[str] | None = None) -> str:
    author_slug = ""
    if record.authors:
        family = re.split(r"[,\s]+", record.authors[0].strip())[0]
        author_slug = _ascii_slug(family)
    if not author_slug:
        author_slug = "ref"
    year = record.year if re.fullmatch(r"\d{4}", record.year or "") else ""
    title_word = ""
    for word in normalize_title(record.title).split():
        slug = _ascii_slug(word)
        if len(slug) >= 3 and slug not in _STOPWORDS:
            title_word = slug[:12]
            break
    if not title_word:
        digest_source = normalize_title(record.title) or record.doi or record.url or repr(record.authors)
        title_word = hashlib.sha1(digest_source.encode("utf-8")).hexdigest()[:6]
    base = f"{author_slug}{year}{title_word}"
    if taken is None:
        return base
    candidate = base
    suffix_index = 0
    while candidate in taken:
        suffix_index += 1
        candidate = base + chr(ord("a") + (suffix_index - 1) % 26) * (1 + (suffix_index - 1) // 26)
    taken.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# BibTeX parsing
# ---------------------------------------------------------------------------

def parse_bibtex(text: str, *, source_file: str = "") -> list[BibRecord]:
    records: list[BibRecord] = []
    for entry_type, key, body in _iter_bibtex_entries(text):
        if entry_type.lower() in {"comment", "preamble", "string"}:
            continue
        fields = _parse_bibtex_fields(body)
        record = BibRecord(
            key=key.strip(),
            entry_type=entry_type.lower(),
            title=_strip_braces(fields.get("title", "")),
            authors=_split_authors(_strip_braces(fields.get("author", ""))),
            year=_extract_year(fields.get("year", "") or fields.get("date", "")),
            journal=_strip_braces(fields.get("journal", "") or fields.get("booktitle", "")),
            volume=_strip_braces(fields.get("volume", "")),
            number=_strip_braces(fields.get("number", "")),
            pages=_strip_braces(fields.get("pages", "")),
            doi=normalize_doi(fields.get("doi", "") or fields.get("url", "")),
            url=_strip_braces(fields.get("url", "")),
            abstract=_strip_braces(fields.get("abstract", "")),
            language=_strip_braces(fields.get("language", "")),
            source_file=source_file,
            source_format="bibtex",
        )
        known = {
            "title", "author", "year", "date", "journal", "booktitle", "volume",
            "number", "pages", "doi", "url", "abstract", "language",
        }
        record.extra_fields = {
            name: _strip_braces(value) for name, value in fields.items() if name not in known
        }
        if not record.language and contains_cjk(record.title):
            record.language = "zh"
        records.append(record)
    return records


def _iter_bibtex_entries(text: str):
    index = 0
    while True:
        at = text.find("@", index)
        if at < 0:
            return
        match = re.match(r"@\s*(\w+)\s*[{(]", text[at:])
        if not match:
            index = at + 1
            continue
        entry_type = match.group(1)
        open_char = text[at + match.end() - 1]
        close_char = "}" if open_char == "{" else ")"
        depth = 1
        pos = at + match.end()
        start = pos
        while pos < len(text) and depth > 0:
            char = text[pos]
            if char == open_char or (open_char == "{" and char == "{"):
                depth += 1
            elif char == close_char or (open_char == "{" and char == "}"):
                depth -= 1
            pos += 1
        body = text[start : pos - 1]
        key, _, rest = body.partition(",")
        yield entry_type, key, rest
        index = pos


def _parse_bibtex_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    pos = 0
    length = len(body)
    while pos < length:
        match = re.compile(r"\s*(\w[\w-]*)\s*=\s*").match(body, pos)
        if not match:
            pos += 1
            continue
        name = match.group(1).lower()
        pos = match.end()
        if pos >= length:
            break
        char = body[pos]
        if char == "{":
            depth = 1
            pos += 1
            start = pos
            while pos < length and depth > 0:
                if body[pos] == "{":
                    depth += 1
                elif body[pos] == "}":
                    depth -= 1
                pos += 1
            value = body[start : pos - 1]
        elif char == '"':
            pos += 1
            start = pos
            while pos < length and body[pos] != '"':
                pos += 1
            value = body[start:pos]
            pos += 1
        else:
            start = pos
            while pos < length and body[pos] not in ",\n":
                pos += 1
            value = body[start:pos]
        fields[name] = " ".join(value.split())
        comma = body.find(",", pos)
        pos = comma + 1 if comma >= 0 else length
    return fields


def _strip_braces(value: str) -> str:
    return " ".join(re.sub(r"[{}]", "", value or "").split())


def _split_authors(value: str) -> list[str]:
    if not value:
        return []
    parts = re.split(r"\s+and\s+", value, flags=re.IGNORECASE)
    if len(parts) == 1 and ";" in value:
        parts = value.split(";")
    return [part.strip() for part in parts if part.strip()]


def _extract_year(value: str) -> str:
    match = re.search(r"(19|20)\d{2}", value or "")
    return match.group(0) if match else ""


# ---------------------------------------------------------------------------
# RIS parsing (tolerant of CNKI / EndNote exports)
# ---------------------------------------------------------------------------

_RIS_LINE = re.compile(r"^([A-Z][A-Z0-9])\s{0,2}-\s?(.*)$")

_RIS_TYPE_MAP = {
    "JOUR": "article",
    "CONF": "inproceedings",
    "CPAPER": "inproceedings",
    "THES": "phdthesis",
    "BOOK": "book",
    "CHAP": "incollection",
    "RPRT": "techreport",
    "UNPB": "unpublished",
    "NEWS": "misc",
}


def parse_ris(text: str, *, source_file: str = "") -> list[BibRecord]:
    records: list[BibRecord] = []
    current: dict[str, list[str]] | None = None
    last_tag = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip("﻿").rstrip()
        if not line.strip():
            continue
        match = _RIS_LINE.match(line.strip())
        if match:
            tag, value = match.group(1), match.group(2).strip()
            if tag == "TY":
                current = {"TY": [value]}
                last_tag = tag
                continue
            if current is None:
                continue
            if tag == "ER":
                records.append(_ris_to_record(current, source_file))
                current = None
                last_tag = ""
                continue
            current.setdefault(tag, []).append(value)
            last_tag = tag
        elif current is not None and last_tag and last_tag not in {"TY", "ER"}:
            # Continuation line (CNKI wraps long abstracts without tags).
            current[last_tag][-1] = (current[last_tag][-1] + " " + line.strip()).strip()
    if current is not None:
        records.append(_ris_to_record(current, source_file))
    return records


def _ris_first(payload: dict[str, list[str]], *tags: str) -> str:
    for tag in tags:
        values = payload.get(tag)
        if values and values[0].strip():
            return values[0].strip()
    return ""


def _ris_to_record(payload: dict[str, list[str]], source_file: str) -> BibRecord:
    authors = []
    for tag in ("AU", "A1", "A2", "A3"):
        authors.extend(value.strip() for value in payload.get(tag, []) if value.strip())
    title = _ris_first(payload, "TI", "T1")
    record = BibRecord(
        entry_type=_RIS_TYPE_MAP.get(_ris_first(payload, "TY").upper(), "article"),
        title=title,
        authors=authors,
        year=_extract_year(_ris_first(payload, "PY", "Y1", "DA")),
        journal=_ris_first(payload, "JO", "JF", "T2", "JA"),
        volume=_ris_first(payload, "VL"),
        number=_ris_first(payload, "IS"),
        pages="-".join(value for value in (_ris_first(payload, "SP"), _ris_first(payload, "EP")) if value),
        doi=normalize_doi(_ris_first(payload, "DO", "DI")),
        url=_ris_first(payload, "UR", "L1", "L2"),
        abstract=_ris_first(payload, "AB", "N2"),
        language=_ris_first(payload, "LA"),
        source_file=source_file,
        source_format="ris",
    )
    if not record.language and contains_cjk(record.title):
        record.language = "zh"
    return record


# ---------------------------------------------------------------------------
# CSV parsing (CNKI/GS spreadsheet exports; Chinese or English headers)
# ---------------------------------------------------------------------------

_CSV_HEADER_MAP = {
    "title": ["title", "篇名", "题名", "文献标题", "article title"],
    "authors": ["authors", "author", "作者", "author full names"],
    "year": ["year", "publication year", "年份", "发表年份", "发表时间", "出版年"],
    "journal": ["journal", "source", "刊名", "来源", "文献来源", "source title"],
    "doi": ["doi"],
    "url": ["url", "link", "链接", "网址"],
    "abstract": ["abstract", "摘要"],
}


def parse_csv_records(text: str, *, source_file: str = "") -> list[BibRecord]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames:
        return []
    lookup: dict[str, str] = {}
    for column in reader.fieldnames:
        normalized = (column or "").strip().lower()
        for target, aliases in _CSV_HEADER_MAP.items():
            if normalized in aliases and target not in lookup:
                lookup[target] = column
    records: list[BibRecord] = []
    for row in reader:
        def cell(name: str) -> str:
            column = lookup.get(name)
            return (row.get(column) or "").strip() if column else ""

        title = cell("title")
        if not title:
            continue
        authors_raw = cell("authors")
        authors = [part.strip() for part in re.split(r"[;；]", authors_raw) if part.strip()]
        record = BibRecord(
            title=title,
            authors=authors,
            year=_extract_year(cell("year")),
            journal=cell("journal"),
            doi=normalize_doi(cell("doi")),
            url=cell("url"),
            abstract=cell("abstract"),
            source_file=source_file,
            source_format="csv",
        )
        if contains_cjk(record.title):
            record.language = "zh"
        records.append(record)
    return records


def parse_records_file(path_text: str, file_name: str) -> list[BibRecord]:
    """Dispatch on extension, with content sniffing as a secondary parse path."""
    lower = file_name.lower()
    if lower.endswith(".bib") or lower.endswith(".bibtex"):
        return parse_bibtex(path_text, source_file=file_name)
    if lower.endswith(".ris") or lower.endswith(".txt"):
        parsed = parse_ris(path_text, source_file=file_name)
        if parsed:
            return parsed
        return parse_bibtex(path_text, source_file=file_name)
    if lower.endswith(".csv"):
        return parse_csv_records(path_text, source_file=file_name)
    if "@" in path_text and re.search(r"@\s*\w+\s*[{(]", path_text):
        return parse_bibtex(path_text, source_file=file_name)
    return parse_ris(path_text, source_file=file_name)


# ---------------------------------------------------------------------------
# Deduplication and normalized BibTeX output
# ---------------------------------------------------------------------------

def dedupe_records(records: list[BibRecord]) -> tuple[list[BibRecord], list[dict[str, Any]]]:
    """DOI first, then normalized title + year. Returns (kept, merge_log)."""
    kept: list[BibRecord] = []
    by_doi: dict[str, int] = {}
    by_title_year: dict[tuple[str, str], int] = {}
    merges: list[dict[str, Any]] = []
    for record in records:
        target_index: int | None = None
        if record.doi and record.doi in by_doi:
            target_index = by_doi[record.doi]
            reason = "doi"
        else:
            title_key = (normalize_title(record.title), record.year)
            if title_key[0] and title_key in by_title_year:
                target_index = by_title_year[title_key]
                reason = "title_year"
        if target_index is None:
            kept.append(record)
            index = len(kept) - 1
            if record.doi:
                by_doi[record.doi] = index
            title_key = (normalize_title(record.title), record.year)
            if title_key[0]:
                by_title_year[title_key] = index
        else:
            _merge_into(kept[target_index], record)
            merges.append(
                {
                    "kept_title": kept[target_index].title,
                    "dropped_title": record.title,
                    "dropped_source": record.source_file,
                    "match_on": reason,
                }
            )
    return kept, merges


def _merge_into(target: BibRecord, other: BibRecord) -> None:
    for attr in ("title", "year", "journal", "volume", "number", "pages", "doi", "url", "abstract", "language"):
        if not getattr(target, attr) and getattr(other, attr):
            setattr(target, attr, getattr(other, attr))
    if not target.authors and other.authors:
        target.authors = other.authors


def assign_citekeys(records: list[BibRecord]) -> None:
    taken: set[str] = {record.key for record in records if record.key}
    for record in records:
        if not record.key:
            record.key = make_citekey(record, taken)


def to_bibtex(record: BibRecord) -> str:
    fields: list[tuple[str, str]] = []
    if record.title:
        fields.append(("title", record.title))
    if record.authors:
        fields.append(("author", " and ".join(record.authors)))
    if record.year:
        fields.append(("year", record.year))
    if record.journal:
        journal_field = "journal" if record.entry_type == "article" else "booktitle"
        fields.append((journal_field, record.journal))
    for attr in ("volume", "number", "pages", "doi", "url"):
        value = getattr(record, attr)
        if value:
            fields.append((attr, value))
    if record.language:
        fields.append(("language", record.language))
    body = ",\n".join(f"  {name} = {{{value}}}" for name, value in fields)
    return f"@{record.entry_type}{{{record.key},\n{body}\n}}"


def records_to_bibtex(records: list[BibRecord]) -> str:
    return "\n\n".join(to_bibtex(record) for record in sorted(records, key=lambda item: item.key)) + "\n"
