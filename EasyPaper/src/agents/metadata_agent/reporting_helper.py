"""
Reporting and alignment helper utilities for MetaDataAgent.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

from ..shared.session_memory import SessionMemory

if TYPE_CHECKING:
    from ..planner_agent.models import PaperPlan, SectionPlan


class ReportingHelper:
    """
    Builds citation, structure, and reviewer alignment reports.
    """

    def __init__(self, citation_validator, paragraph_splitter):
        self._citation_validator = citation_validator
        self._paragraph_splitter = paragraph_splitter

    def collect_section_citation_budget_usage(
        self,
        *,
        section_type: str,
        content: str,
        section_plan: Optional[SectionPlan],
        writer_valid_keys: List[str],
    ) -> Optional[Dict[str, Any]]:
        if not section_plan:
            return None

        valid_set = set(writer_valid_keys or [])
        _, _, used_keys = self._citation_validator(content, valid_set, remove_invalid=False)
        selected_refs = list(section_plan.budget_selected_refs or section_plan.assigned_refs or [])
        selected_set = set(selected_refs)
        used_budget_keys = [k for k in used_keys if k in selected_set]
        overflow_keys = [k for k in used_keys if k not in selected_set]
        budget = section_plan.citation_budget or {}
        return {
            "section_type": section_type,
            "min_refs": budget.get("min_refs"),
            "target_refs": budget.get("target_refs"),
            "max_refs": budget.get("max_refs"),
            "selected_refs": selected_refs,
            "reserve_refs": list(section_plan.budget_reserve_refs or []),
            "writer_valid_keys_count": len(valid_set),
            "used_keys": used_keys,
            "used_count": len(used_keys),
            "used_budget_keys": used_budget_keys,
            "used_budget_count": len(used_budget_keys),
            "overflow_keys": overflow_keys,
            "overflow_count": len(overflow_keys),
        }

    @staticmethod
    def upsert_section_budget_usage(
        usage_rows: List[Dict[str, Any]],
        usage_row: Optional[Dict[str, Any]],
    ) -> None:
        if not usage_row:
            return
        section_type = usage_row.get("section_type")
        if not section_type:
            return
        for idx, row in enumerate(usage_rows):
            if row.get("section_type") == section_type:
                usage_rows[idx] = usage_row
                return
        usage_rows.append(usage_row)

    @staticmethod
    def build_citation_plan_alignment_stats(
        paper_plan: Optional[PaperPlan],
        usage_rows: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        usage_by_section: Dict[str, Dict[str, Any]] = {
            str(r.get("section_type")): r
            for r in usage_rows
            if r.get("section_type")
        }

        per_section: List[Dict[str, Any]] = []
        total_selected = total_used = total_used_budget = total_overflow = total_missing = 0
        sections_with_budget = sections_meeting_min = 0

        for sp in (paper_plan.sections if paper_plan else []):
            budget = sp.citation_budget or {}
            selected_refs = list(sp.budget_selected_refs or sp.assigned_refs or [])
            usage = usage_by_section.get(sp.section_type, {})
            used_keys = list(usage.get("used_keys", []) or [])
            used_budget_keys = list(usage.get("used_budget_keys", []) or [])
            overflow_keys = list(usage.get("overflow_keys", []) or [])
            missing_selected_refs = [k for k in selected_refs if k not in set(used_budget_keys)]

            min_refs = int(budget.get("min_refs") or 0)
            target_refs = int(budget.get("target_refs") or 0)
            max_refs = int(budget.get("max_refs") or 0)

            used_count = len(used_keys)
            used_budget_count = len(used_budget_keys)
            overflow_count = len(overflow_keys)
            selected_count = len(selected_refs)
            coverage_rate = round(used_budget_count / selected_count, 4) if selected_count > 0 else None
            min_met = (used_count >= min_refs) if min_refs > 0 else True
            target_met = (used_count >= target_refs) if target_refs > 0 else True
            max_exceeded = (used_count > max_refs) if max_refs > 0 else False

            if selected_count > 0:
                sections_with_budget += 1
            if min_met:
                sections_meeting_min += 1

            total_selected += selected_count
            total_used += used_count
            total_used_budget += used_budget_count
            total_overflow += overflow_count
            total_missing += len(missing_selected_refs)

            per_section.append(
                {
                    "section_type": sp.section_type,
                    "plan": {
                        "min_refs": min_refs,
                        "target_refs": target_refs,
                        "max_refs": max_refs,
                        "selected_count": selected_count,
                        "selected_refs": selected_refs,
                    },
                    "final": {
                        "used_count": used_count,
                        "used_keys": used_keys,
                        "used_budget_count": used_budget_count,
                        "used_budget_keys": used_budget_keys,
                        "overflow_count": overflow_count,
                        "overflow_keys": overflow_keys,
                    },
                    "delta": {
                        "coverage_rate": coverage_rate,
                        "missing_selected_count": len(missing_selected_refs),
                        "missing_selected_refs": missing_selected_refs,
                        "extra_non_budget_count": overflow_count,
                    },
                    "status": {
                        "min_met": min_met,
                        "target_met": target_met,
                        "max_exceeded": max_exceeded,
                    },
                }
            )

        overall = {
            "sections_total": len(per_section),
            "sections_with_budget": sections_with_budget,
            "sections_meeting_min": sections_meeting_min,
            "total_selected_refs": total_selected,
            "total_used_refs": total_used,
            "total_used_budget_refs": total_used_budget,
            "total_overflow_refs": total_overflow,
            "total_missing_selected_refs": total_missing,
            "overall_budget_coverage_rate": round(total_used_budget / total_selected, 4) if total_selected > 0 else None,
        }
        return {"overall": overall, "sections": per_section}

    def build_structure_alignment_stats(
        self,
        *,
        paper_plan: Optional[PaperPlan],
        generated_sections: Dict[str, str],
        threshold: int,
    ) -> Dict[str, Any]:
        per_section: List[Dict[str, Any]] = []
        gate_expected_count = gate_pass_count = 0

        for sp in (paper_plan.sections if paper_plan else []):
            final_content = generated_sections.get(sp.section_type, "") or ""
            paragraphs = [p.strip() for p in re.split(r"\n\s*\n", final_content) if p.strip()]
            paragraph_count = len(paragraphs)
            subsection_count = len(re.findall(r"\\subsection\{.+?\}|\\subsubsection\{.+?\}", final_content))
            transition_count = 0
            for para in paragraphs[1:]:
                lower = para.lower()
                if lower.startswith(("however", "therefore", "in contrast", "meanwhile", "moreover", "furthermore", "additionally", "by contrast", "in summary")):
                    transition_count += 1

            expected_gate = bool(sp.sectioning_recommended or paragraph_count >= threshold) and sp.section_type not in {"abstract", "conclusion"}
            passed_gate = bool(subsection_count > 0 or (paragraph_count >= 4 and transition_count >= 1))
            if expected_gate:
                gate_expected_count += 1
                if passed_gate:
                    gate_pass_count += 1

            per_section.append(
                {
                    "section_type": sp.section_type,
                    "plan": {
                        "paragraph_count": len(sp.paragraphs or []),
                        "topic_clusters": list(sp.topic_clusters or []),
                        "transition_intents": list(sp.transition_intents or []),
                        "sectioning_recommended": bool(sp.sectioning_recommended),
                    },
                    "final": {
                        "paragraph_count": paragraph_count,
                        "explicit_subsection_count": subsection_count,
                        "transition_marker_count": transition_count,
                    },
                    "status": {
                        "structure_gate_expected": expected_gate,
                        "structure_gate_passed": passed_gate if expected_gate else None,
                    },
                }
            )

        return {
            "overall": {
                "sections_total": len(per_section),
                "gate_expected_sections": gate_expected_count,
                "gate_passed_sections": gate_pass_count,
                "gate_pass_rate": round(gate_pass_count / gate_expected_count, 4) if gate_expected_count > 0 else None,
            },
            "sections": per_section,
        }

    def build_paragraph_feedback_alignment_report(
        self,
        *,
        memory: Optional[SessionMemory],
        generated_sections: Dict[str, str],
    ) -> Dict[str, Any]:
        if memory is None or not getattr(memory, "review_history", None):
            return {"sections": [], "overall": {"records": 0}}

        latest = memory.review_history[-1]
        rows: List[Dict[str, Any]] = []
        total_targets = total_mapped = total_out_of_range = 0

        for section_type, feedback in (latest.section_feedbacks or {}).items():
            if not isinstance(feedback, dict):
                continue
            target_paragraphs = [
                int(x) for x in (feedback.get("target_paragraphs", []) or [])
                if str(x).strip().lstrip("-").isdigit()
            ]
            final_paragraphs = self._paragraph_splitter(generated_sections.get(section_type, "") or "")
            final_count = len(final_paragraphs)
            mapped = []
            out_of_range = []
            for pidx in target_paragraphs:
                if 0 <= pidx < final_count:
                    mapped.append({"from": pidx, "to": [pidx], "strategy": "identity"})
                elif final_count > 0:
                    nearest = min(max(pidx, 0), final_count - 1)
                    mapped.append({"from": pidx, "to": [nearest], "strategy": "clamped_nearest"})
                    out_of_range.append(pidx)
                else:
                    mapped.append({"from": pidx, "to": [], "strategy": "no_paragraphs"})
                    out_of_range.append(pidx)

            total_targets += len(target_paragraphs)
            total_mapped += len([m for m in mapped if m.get("to")])
            total_out_of_range += len(out_of_range)

            rows.append(
                {
                    "section_type": section_type,
                    "target_paragraphs": target_paragraphs,
                    "final_paragraph_count": final_count,
                    "mappings": mapped,
                    "out_of_range_targets": out_of_range,
                }
            )

        return {
            "overall": {
                "records": len(rows),
                "total_targets": total_targets,
                "mapped_targets": total_mapped,
                "out_of_range_targets": total_out_of_range,
            },
            "sections": rows,
        }

    def rebuild_citation_budget_usage_from_final_sections(
        self,
        *,
        paper_plan: Optional[PaperPlan],
        generated_sections: Dict[str, str],
        valid_citation_keys: Optional[Set[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not paper_plan:
            return []

        usage_rows: List[Dict[str, Any]] = []
        for sp in paper_plan.sections:
            final_content = generated_sections.get(sp.section_type, "")
            if valid_citation_keys is not None:
                writer_valid_keys = list(valid_citation_keys)
            else:
                writer_valid_keys = list(dict.fromkeys(list(sp.budget_selected_refs or sp.assigned_refs or [])))
            usage_row = self.collect_section_citation_budget_usage(
                section_type=sp.section_type,
                content=final_content,
                section_plan=sp,
                writer_valid_keys=writer_valid_keys,
            )
            self.upsert_section_budget_usage(usage_rows, usage_row)
        return usage_rows

    @staticmethod
    def build_reviewer_acceptance_stats(
        *,
        memory: Optional[SessionMemory],
    ) -> Dict[str, Any]:
        if memory is None or not getattr(memory, "review_history", None):
            return {"overall": {"total": 0}, "by_iteration": []}

        by_iteration: List[Dict[str, Any]] = []
        total = passed = failed = noop_accepted = changed_accepted = 0
        for rec in memory.review_history:
            verifications = list(getattr(rec, "reviewer_verification", []) or [])
            iter_total = len(verifications)
            iter_passed = iter_failed = iter_noop_accepted = iter_changed_accepted = 0
            for v in verifications:
                if not isinstance(v, dict):
                    continue
                ok = bool(v.get("passed", False))
                changed_flag = bool(v.get("changed", False))
                if ok:
                    iter_passed += 1
                    if changed_flag:
                        iter_changed_accepted += 1
                    else:
                        iter_noop_accepted += 1
                else:
                    iter_failed += 1

            total += iter_total
            passed += iter_passed
            failed += iter_failed
            noop_accepted += iter_noop_accepted
            changed_accepted += iter_changed_accepted
            by_iteration.append(
                {
                    "iteration": int(getattr(rec, "iteration", 0)),
                    "total": iter_total,
                    "passed": iter_passed,
                    "failed": iter_failed,
                    "noop_accepted": iter_noop_accepted,
                    "changed_accepted": iter_changed_accepted,
                }
            )

        return {
            "overall": {
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total, 4) if total > 0 else None,
                "noop_accepted": noop_accepted,
                "changed_accepted": changed_accepted,
            },
            "by_iteration": by_iteration,
        }

    @staticmethod
    def build_citation_repair_stats(
        *,
        memory: Optional[SessionMemory],
    ) -> Dict[str, Any]:
        if memory is None or not getattr(memory, "review_history", None):
            return {"overall": {"removed_total": 0}, "by_section": {}, "events": []}

        by_section: Dict[str, int] = {}
        events: List[Dict[str, Any]] = []
        removed_total = 0
        for rec in memory.review_history:
            trace_rows = list(getattr(rec, "decision_trace", []) or [])
            for row in trace_rows:
                if not isinstance(row, dict):
                    continue
                if str(row.get("decision", "")) != "removed_invalid_citations":
                    continue
                section_type = str(row.get("section_type", "unknown"))
                count = int(row.get("count", 0) or 0)
                removed_total += count
                by_section[section_type] = by_section.get(section_type, 0) + count
                events.append(
                    {
                        "iteration": int(getattr(rec, "iteration", 0)),
                        "section_type": section_type,
                        "count": count,
                        "keys": list(row.get("keys", []) or []),
                    }
                )
        return {
            "overall": {"removed_total": removed_total, "events": len(events)},
            "by_section": by_section,
            "events": events,
        }

    @staticmethod
    def build_explicit_subsection_coverage(
        *,
        paper_plan: Optional[PaperPlan],
        generated_sections: Dict[str, str],
    ) -> Dict[str, Any]:
        rows: List[Dict[str, Any]] = []
        recommended_total = recommended_with_explicit = 0
        for sp in (paper_plan.sections if paper_plan else []):
            if sp.section_type in {"abstract", "conclusion"}:
                continue
            if not bool(sp.sectioning_recommended):
                continue
            recommended_total += 1
            content = generated_sections.get(sp.section_type, "") or ""
            explicit_count = len(re.findall(r"\\subsection\{.+?\}|\\subsubsection\{.+?\}", content))
            has_explicit = explicit_count > 0
            if has_explicit:
                recommended_with_explicit += 1
            rows.append(
                {
                    "section_type": sp.section_type,
                    "section_title": sp.section_title,
                    "explicit_subsection_count": explicit_count,
                    "has_explicit_subsection": has_explicit,
                }
            )
        return {
            "overall": {
                "recommended_sections": recommended_total,
                "recommended_with_explicit_subsection": recommended_with_explicit,
                "coverage_rate": round(recommended_with_explicit / recommended_total, 4) if recommended_total > 0 else None,
            },
            "sections": rows,
        }
