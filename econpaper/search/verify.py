"""L2 verification layer: per-entry existence and metadata checks for refs.bib.

This is the first reason L2 exists: it feeds the citation-safety fake-citation
hard block with real evidence. Free official APIs only (Crossref polite pool,
OpenAlex); an injectable fetcher keeps tests offline. User-requested offline
runs fail closed instead of emitting a substitute verification result.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import SEARCH_TIERS_VERSION
from .records import BibRecord, normalize_title, parse_bibtex, records_to_bibtex

Fetcher = Callable[[str], dict[str, Any] | None]

VERIFICATION_REPORT_FILENAME = "citation_verification_report.json"
DEFAULT_MAX_CALLS = 50
_TITLE_MATCH_THRESHOLD = 0.6

STATUS_VERIFIED = "verified"
STATUS_MISMATCH = "metadata_mismatch"
STATUS_DOI_NOT_FOUND = "doi_not_found"
STATUS_TITLE_NOT_FOUND = "title_not_found"
STATUS_OFFLINE = "unverified_offline"
STATUS_BUDGET = "skipped_budget"
STATUS_UNRESOLVABLE = "unresolvable_no_doi_or_title"


@dataclass
class VerificationIssue:
    code: str
    severity: str
    message: str
    paper_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message, "paper_key": self.paper_key}


@dataclass
class VerificationResult:
    entries: list[dict[str, Any]] = field(default_factory=list)
    records: list[BibRecord] = field(default_factory=list)
    status: str = "passed"
    api_calls_used: int = 0
    issues: list[VerificationIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str, paper_key: str | None = None) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(VerificationIssue(code=code, severity=severity, message=message, paper_key=paper_key))

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry["status"]] = counts.get(entry["status"], 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "api_calls_used": self.api_calls_used,
            "summary": self.summary(),
            "entries": self.entries,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def default_fetcher(mailto: str | None = None, timeout: float = 20.0) -> Fetcher:
    def fetch(url: str) -> dict[str, Any] | None:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": f"econpaper-search/{SEARCH_TIERS_VERSION} (mailto:{mailto or 'unset'})"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    return fetch


def verify_references(
    refs_path: str | Path,
    *,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_calls: int = DEFAULT_MAX_CALLS,
) -> VerificationResult:
    result = VerificationResult()
    refs = Path(refs_path)
    if not refs.exists():
        result.add_issue("missing_refs_file", "hard_block", f"refs.bib does not exist: {refs}")
        return result
    records = parse_bibtex(refs.read_text(encoding="utf-8-sig"), source_file=refs.name)
    if not records:
        result.add_issue("refs_bib_empty", "hard_block", f"No BibTeX entries parsed from {refs}.")
        return result
    if offline:
        result.records = records
        result.add_issue(
            "offline_not_allowed",
            "hard_block",
            "Citation verification requires live Crossref/OpenAlex access; offline mode is a boundary, not a successful substitute result.",
        )
        for record in records:
            result.entries.append(
                {
                    "paper_key": record.key,
                    "title": record.title,
                    "doi": record.doi,
                    "status": STATUS_OFFLINE,
                    "checked_sources": [],
                    "evidence": {"note": "offline run requested; no verification attempted"},
                    "enriched_fields": [],
                }
            )
        return result
    if fetcher is None and not offline:
        fetcher = default_fetcher(mailto)
    result.records = records
    for record in records:
        entry = _verify_record(record, result, fetcher, offline, mailto, max_calls)
        result.entries.append(entry)
    _raise_severities(result)
    return result


def write_verification_report(
    refs_path: str | Path,
    *,
    out_dir: str | Path,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_calls: int = DEFAULT_MAX_CALLS,
) -> VerificationResult:
    result = verify_references(
        refs_path,
        fetcher=fetcher,
        offline=offline,
        mailto=mailto,
        max_calls=max_calls,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / VERIFICATION_REPORT_FILENAME).write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if result.records:
        (out_path / "refs.normalized.bib").write_text(records_to_bibtex(result.records), encoding="utf-8")
    return result


def _verify_record(
    record: BibRecord,
    result: VerificationResult,
    fetcher: Fetcher | None,
    offline: bool,
    mailto: str | None,
    max_calls: int,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "paper_key": record.key,
        "title": record.title,
        "doi": record.doi,
        "status": STATUS_OFFLINE,
        "checked_sources": [],
        "evidence": {},
        "enriched_fields": [],
    }
    if record.language == "zh" and not record.doi:
        # Open APIs barely cover the CNKI ecosystem; do not burn budget or
        # mislabel Chinese entries as suspicious.
        entry["status"] = STATUS_OFFLINE
        entry["evidence"]["note"] = "Chinese-language record without DOI; open-API coverage is near zero (L2 is the English tier)."
        return entry
    if offline or fetcher is None:
        return entry
    if not record.doi and not record.title:
        entry["status"] = STATUS_UNRESOLVABLE
        return entry
    if result.api_calls_used >= max_calls:
        entry["status"] = STATUS_BUDGET
        return entry

    mailto_param = f"&mailto={urllib.parse.quote(mailto)}" if mailto else ""
    if record.doi:
        result.api_calls_used += 1
        payload = fetcher(f"https://api.crossref.org/works/{urllib.parse.quote(record.doi)}")
        entry["checked_sources"].append("crossref_doi")
        message = (payload or {}).get("message") if isinstance(payload, dict) else None
        if isinstance(message, dict):
            return _compare_metadata(record, entry, message_source="crossref", title=_crossref_title(message),
                                     year=_crossref_year(message), journal=_crossref_journal(message), doi=record.doi)
        entry["status"] = STATUS_DOI_NOT_FOUND
        return entry

    # No DOI: title search on Crossref, then OpenAlex.
    if result.api_calls_used < max_calls:
        result.api_calls_used += 1
        query = urllib.parse.quote(record.title)
        payload = fetcher(f"https://api.crossref.org/works?query.bibliographic={query}&rows=3{mailto_param}")
        entry["checked_sources"].append("crossref_title")
        items = (((payload or {}).get("message") or {}).get("items") or []) if isinstance(payload, dict) else []
        best = _best_title_match(record.title, items, _crossref_title)
        if best is not None:
            return _compare_metadata(record, entry, message_source="crossref", title=_crossref_title(best),
                                     year=_crossref_year(best), journal=_crossref_journal(best),
                                     doi=str(best.get("DOI") or "").lower())
    if result.api_calls_used < max_calls:
        result.api_calls_used += 1
        query = urllib.parse.quote(record.title)
        payload = fetcher(f"https://api.openalex.org/works?filter=title.search:{query}&per-page=3{mailto_param}")
        entry["checked_sources"].append("openalex_title")
        items = (payload or {}).get("results") or [] if isinstance(payload, dict) else []
        best = _best_title_match(record.title, items, lambda item: str(item.get("display_name") or ""))
        if best is not None:
            doi = str(best.get("doi") or "").replace("https://doi.org/", "").lower()
            year = str(best.get("publication_year") or "")
            return _compare_metadata(record, entry, message_source="openalex",
                                     title=str(best.get("display_name") or ""), year=year, journal="", doi=doi)
    entry["status"] = STATUS_TITLE_NOT_FOUND
    return entry


def _compare_metadata(
    record: BibRecord,
    entry: dict[str, Any],
    *,
    message_source: str,
    title: str,
    year: str,
    journal: str,
    doi: str,
) -> dict[str, Any]:
    entry["evidence"] = {"source": message_source, "matched_title": title, "matched_year": year, "matched_doi": doi}
    title_score = _title_similarity(record.title, title)
    year_ok = (not record.year) or (not year) or abs(int(record.year) - int(year)) <= 1
    if title_score >= _TITLE_MATCH_THRESHOLD and year_ok:
        entry["status"] = STATUS_VERIFIED
        for attr, matched in (("doi", doi), ("year", year), ("journal", journal)):
            if matched and not getattr(record, attr):
                setattr(record, attr, matched)
                entry["enriched_fields"].append(attr)
    else:
        entry["status"] = STATUS_MISMATCH
        entry["evidence"]["title_similarity"] = round(title_score, 3)
        entry["evidence"]["year_consistent"] = year_ok
    return entry


def _raise_severities(result: VerificationResult) -> None:
    for entry in result.entries:
        if entry["status"] == STATUS_DOI_NOT_FOUND:
            # A DOI that resolves to nothing is the strongest fabricated-citation
            # signal; this feeds the non-overridable fake-citation hard block.
            result.add_issue(
                "doi_resolves_to_nothing",
                "hard_block",
                f"Entry `{entry['paper_key']}` carries DOI `{entry['doi']}` that Crossref cannot resolve.",
                paper_key=entry["paper_key"],
            )
        elif entry["status"] in {STATUS_MISMATCH, STATUS_TITLE_NOT_FOUND}:
            # Could be a working paper outside Crossref: flag-and-confirm, not block.
            result.add_issue(
                "citation_unconfirmed",
                "flag",
                f"Entry `{entry['paper_key']}` could not be confirmed ({entry['status']}); confirm it exists or fix metadata.",
                paper_key=entry["paper_key"],
            )


def _best_title_match(title: str, items: list[Any], title_getter: Callable[[dict[str, Any]], str]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = 0.0
    for item in items:
        if not isinstance(item, dict):
            continue
        score = _title_similarity(title, title_getter(item))
        if score > best_score:
            best, best_score = item, score
    return best if best_score >= _TITLE_MATCH_THRESHOLD else None


def _title_similarity(left: str, right: str) -> float:
    tokens_left = set(normalize_title(left).split())
    tokens_right = set(normalize_title(right).split())
    if not tokens_left or not tokens_right:
        return 0.0
    overlap = len(tokens_left & tokens_right)
    return overlap / max(len(tokens_left), len(tokens_right))


def _crossref_title(message: dict[str, Any]) -> str:
    titles = message.get("title") or []
    return str(titles[0]) if titles else ""


def _crossref_year(message: dict[str, Any]) -> str:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = ((message.get(key) or {}).get("date-parts") or [[]])[0]
        if parts and parts[0]:
            return str(parts[0])
    return ""


def _crossref_journal(message: dict[str, Any]) -> str:
    containers = message.get("container-title") or []
    return str(containers[0]) if containers else ""
