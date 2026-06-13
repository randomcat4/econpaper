"""L2 retrieval layer: execute English query cards on open official APIs.

Free-first, no scraping: OpenAlex (metadata backbone) and arXiv (preprint
metadata/PDF locations) via an injectable fetcher with a per-run call budget.
Output is bibliographic candidates + low-confidence structured notes whose
`what_it_did` is only ever an official abstract excerpt. Offline, unreachable,
or under-budget runs fail closed instead of claiming an L1 substitute succeeded.
Chinese coverage in the open-API ecosystem is near zero; L2 is the English tier.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..intake import AUTHOR_INPUT_NEEDED
from . import SEARCH_TIERS_VERSION
from .ingest import structured_note_skeleton
from .records import BibRecord, assign_citekeys, dedupe_records, normalize_doi, records_to_bibtex
from .verify import Fetcher

DEFAULT_MAX_CALLS = 20
DEFAULT_MAX_RESULTS = 100
_ABSTRACT_EXCERPT_CHARS = 600


@dataclass
class OpenSearchIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


@dataclass
class OpenSearchResult:
    candidates: list[dict[str, Any]] = field(default_factory=list)
    records: list[BibRecord] = field(default_factory=list)
    notes: list[dict[str, Any]] = field(default_factory=list)
    queries_run: list[dict[str, Any]] = field(default_factory=list)
    api_calls_used: int = 0
    degraded_to: str | None = None
    stop_reason: str = ""
    status: str = "passed"
    issues: list[OpenSearchIssue] = field(default_factory=list)

    @property
    def has_hard_blocks(self) -> bool:
        return any(issue.severity == "hard_block" for issue in self.issues)

    def add_issue(self, code: str, severity: str, message: str) -> None:
        if severity == "hard_block":
            self.status = "failed"
        self.issues.append(OpenSearchIssue(code=code, severity=severity, message=message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SEARCH_TIERS_VERSION,
            "status": self.status,
            "has_hard_blocks": self.has_hard_blocks,
            "api_calls_used": self.api_calls_used,
            "degraded_to": self.degraded_to,
            "stop_reason": self.stop_reason,
            "queries_run": self.queries_run,
            "candidate_count": len(self.candidates),
            "candidates": self.candidates,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def run_open_search(
    *,
    prescription: dict[str, Any] | None = None,
    queries: list[str] | None = None,
    anchor_dois: list[str] | None = None,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_calls: int = DEFAULT_MAX_CALLS,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> OpenSearchResult:
    result = OpenSearchResult()
    query_list = list(queries or [])
    if prescription:
        query_list.extend(_queries_from_prescription(prescription))
        anchor_dois = list(anchor_dois or []) + [
            normalize_doi(anchor.get("doi"))
            for anchor in (prescription.get("snowball_plan") or {}).get("anchor_papers", [])
            if isinstance(anchor, dict) and anchor.get("doi")
        ]
    query_list = _dedupe_strings(query_list)
    anchor_dois = _dedupe_strings([doi for doi in (anchor_dois or []) if doi])

    if not query_list and not anchor_dois:
        result.add_issue(
            "no_queries",
            "hard_block",
            "Nothing to search: provide a prescription with English query cards, raw queries, or anchor DOIs.",
        )
        return result
    if offline:
        result.stop_reason = "offline_not_allowed"
        result.add_issue(
            "offline_not_allowed",
            "hard_block",
            "L2 retrieval requires live official API access; offline mode is a boundary, not a successful substitute result.",
        )
        return result
    if fetcher is None:
        fetcher = default_open_fetcher(mailto)

    mailto_param = f"&mailto={urllib.parse.quote(mailto)}" if mailto else ""
    raw_hits: list[tuple[BibRecord, dict[str, Any]]] = []

    for query in query_list:
        if result.api_calls_used >= max_calls:
            _block_budget(result)
            break
        result.api_calls_used += 1
        per_page = min(25, max_results)
        url = f"https://api.openalex.org/works?search={urllib.parse.quote(query)}&per-page={per_page}{mailto_param}"
        payload = fetcher(url)
        works = (payload or {}).get("results") if isinstance(payload, dict) else None
        result.queries_run.append({"source": "openalex", "query": query, "hits": None if works is None else len(works)})
        if works is None:
            result.add_issue("source_unreachable", "flag", f"OpenAlex returned nothing for query: {query}")
            continue
        for rank, work in enumerate(works):
            parsed = _record_from_openalex(work)
            if parsed:
                raw_hits.append((parsed, {"query": query, "rank": rank, "via": "openalex_search"}))
        if result.api_calls_used >= max_calls:
            _block_budget(result)
            break
        result.api_calls_used += 1
        arxiv_url = (
            "https://export.arxiv.org/api/query?"
            f"search_query=all:{urllib.parse.quote(query)}&start=0&max_results={min(25, max_results)}"
            "&sortBy=relevance&sortOrder=descending"
        )
        arxiv_payload = fetcher(arxiv_url)
        arxiv_records = _records_from_arxiv_payload(arxiv_payload)
        result.queries_run.append({"source": "arxiv", "query": query, "hits": None if arxiv_payload is None else len(arxiv_records)})
        if arxiv_payload is None:
            result.add_issue("source_unreachable", "flag", f"arXiv returned nothing for query: {query}")
            continue
        for rank, record in enumerate(arxiv_records):
            raw_hits.append((record, {"query": query, "rank": rank, "via": "arxiv_search"}))

    for doi in anchor_dois:
        if result.api_calls_used >= max_calls:
            _block_budget(result)
            break
        result.api_calls_used += 1
        payload = fetcher(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi)}?{mailto_param.lstrip('&')}")
        if not isinstance(payload, dict):
            result.add_issue("anchor_unresolved", "flag", f"Anchor DOI could not be resolved on OpenAlex: {doi}")
            continue
        anchor_id = str(payload.get("id") or "").rsplit("/", 1)[-1]
        result.queries_run.append({"source": "openalex", "query": f"anchor:{doi}", "hits": 1})
        # Forward snowball: works citing the anchor.
        if anchor_id and result.api_calls_used < max_calls:
            result.api_calls_used += 1
            cites_payload = fetcher(
                f"https://api.openalex.org/works?filter=cites:{anchor_id}&per-page=25&sort=publication_date:desc{mailto_param}"
            )
            citing = (cites_payload or {}).get("results") if isinstance(cites_payload, dict) else []
            result.queries_run.append({"source": "openalex", "query": f"cites:{anchor_id}", "hits": len(citing or [])})
            for rank, work in enumerate(citing or []):
                parsed = _record_from_openalex(work)
                if parsed:
                    raw_hits.append((parsed, {"query": f"cites:{doi}", "rank": rank, "via": "snowball_forward"}))
        # Backward snowball: the anchor's references (IDs only; resolve a capped batch).
        referenced = [str(item) for item in payload.get("referenced_works") or []][:25]
        if referenced and result.api_calls_used < max_calls:
            result.api_calls_used += 1
            ids = "|".join(ref.rsplit("/", 1)[-1] for ref in referenced)
            refs_payload = fetcher(f"https://api.openalex.org/works?filter=openalex_id:{ids}&per-page=25{mailto_param}")
            referenced_works = (refs_payload or {}).get("results") if isinstance(refs_payload, dict) else []
            result.queries_run.append({"source": "openalex", "query": f"references_of:{anchor_id}", "hits": len(referenced_works or [])})
            for rank, work in enumerate(referenced_works or []):
                parsed = _record_from_openalex(work)
                if parsed:
                    raw_hits.append((parsed, {"query": f"references_of:{doi}", "rank": rank, "via": "snowball_backward"}))

    if not raw_hits:
        if any(entry["hits"] is None for entry in result.queries_run):
            result.stop_reason = "source_unreachable"
            result.add_issue(
                "source_unreachable",
                "hard_block",
                "Open official APIs were unreachable; no substitute result is emitted.",
            )
        else:
            result.stop_reason = "no_hits"
            result.add_issue(
                "no_hits",
                "flag",
                "No candidates returned by open official APIs for the requested queries.",
            )
        return result

    records = [record for record, _ in raw_hits]
    provenance: dict[int, dict[str, Any]] = {id(record): meta for record, meta in raw_hits}
    deduped, _merges = dedupe_records(records)
    assign_citekeys(deduped)
    ranked = sorted(deduped, key=lambda record: -_score(record, provenance))[:max_results]
    result.records = ranked
    result.candidates = [_candidate_payload(record, provenance) for record in ranked]
    result.notes = [_abstract_note(record) for record in ranked]
    return result


def write_open_search_pack(
    *,
    out_dir: str | Path,
    prescription_path: str | Path | None = None,
    queries: list[str] | None = None,
    anchor_dois: list[str] | None = None,
    fetcher: Fetcher | None = None,
    offline: bool = False,
    mailto: str | None = None,
    max_calls: int = DEFAULT_MAX_CALLS,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> OpenSearchResult:
    prescription = None
    if prescription_path is not None:
        path = Path(prescription_path)
        if path.exists():
            prescription = json.loads(path.read_text(encoding="utf-8-sig"))
        else:
            result = OpenSearchResult()
            result.add_issue("missing_prescription", "hard_block", f"Prescription file does not exist: {path}")
            return result
    result = run_open_search(
        prescription=prescription,
        queries=queries,
        anchor_dois=anchor_dois,
        fetcher=fetcher,
        offline=offline,
        mailto=mailto,
        max_calls=max_calls,
        max_results=max_results,
    )
    out_path = Path(out_dir)
    internal = out_path / "reports" / "internal"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "open_search_report.json").write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if result.records:
        (out_path / "refs.candidates.bib").write_text(records_to_bibtex(result.records), encoding="utf-8")
        (out_path / "external_literature_notes.json").write_text(
            json.dumps(result.notes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return result


def default_open_fetcher(mailto: str | None = None, timeout: float = 20.0) -> Fetcher:
    def fetch(url: str) -> dict[str, Any] | None:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": f"econpaper-search/{SEARCH_TIERS_VERSION} (mailto:{mailto or 'unset'})"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
        except Exception:
            return None
        if "export.arxiv.org/api/query" in url:
            return {"_raw": body}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None


def _queries_from_prescription(prescription: dict[str, Any]) -> list[str]:
    """Use the English GS cards as plain keyword queries; WoS/CNKI syntax stays human-side."""
    queries: list[str] = []
    for card in prescription.get("query_cards", []):
        if card.get("language") != "en":
            continue
        query = str(card.get("query") or "")
        if not query or AUTHOR_INPUT_NEEDED in query:
            continue
        if card.get("source") == "google_scholar":
            cleaned = query.replace("intitle:", "")
            phrases = re.findall(r'"([^"]+)"', cleaned)
            queries.append(" ".join(phrases) if phrases else cleaned)
        elif card.get("source") == "web_of_science":
            phrases = re.findall(r'"([^"]+)"', query)
            if phrases:
                queries.append(" ".join(phrases[:4]))
    return queries


def _record_from_openalex(work: Any) -> BibRecord | None:
    if not isinstance(work, dict):
        return None
    title = str(work.get("display_name") or work.get("title") or "").strip()
    if not title:
        return None
    authors = []
    for authorship in work.get("authorships") or []:
        name = ((authorship or {}).get("author") or {}).get("display_name")
        if name:
            authors.append(str(name))
    location = (work.get("primary_location") or {}) if isinstance(work.get("primary_location"), dict) else {}
    venue = ((location.get("source") or {}) if isinstance(location.get("source"), dict) else {}).get("display_name", "")
    oa_info = work.get("open_access") or {}
    record = BibRecord(
        title=title,
        authors=authors,
        year=str(work.get("publication_year") or ""),
        journal=str(venue or ""),
        doi=normalize_doi(str(work.get("doi") or "")),
        url=str(work.get("id") or ""),
        abstract=_abstract_from_inverted_index(work.get("abstract_inverted_index")),
        source_file="openalex",
        source_format="api",
    )
    record.extra_fields["cited_by_count"] = str(work.get("cited_by_count") or 0)
    if isinstance(oa_info, dict) and oa_info.get("oa_url"):
        record.extra_fields["oa_url"] = str(oa_info["oa_url"])
    record.extra_fields["openalex_id"] = str(work.get("id") or "").rsplit("/", 1)[-1]
    return record


def _records_from_arxiv_payload(payload: Any) -> list[BibRecord]:
    if not isinstance(payload, dict) or not isinstance(payload.get("_raw"), str):
        return []
    try:
        root = ET.fromstring(payload["_raw"])
    except ET.ParseError:
        return []
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    records: list[BibRecord] = []
    for entry in root.findall("atom:entry", ns):
        title = _xml_text(entry.find("atom:title", ns))
        if not title:
            continue
        authors = [
            _xml_text(author.find("atom:name", ns))
            for author in entry.findall("atom:author", ns)
        ]
        authors = [author for author in authors if author]
        published = _xml_text(entry.find("atom:published", ns))
        arxiv_id = _xml_text(entry.find("atom:id", ns))
        doi = _xml_text(entry.find("arxiv:doi", ns))
        pdf_url = ""
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                pdf_url = link.attrib.get("href", "")
                break
        abstract = _xml_text(entry.find("atom:summary", ns))
        record = BibRecord(
            entry_type="article",
            title=" ".join(title.split()),
            authors=authors,
            year=published[:4] if published[:4].isdigit() else "",
            journal="arXiv preprint",
            doi=normalize_doi(doi),
            url=arxiv_id,
            abstract=" ".join(abstract.split()),
            source_file="arxiv",
            source_format="api",
        )
        if arxiv_id:
            record.extra_fields["arxiv_id"] = arxiv_id.rsplit("/", 1)[-1]
        if pdf_url:
            record.extra_fields["oa_url"] = pdf_url
            record.extra_fields["pdf_url"] = pdf_url
        records.append(record)
    return records


def _xml_text(node: Any) -> str:
    text = getattr(node, "text", None)
    return str(text).strip() if text else ""


def _abstract_from_inverted_index(index: Any) -> str:
    if not isinstance(index, dict) or not index:
        return ""
    positions: dict[int, str] = {}
    for word, slots in index.items():
        for slot in slots or []:
            positions[int(slot)] = str(word)
    return " ".join(positions[key] for key in sorted(positions))


def _score(record: BibRecord, provenance: dict[int, dict[str, Any]]) -> float:
    """Mixed ranking: API relevance order + log citation count (design §2.3.3)."""
    meta = provenance.get(id(record), {})
    rank = float(meta.get("rank", 25))
    citations = float(record.extra_fields.get("cited_by_count") or 0)
    return (25.0 - min(rank, 25.0)) + 4.0 * math.log1p(citations)


def _candidate_payload(record: BibRecord, provenance: dict[int, dict[str, Any]]) -> dict[str, Any]:
    meta = provenance.get(id(record), {})
    payload = record.to_dict()
    payload["cited_by_count"] = int(record.extra_fields.get("cited_by_count") or 0)
    payload["oa_url"] = record.extra_fields.get("oa_url", "")
    payload["pdf_url"] = record.extra_fields.get("pdf_url", "")
    payload["arxiv_id"] = record.extra_fields.get("arxiv_id", "")
    payload["openalex_id"] = record.extra_fields.get("openalex_id", "")
    payload["found_via"] = meta.get("via", "openalex_search")
    payload["matched_query"] = meta.get("query", "")
    return payload


def _abstract_note(record: BibRecord) -> dict[str, Any]:
    excerpt = record.abstract.strip()[:_ABSTRACT_EXCERPT_CHARS]
    note = structured_note_skeleton(
        record,
        created_by="econpaper_search_l2_openapi",
        what_it_did=f"[ABSTRACT EXCERPT, unverified] {excerpt}" if excerpt else None,
        confidence="low",
    )
    return note


def _block_budget(result: OpenSearchResult) -> None:
    if not result.has_hard_blocks:
        result.stop_reason = "api_call_budget"
        result.add_issue(
            "budget_exhausted",
            "hard_block",
            "API call budget exhausted before all requested official sources were queried; partial candidates are retained but no substitute success is claimed.",
        )


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out
