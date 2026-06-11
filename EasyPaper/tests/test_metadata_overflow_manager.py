from types import SimpleNamespace

from src.agents.metadata_agent.models import StructuralAction
from src.agents.metadata_agent.overflow_manager import OverflowManager


def test_overflow_manager_plans_structural_actions_for_large_overflow():
    manager = OverflowManager()
    generated_sections = {
        "introduction": (
            "\\begin{figure*}\\includegraphics[width=\\textwidth]{fig1}\\label{fig:one}\\end{figure*}\n"
            "\\begin{table}\\label{tab:one}\\end{table}"
        ),
        "conclusion": "",
    }
    paper_plan = SimpleNamespace(sections=[SimpleNamespace(section_type="introduction")])

    actions = manager.plan_overflow_strategy(
        overflow_pages=2.0,
        generated_sections=generated_sections,
        paper_plan=paper_plan,
        figures=[],
    )

    assert actions
    assert not any(action.action_type == "move_figure" for action in actions)
    assert any(action.action_type in {"downgrade_wide", "resize_figure"} for action in actions)


def test_overflow_manager_blocks_figure_appendix_move_and_resizes_in_place():
    manager = OverflowManager()
    generated_sections = {
        "introduction": (
            "\\begin{figure*}\\includegraphics[width=\\textwidth]{fig1}\\label{fig:one}\\end{figure*}"
        )
    }
    section_order = ["introduction", "conclusion"]
    actions = [
        StructuralAction(action_type="create_appendix"),
        StructuralAction(action_type="move_figure", target_id="fig:one", section="introduction"),
        StructuralAction(
            action_type="resize_figure",
            target_id="fig:one",
            section="introduction",
            params={"width": "0.8\\linewidth"},
        ),
    ]

    diagnostics = manager.execute_structural_actions(actions, generated_sections, section_order)

    assert "\\begin{figure" in generated_sections["introduction"]
    assert "width=0.8\\linewidth" in generated_sections["introduction"]
    assert "fig:one" in generated_sections["introduction"]
    assert "appendix" not in generated_sections or "fig:one" not in generated_sections["appendix"]
    assert diagnostics == []


def test_wide_figure_downgrade_overlap_regression_is_label_targeted():
    manager = OverflowManager()
    generated_sections = {
        "result": (
            "\\begin{figure*}\\includegraphics[width=0.92\\textwidth]{fig:wide}"
            "\\caption{Wide}\\label{fig:wide}\\end{figure*}\n"
            "\\begin{figure*}\\includegraphics[width=0.92\\textwidth]{fig:other}"
            "\\caption{Other}\\label{fig:other}\\end{figure*}"
        )
    }
    actions = [
        StructuralAction(
            action_type="downgrade_wide",
            target_id="fig:wide",
            section="result",
        )
    ]

    diagnostics = manager.execute_structural_actions(actions, generated_sections, ["result"])

    assert diagnostics == []
    assert "\\label{fig:wide}\\end{figure}" in generated_sections["result"]
    assert "width=0.82\\linewidth" in generated_sections["result"]
    assert "\\label{fig:other}\\end{figure*}" in generated_sections["result"]
    assert "width=0.92\\textwidth]{fig:wide}" not in generated_sections["result"]


def test_missing_downgrade_label_returns_error_without_broad_mutation():
    manager = OverflowManager()
    generated_sections = {
        "result": "\\begin{figure*}\\includegraphics[width=0.92\\textwidth]{fig:other}\\label{fig:other}\\end{figure*}"
    }
    actions = [
        StructuralAction(
            action_type="downgrade_wide",
            target_id="fig:missing",
            section="result",
        )
    ]

    diagnostics = manager.execute_structural_actions(actions, generated_sections, ["result"])

    assert len(diagnostics) == 1
    assert diagnostics[0].severity == "error"
    assert diagnostics[0].code == "target_label_not_found"
    assert "\\begin{figure*}" in generated_sections["result"]
