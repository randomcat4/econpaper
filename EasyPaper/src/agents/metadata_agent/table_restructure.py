"""Critic-gated table schema restructuring helpers."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


SEMANTIC_CONTRACT_VERSION = "table_semantic_preservation_v1"


@dataclass
class TableRestructureResult:
    generated_sections: Dict[str, str]
    converted_tables: Dict[str, str]
    evolution: Dict[str, Any]
    iterations: List[Dict[str, Any]] = field(default_factory=list)
    approved_rewrite_count: int = 0


def _strip_code_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|latex|tex)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_json_response(text: str) -> Dict[str, Any]:
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _extract_table_block(content: str, table_id: str) -> str:
    if not content or not table_id:
        return ""
    pattern = re.compile(
        r"\\begin\{table\*?\}(?:\[[^\]]*\])?.*?"
        + re.escape(f"\\label{{{table_id}}}")
        + r".*?\\end\{table\*?\}",
        re.DOTALL,
    )
    match = pattern.search(content)
    return match.group(0) if match else ""


def _replace_table_block(content: str, table_id: str, replacement: str) -> Tuple[str, bool]:
    current = _extract_table_block(content, table_id)
    if not current:
        return content, False
    return content.replace(current, replacement, 1), True


def _extract_tabular_cells(latex: str) -> List[str]:
    body_match = re.search(
        r"\\begin\{tabular[*]?\}\{[^}]*\}(.*?)\\end\{tabular[*]?\}",
        latex or "",
        re.DOTALL,
    )
    body = body_match.group(1) if body_match else latex or ""
    cells: List[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%") or stripped.startswith("\\"):
            continue
        if "&" not in stripped:
            continue
        stripped = stripped.replace("\\\\", "")
        for cell in stripped.split("&"):
            clean = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", cell)
            clean = re.sub(r"[{}]", "", clean)
            clean = " ".join(clean.split())
            if clean:
                cells.append(clean)
    return cells


def _semantic_signature(latex: str) -> Dict[str, Any]:
    cells = _extract_tabular_cells(latex)
    numeric_tokens = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[%])?", " ".join(cells))
    text_tokens = [
        token.lower()
        for cell in cells
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]*", cell)
        if len(token) > 1
    ]
    return {
        "cell_count": len(cells),
        "numeric_tokens": sorted(numeric_tokens),
        "text_tokens": sorted(text_tokens),
    }


def _local_semantic_guard(original_latex: str, proposed_latex: str) -> Tuple[bool, str]:
    original = _semantic_signature(original_latex)
    proposed = _semantic_signature(proposed_latex)
    if original["numeric_tokens"] != proposed["numeric_tokens"]:
        return False, "numeric tokens changed"
    original_text = set(original["text_tokens"])
    proposed_text = set(proposed["text_tokens"])
    missing = sorted(original_text - proposed_text)
    if missing:
        return False, f"text tokens missing: {', '.join(missing[:8])}"
    if proposed["cell_count"] < max(1, int(original["cell_count"] * 0.7)):
        return False, "proposed table collapses too many cells"
    return True, "local semantic guard passed"


def _find_restructure_candidates(table_review_bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
    reviews_by_id = {
        str(review.get("table_id") or ""): review
        for review in table_review_bundle.get("reviews", []) or []
        if isinstance(review, dict)
    }
    candidates: List[Dict[str, Any]] = []
    for finding in table_review_bundle.get("paper_level_findings", []) or []:
        if not isinstance(finding, dict) or not finding.get("restructure_candidate"):
            continue
        if finding.get("type") != "table_font_inconsistent":
            continue
        table_id = (
            ((finding.get("evidence") or {}).get("max_shrink_table") or {}).get("table_id")
            or ""
        )
        review = reviews_by_id.get(str(table_id))
        if not review:
            continue
        if review.get("source_kind", "user_provided") != "user_provided":
            continue
        candidates.append(
            {
                "table_id": table_id,
                "review": review,
                "finding": finding,
            }
        )
    return candidates


def _build_contract(table_id: str, original_latex: str, evidence: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "version": SEMANTIC_CONTRACT_VERSION,
        "table_id": table_id,
        "hard_rules": [
            "Do not remove, summarize, invent, or change numeric values.",
            "Do not change the meaning of rows, columns, groups, metrics, ordering, or hierarchy.",
            "Schema restructuring is allowed only to reduce obvious font-size inconsistency.",
            "If semantic preservation cannot be proven, reject restructuring.",
        ],
        "original_signature": _semantic_signature(original_latex),
        "trigger_evidence": evidence,
    }


async def _call_json_agent(
    client: Any,
    model_name: str,
    *,
    system: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
        ],
        temperature=0.0,
    )
    return _parse_json_response(response.choices[0].message.content or "{}")


async def run_table_restructure_loop(
    *,
    client: Any,
    model_name: str,
    generated_sections: Dict[str, str],
    converted_tables: Optional[Dict[str, str]],
    table_review_bundle: Dict[str, Any],
    enabled: bool,
    max_iterations: int,
) -> TableRestructureResult:
    """Run conservative proposer/critic restructuring for justified tables."""
    sections = dict(generated_sections or {})
    tables = dict(converted_tables or {})
    iterations: List[Dict[str, Any]] = []
    evolution = {
        "enabled": bool(enabled),
        "max_iterations": int(max_iterations),
        "final_status": "not_run",
        "reason": "",
        "iterations": iterations,
    }
    if not enabled:
        evolution["reason"] = "table critic disabled"
        return TableRestructureResult(sections, tables, evolution, iterations, 0)
    candidates = _find_restructure_candidates(table_review_bundle)
    if not candidates:
        evolution["final_status"] = "no_candidates"
        evolution["reason"] = "no table met restructuring preconditions"
        return TableRestructureResult(sections, tables, evolution, iterations, 0)
    if client is None:
        evolution["final_status"] = "skipped"
        evolution["reason"] = "no LLM client available"
        return TableRestructureResult(sections, tables, evolution, iterations, 0)

    approved = 0
    max_rounds = max(1, int(max_iterations or 1))
    for candidate in candidates:
        table_id = str(candidate["table_id"])
        original_latex = tables.get(table_id, "")
        section_type = str((candidate.get("review") or {}).get("section_type") or "")
        if not original_latex and section_type in sections:
            original_latex = _extract_table_block(sections[section_type], table_id)
        if not original_latex:
            iterations.append(
                {
                    "iteration": len(iterations) + 1,
                    "status": "skipped",
                    "table_id": table_id,
                    "issues": [{"severity": "warning", "message": "original table block not found"}],
                }
            )
            continue

        contract = _build_contract(
            table_id,
            original_latex,
            {
                "review": candidate.get("review"),
                "finding": candidate.get("finding"),
            },
        )
        precheck = await _call_json_agent(
            client,
            model_name,
            system=(
                "You are a strict table restructuring critic. Return JSON only. "
                "Decide whether schema restructuring is justified under the "
                "semantic preservation contract."
            ),
            payload={
                "task": "precheck",
                "contract": contract,
                "required_output": {
                    "can_restructure": "boolean",
                    "reason": "string",
                    "required_preservation_proof": [
                        "item/group/metric/order/hierarchy mapping requirements"
                    ],
                },
            },
        )
        if not bool(precheck.get("can_restructure")):
            iterations.append(
                {
                    "iteration": len(iterations) + 1,
                    "table_id": table_id,
                    "status": "critic_rejected_precheck",
                    "before": contract,
                    "issues": [precheck],
                }
            )
            continue

        latest_feedback = precheck
        for _ in range(max_rounds):
            iteration_no = len(iterations) + 1
            proposal = await _call_json_agent(
                client,
                model_name,
                system=(
                    "You are an academic LaTeX table editor. Return JSON only. "
                    "You may restructure rows/columns only when every original "
                    "data item and semantic relation is preserved."
                ),
                payload={
                    "task": "rewrite_table",
                    "contract": contract,
                    "critic_feedback": latest_feedback,
                    "original_latex": original_latex,
                    "required_output": {
                        "proposed_latex": "complete LaTeX table",
                        "preservation_proof": "mapping of original rows, columns, groups, metrics, order, hierarchy",
                    },
                },
            )
            proposed_latex = _strip_code_fences(str(proposal.get("proposed_latex") or ""))
            local_ok, local_reason = _local_semantic_guard(original_latex, proposed_latex)
            if not local_ok:
                latest_feedback = {
                    "passed": False,
                    "reason": local_reason,
                    "source": "local_semantic_guard",
                }
                iterations.append(
                    {
                        "iteration": iteration_no,
                        "table_id": table_id,
                        "status": "local_rejected",
                        "before": contract,
                        "issues": [latest_feedback],
                        "after": proposal,
                    }
                )
                continue

            verdict = await _call_json_agent(
                client,
                model_name,
                system=(
                    "You are the final critic judge for table semantic preservation. "
                    "Return JSON only. Reject if any data item, grouping, metric, "
                    "ordering, or hierarchy is missing or changed."
                ),
                payload={
                    "task": "judge_rewrite",
                    "contract": contract,
                    "original_latex": original_latex,
                    "proposed_latex": proposed_latex,
                    "proposal": proposal,
                    "local_semantic_guard": local_reason,
                    "required_output": {
                        "passed": "boolean",
                        "reason": "string",
                        "semantic_preservation_proof": "string",
                    },
                },
            )
            if bool(verdict.get("passed")):
                tables[table_id] = proposed_latex
                if section_type in sections:
                    sections[section_type], _ = _replace_table_block(
                        sections[section_type],
                        table_id,
                        proposed_latex,
                    )
                approved += 1
                iterations.append(
                    {
                        "iteration": iteration_no,
                        "table_id": table_id,
                        "status": "approved",
                        "before": contract,
                        "issues": [verdict],
                        "after": {
                            "proposed_latex": proposed_latex,
                            "preservation_proof": proposal.get("preservation_proof", ""),
                        },
                    }
                )
                break

            latest_feedback = verdict
            iterations.append(
                {
                    "iteration": iteration_no,
                    "table_id": table_id,
                    "status": "critic_rejected_rewrite",
                    "before": contract,
                    "issues": [verdict],
                    "after": proposal,
                }
            )

    evolution["final_status"] = "approved" if approved else "reverted_original"
    evolution["reason"] = (
        f"approved {approved} table rewrite(s)"
        if approved
        else "no rewrite passed critic validation; original tables retained"
    )
    return TableRestructureResult(sections, tables, evolution, iterations, approved)
