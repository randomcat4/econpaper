"""
Overflow manager for metadata-agent structural page-limit mitigation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..vlm_review_agent.models import SECTION_TRIM_PRIORITY
from ..planner_agent.models import PaperPlan
from .models import FigureSpec, SpaceEstimate, StructuralAction


@dataclass
class StructuralActionDiagnostic:
    severity: str
    action_type: str
    target_id: str
    section: str
    code: str
    message: str


class OverflowManager:
    """
    Encapsulates structural overflow planning and execution.
    """

    _ELEMENT_PAGE_COST = {
        "figure*": 0.4,
        "figure": 0.2,
        "table*": 0.3,
        "table": 0.15,
    }

    def estimate_section_space(
        self,
        section_type: str,
        content: str,
    ) -> SpaceEstimate:
        est = SpaceEstimate()

        est.wide_figures = len(re.findall(r"\\begin\{figure\*\}", content))
        est.narrow_figures = len(re.findall(r"\\begin\{figure\}", content)) - est.wide_figures
        if est.narrow_figures < 0:
            est.narrow_figures = 0

        est.wide_tables = len(re.findall(r"\\begin\{table\*\}", content))
        est.narrow_tables = len(re.findall(r"\\begin\{table\}", content)) - est.wide_tables
        if est.narrow_tables < 0:
            est.narrow_tables = 0

        est.figure_ids = re.findall(r"\\label\{(fig:[^}]+)\}", content)
        est.table_ids = re.findall(r"\\label\{(tab:[^}]+)\}", content)

        est.total_pages = (
            est.wide_figures * self._ELEMENT_PAGE_COST["figure*"]
            + est.narrow_figures * self._ELEMENT_PAGE_COST["figure"]
            + est.wide_tables * self._ELEMENT_PAGE_COST["table*"]
            + est.narrow_tables * self._ELEMENT_PAGE_COST["table"]
        )
        return est

    def plan_overflow_strategy(
        self,
        overflow_pages: float,
        generated_sections: Dict[str, str],
        paper_plan: Optional[PaperPlan],
        figures: Optional[List[FigureSpec]],
    ) -> List[StructuralAction]:
        actions: List[StructuralAction] = []
        remaining = overflow_pages

        if remaining <= 0:
            return actions

        space_map: Dict[str, SpaceEstimate] = {}
        for sec, content in generated_sections.items():
            if sec == "appendix":
                continue
            space_map[sec] = self.estimate_section_space(sec, content)

        print(
            f"[OverflowStrategy] overflow={overflow_pages:.1f} pages, "
            f"Level={'1' if overflow_pages < 0.5 else '2' if overflow_pages <= 1.5 else '3'}"
        )
        for sec, est in space_map.items():
            if est.total_pages > 0:
                print(
                    f"  {sec}: {est.wide_figures} figure*, {est.narrow_figures} figure, "
                    f"{est.wide_tables} table*, {est.narrow_tables} table  "
                    f"=> ~{est.total_pages:.2f} pages"
                )

        if overflow_pages < 0.5:
            return actions

        processed_ids: set[str] = set()
        sorted_sections = sorted(
            space_map.keys(),
            key=lambda s: SECTION_TRIM_PRIORITY.get(s, 5),
            reverse=True,
        )

        for sec in sorted_sections:
            est = space_map.get(sec)
            if not est or est.wide_figures == 0:
                continue
            for fid in est.figure_ids:
                if fid in processed_ids:
                    continue
                savings = 0.2
                actions.append(
                    StructuralAction(
                        action_type="downgrade_wide",
                        target_id=fid,
                        section=sec,
                        estimated_savings=savings,
                    )
                )
                processed_ids.add(fid)
                remaining -= savings
                print(f"  -> downgrade_wide figure {fid} in {sec} (save ~{savings:.1f}p)")
                if remaining <= 0:
                    break
            if remaining <= 0:
                break

        if remaining > 0:
            for sec in sorted_sections:
                est = space_map.get(sec)
                if not est or (est.wide_figures + est.narrow_figures) == 0:
                    continue
                for fid in est.figure_ids:
                    resize_key = f"resize:{fid}"
                    if resize_key in processed_ids:
                        continue
                    savings = 0.05
                    actions.append(
                        StructuralAction(
                            action_type="resize_figure",
                            target_id=fid,
                            section=sec,
                            params={"width": "0.8\\linewidth"},
                            estimated_savings=savings,
                        )
                    )
                    processed_ids.add(resize_key)
                    remaining -= savings
                    if remaining <= 0:
                        break
                if remaining <= 0:
                    break

        if overflow_pages > 1.5 and remaining > 0:
            for sec in sorted_sections:
                est = space_map.get(sec)
                if not est:
                    continue
                if remaining > 0:
                    for tid in est.table_ids:
                        move_key = f"move:{tid}"
                        if move_key in processed_ids:
                            continue
                        savings = (
                            self._ELEMENT_PAGE_COST["table*"]
                            if est.wide_tables > 0
                            else self._ELEMENT_PAGE_COST["table"]
                        )
                        if "appendix" not in generated_sections and not any(
                            a.action_type == "create_appendix" for a in actions
                        ):
                            actions.append(StructuralAction(action_type="create_appendix", estimated_savings=0))
                        actions.append(
                            StructuralAction(
                                action_type="move_table",
                                target_id=tid,
                                section=sec,
                                estimated_savings=savings,
                            )
                        )
                        processed_ids.add(move_key)
                        remaining -= savings
                        print(f"  -> move_table {tid} from {sec} to appendix (save ~{savings:.1f}p)")
                        if remaining <= 0:
                            break
                if remaining <= 0:
                    break

        if remaining > 0:
            print(
                "[OverflowStrategy] WARNING: unresolved overflow remains after same-section "
                "figure resizing/downgrading; figure moves to appendix are disabled."
            )

        total_savings = sum(a.estimated_savings for a in actions)
        print(
            f"[OverflowStrategy] Planned {len(actions)} structural actions, "
            f"estimated savings ~{total_savings:.1f} pages"
        )
        return actions

    def resize_figures_in_section(
        self,
        section_content: str,
        actions: List[StructuralAction],
        *,
        column_format: Optional[str] = None,
    ) -> tuple[str, List[StructuralActionDiagnostic]]:
        modified = section_content
        diagnostics: List[StructuralActionDiagnostic] = []

        for act in actions:
            target_label = act.target_id
            block_re = re.compile(
                r"(\\begin\{figure\*?\}.*?\\label\{"
                + re.escape(target_label)
                + r"\}.*?\\end\{figure\*?\})",
                re.DOTALL,
            )
            match = block_re.search(modified)
            if not match:
                severity = "error" if act.action_type == "downgrade_wide" else "warning"
                diagnostics.append(StructuralActionDiagnostic(
                    severity=severity,
                    action_type=act.action_type,
                    target_id=target_label,
                    section=act.section,
                    code="target_label_not_found",
                    message=f"Could not find figure block for label '{target_label}' in section '{act.section}'.",
                ))
                continue

            block = match.group(1)
            if act.action_type == "downgrade_wide":
                new_block = block.replace("\\begin{figure*}", "\\begin{figure}")
                new_block = new_block.replace("\\end{figure*}", "\\end{figure}")
                new_block = re.sub(
                    r"\\includegraphics\[([^\]]*?)width\s*=\s*[^,\]\s]+",
                    lambda m: f"\\includegraphics[{m.group(1)}width=0.82\\linewidth",
                    new_block,
                    count=1,
                )
                modified = modified[:match.start()] + new_block + modified[match.end():]
                print(f"  [Structural] Downgraded figure* -> figure for {act.target_id}")
            elif act.action_type == "resize_figure":
                target_width = act.params.get("width", "0.8\\linewidth")
                new_block = re.sub(
                    r"\\includegraphics\[([^\]]*?)width\s*=\s*\\textwidth",
                    lambda m: f"\\includegraphics[{m.group(1)}width={target_width}",
                    block,
                )
                new_block = re.sub(
                    r"\\includegraphics\[([^\]]*?)width\s*=\s*\\linewidth",
                    lambda m: f"\\includegraphics[{m.group(1)}width={target_width}",
                    new_block,
                )
                new_block = re.sub(
                    r"\\includegraphics\[([^\]]*?)width\s*=\s*\\columnwidth",
                    lambda m: f"\\includegraphics[{m.group(1)}width={target_width}",
                    new_block,
                )
                modified = modified[:match.start()] + new_block + modified[match.end():]
                print(f"  [Structural] Resized figures to {target_width} for {act.target_id}")

        return modified, diagnostics

    def move_figures_to_appendix(
        self,
        generated_sections: Dict[str, str],
        actions: List[StructuralAction],
    ) -> None:
        if "appendix" not in generated_sections:
            generated_sections["appendix"] = ""

        appendix_parts: List[str] = []
        if generated_sections["appendix"]:
            appendix_parts.append(generated_sections["appendix"])

        existing_labels = set(re.findall(r"\\label\{([^}]+)\}", generated_sections["appendix"]))

        for act in actions:
            if act.action_type not in ("move_figure", "move_table"):
                continue

            if act.action_type == "move_figure":
                print(
                    f"  [Structural] WARNING: blocked move_figure {act.target_id}; "
                    "figures may not be moved to appendix"
                )
                continue

            sec = act.section
            content = generated_sections.get(sec, "")
            if not content:
                continue

            target_label = act.target_id
            if target_label in existing_labels:
                print(f"  [Structural] Skipping {target_label} — already in appendix")
                continue

            env_names = ["table\\*", "table"]
            ref_text = f"Table~\\\\ref{{{target_label}}}"

            extracted = False
            for env in env_names:
                pattern = re.compile(
                    r"(\\begin\{" + env + r"\}.*?\\label\{" + re.escape(target_label) + r"\}.*?\\end\{" + env + r"\})",
                    re.DOTALL,
                )
                m = pattern.search(content)
                if m:
                    block = m.group(1)
                    replacement = f"% [{target_label} moved to Appendix]\n(see {ref_text} in the Appendix)"
                    content = content[:m.start()] + replacement + content[m.end():]
                    generated_sections[sec] = content
                    appendix_parts.append(block)
                    existing_labels.add(target_label)
                    extracted = True
                    print(f"  [Structural] Moved {target_label} from {sec} to appendix")
                    break

            if not extracted:
                for env in env_names:
                    pattern = re.compile(r"(\\begin\{" + env + r"\}.*?\\end\{" + env + r"\})", re.DOTALL)
                    for m in pattern.finditer(content):
                        if target_label in m.group(1):
                            block = m.group(1)
                            replacement = f"% [{target_label} moved to Appendix]\n(see {ref_text} in the Appendix)"
                            content = content[:m.start()] + replacement + content[m.end():]
                            generated_sections[sec] = content
                            appendix_parts.append(block)
                            existing_labels.add(target_label)
                            extracted = True
                            print(f"  [Structural] Moved {target_label} from {sec} to appendix (alt)")
                            break
                    if extracted:
                        break

            if not extracted:
                print(f"  [Structural] WARNING: Could not find {target_label} in {sec}")

        generated_sections["appendix"] = "\n\n".join(appendix_parts)

    def create_appendix_section(
        self,
        generated_sections: Dict[str, str],
        section_order: List[str],
    ) -> None:
        if "appendix" not in generated_sections:
            generated_sections["appendix"] = ""
            print("[Structural] Created appendix section")

        if "appendix" not in section_order:
            if "conclusion" in section_order:
                idx = section_order.index("conclusion") + 1
                section_order.insert(idx, "appendix")
            else:
                section_order.append("appendix")
            print(f"[Structural] Added appendix to section_order at position {section_order.index('appendix')}")

    def execute_structural_actions(
        self,
        actions: List[StructuralAction],
        generated_sections: Dict[str, str],
        section_order: List[str],
        *,
        column_format: Optional[str] = None,
    ) -> List[StructuralActionDiagnostic]:
        diagnostics: List[StructuralActionDiagnostic] = []
        if not actions:
            return diagnostics

        print(f"[Structural] Executing {len(actions)} structural actions...")

        create_actions = [a for a in actions if a.action_type == "create_appendix"]
        if create_actions:
            self.create_appendix_section(generated_sections, section_order)

        blocked_figure_moves = [a for a in actions if a.action_type == "move_figure"]
        for action in blocked_figure_moves:
            print(
                f"[Structural] WARNING: ignored move_figure {action.target_id}; "
                "figure appendix moves are disabled"
            )

        move_actions = [a for a in actions if a.action_type == "move_table"]
        if move_actions:
            if "appendix" not in generated_sections:
                self.create_appendix_section(generated_sections, section_order)
            self.move_figures_to_appendix(generated_sections, move_actions)

        resize_actions = [a for a in actions if a.action_type in ("resize_figure", "downgrade_wide")]
        if resize_actions:
            by_section: Dict[str, List[StructuralAction]] = {}
            for action in resize_actions:
                by_section.setdefault(action.section, []).append(action)
            for sec, sec_actions in by_section.items():
                if sec in generated_sections:
                    generated_sections[sec], sec_diagnostics = self.resize_figures_in_section(
                        generated_sections[sec],
                        sec_actions,
                        column_format=column_format,
                    )
                    diagnostics.extend(sec_diagnostics)

        print("[Structural] All structural actions executed")
        return diagnostics
