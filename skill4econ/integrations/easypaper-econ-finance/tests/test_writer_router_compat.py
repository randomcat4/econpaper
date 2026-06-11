"""
Compatibility tests for the public writer surface after internal migration.
"""
import inspect
from unittest.mock import AsyncMock

import pytest


def test_writer_run_no_longer_uses_agent_ainvoke():
    from src.agents.writer_agent.writer_agent import WriterAgent

    source = inspect.getsource(WriterAgent.run)
    assert "self.agent.ainvoke" not in source, (
        "WriterAgent.run() should no longer execute the deprecated LangGraph "
        "graph directly."
    )


def test_writer_init_no_longer_builds_legacy_graph():
    from src.agents.writer_agent.writer_agent import WriterAgent

    source = inspect.getsource(WriterAgent.__init__)
    assert "self.init_agent()" not in source, (
        "WriterAgent should not eagerly initialize the deprecated LangGraph "
        "workflow during normal startup."
    )


def test_writer_no_longer_defines_init_agent():
    from src.agents.writer_agent.writer_agent import WriterAgent

    assert not hasattr(WriterAgent, "init_agent"), (
        "WriterAgent should no longer carry the dead LangGraph init_agent() "
        "constructor after cleanup."
    )


def test_writer_module_no_longer_exports_deprecated_aliases():
    import src.agents.writer_agent as writer_module

    deprecated_exports = {
        "NodeContent",
        "SectionContext",
        "ResourceRequirement",
        "SECTION_REQUIRED_RESOURCES",
        "ClaimType",
        "ClaimRelation",
        "Claim",
    }
    assert deprecated_exports.isdisjoint(set(writer_module.__all__)), (
        "writer_agent should not re-export deprecated compatibility aliases "
        "after cleanup."
    )
    for name in deprecated_exports:
        assert not hasattr(writer_module, name), (
            f"writer_agent should not expose deprecated alias {name} after cleanup."
        )


def test_writer_section_models_no_longer_define_deprecated_aliases():
    from src.agents.writer_agent import section_models

    removed_symbols = {
        "NodeContent",
        "SectionContext",
        "ResourceRequirement",
        "SECTION_REQUIRED_RESOURCES",
        "ClaimType",
        "ClaimRelation",
        "Claim",
    }
    for name in removed_symbols:
        assert not hasattr(section_models, name), (
            f"section_models should not define deprecated alias {name} after cleanup."
        )
    assert not hasattr(section_models.ArgumentStructure, "main_claims"), (
        "ArgumentStructure should no longer carry the deprecated main_claims property."
    )
    assert not hasattr(section_models.SectionRequirement, "min_claims"), (
        "SectionRequirement should no longer carry the deprecated min_claims property."
    )


def test_commander_no_longer_defines_compile_writer_prompt_alias():
    from src.agents.commander_agent.commander_agent import CommanderAgent

    assert not hasattr(CommanderAgent, "compile_writer_prompt"), (
        "CommanderAgent should not keep the deprecated compile_writer_prompt alias."
    )


@pytest.mark.asyncio
async def test_writer_run_preserves_basic_result_shape():
    from src.agents.writer_agent.writer_agent import WriterAgent

    agent = WriterAgent.__new__(WriterAgent)
    agent.generate_content = AsyncMock(return_value={
        "generated_content": "Draft text",
        "llm_calls": 1,
        "iteration": 1,
    })
    agent.mini_review = AsyncMock(return_value={
        "generated_content": "Draft text",
        "review_result": {"passed": True},
        "review_history": [{"passed": True, "issues": [], "warnings": []}],
        "invalid_citations_removed": [],
    })
    agent.revise_content = AsyncMock()
    agent.extract_references = AsyncMock(return_value={
        "citation_ids": ["smith2024"],
        "figure_ids": [],
        "table_ids": [],
        "paragraph_units": [],
        "writer_response_section": [],
        "writer_response_paragraph": [],
    })
    agent._should_revise = lambda state: "done"

    result = await WriterAgent.run(
        agent,
        system_prompt="sys",
        user_prompt="user",
        section_type="introduction",
        enable_review=True,
    )

    assert result["generated_content"] == "Draft text"
    assert result["review_result"]["passed"] is True
    assert result["citation_ids"] == ["smith2024"]
    assert isinstance(result["review_history"], list)
    agent.generate_content.assert_awaited_once()
    agent.mini_review.assert_awaited_once()
    agent.extract_references.assert_awaited_once()
    agent.revise_content.assert_not_called()
