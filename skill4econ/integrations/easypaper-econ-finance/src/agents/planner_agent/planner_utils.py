"""
Stateless helper utilities for PlannerAgent.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from .models import PaperPlan


def normalize_section_type_name(section_type: str) -> str:
    """
    Normalize common plural/alias section names.
    """
    st = (section_type or "").strip().lower()
    alias_map = {
        "methods": "method",
        "methodology": "method",
        "experiments": "experiment",
        "results": "result",
        "intro": "introduction",
    }
    return alias_map.get(st, st)


def normalize_code_focus(raw: Any) -> dict[str, Any]:
    """
    Normalize LLM-provided code_focus object for each section.
    """
    if not isinstance(raw, dict):
        return {}
    must_use = [str(x).strip() for x in (raw.get("must_use_evidence_ids", []) or []) if str(x).strip()]
    key_assets = [str(x).strip() for x in (raw.get("key_assets", []) or []) if str(x).strip()]
    allowed_scope = str(raw.get("allowed_claim_scope", "")).strip()
    notes = str(raw.get("notes", "")).strip()
    out: dict[str, Any] = {}
    if must_use:
        out["must_use_evidence_ids"] = must_use[:10]
    if key_assets:
        out["key_assets"] = key_assets[:8]
    if allowed_scope:
        out["allowed_claim_scope"] = allowed_scope[:320]
    if notes:
        out["notes"] = notes[:320]
    return out


def strip_code_fence(text: str) -> str:
    """
    Strip common markdown code fences from model outputs.
    """
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def extract_balanced_json_block(text: str, start_char: str) -> Optional[str]:
    """
    Extract first balanced JSON object/array block from text.
    """
    end_char = "}" if start_char == "{" else "]"
    start_idx = text.find(start_char)
    if start_idx < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    for i in range(start_idx, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "\"":
                in_string = False
            continue

        if ch == "\"":
            in_string = True
            continue
        if ch == start_char:
            depth += 1
        elif ch == end_char:
            depth -= 1
            if depth == 0:
                return text[start_idx:i + 1]
    return None


def safe_load_json(
    raw: str,
    expected: Optional[type] = None,
) -> Optional[Any]:
    """
    Parse JSON robustly from model outputs with optional type check.
    """
    cleaned = strip_code_fence(raw)
    candidates: list[str] = [cleaned]
    obj_block = extract_balanced_json_block(cleaned, "{")
    arr_block = extract_balanced_json_block(cleaned, "[")
    if obj_block:
        candidates.append(obj_block)
    if arr_block:
        candidates.append(arr_block)

    for cand in candidates:
        if not cand:
            continue
        try:
            parsed = json.loads(cand)
            if expected is not None and not isinstance(parsed, expected):
                continue
            return parsed
        except Exception:
            continue
    return None


def paper_plan_to_json(plan: PaperPlan) -> str:
    """
    Serialize a PaperPlan into readable JSON string.
    """
    return json.dumps(plan.model_dump(), ensure_ascii=False, indent=2)


def has_intro_contribution_summary_signal(plan: PaperPlan) -> bool:
    """
    Check whether introduction includes a contribution-summary intent.
    """
    intro = plan.get_section("introduction")
    if not intro:
        return False
    parts: list[str] = []
    parts.append(intro.mission or "")
    parts.extend([str(x) for x in (intro.key_content or [])])
    for para in intro._all_paragraphs():
        parts.append(para.key_point or "")
        parts.extend([str(x) for x in (para.supporting_points or [])])
    text = " ".join(parts).lower()
    return ("contribut" in text) and (
        ("summary" in text) or ("list" in text) or ("core" in text) or ("key" in text)
    )
