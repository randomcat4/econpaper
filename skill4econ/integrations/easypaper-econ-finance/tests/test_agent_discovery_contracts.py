import json
from types import SimpleNamespace

import pytest


def _agent_instance(cls):
    return cls.__new__(cls)


def test_agent_endpoints_info_are_json_serializable():
    from src.agents.commander_agent.commander_agent import CommanderAgent
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent
    from src.agents.parse_agent.parse_agent import ParseAgent
    from src.agents.planner_agent.planner_agent import PlannerAgent
    from src.agents.reviewer_agent.reviewer_agent import ReviewerAgent
    from src.agents.template_agent.template_agent import TemplateParserAgent
    from src.agents.typesetter_agent.typesetter_agent import TypesetterAgent
    from src.agents.vlm_review_agent.vlm_review_agent import VLMReviewAgent
    from src.agents.writer_agent.writer_agent import WriterAgent

    agent_classes = [
        CommanderAgent,
        MetaDataAgent,
        ParseAgent,
        PlannerAgent,
        ReviewerAgent,
        TemplateParserAgent,
        TypesetterAgent,
        VLMReviewAgent,
        WriterAgent,
    ]

    for cls in agent_classes:
        endpoints = _agent_instance(cls).endpoints_info
        assert isinstance(endpoints, list)
        assert endpoints, cls.__name__
        json.dumps(endpoints)
        for endpoint in endpoints:
            assert endpoint["path"].startswith("/")
            assert endpoint["method"]
            assert endpoint["description"]


def test_metadata_endpoints_info_covers_plan_stream_and_folder_routes():
    from src.agents.metadata_agent.metadata_agent import MetaDataAgent

    paths = {
        endpoint["path"]
        for endpoint in _agent_instance(MetaDataAgent).endpoints_info
    }

    assert "/metadata/generate" in paths
    assert "/metadata/generate/stream" in paths
    assert "/metadata/prepare-plan" in paths
    assert "/metadata/generate-from-plan/stream" in paths
    assert "/metadata/generate-from-folder" in paths
    assert "/metadata/generate/{task_id}/feedback" in paths
    assert "/metadata/generate/{task_id}/cancel" in paths
    assert "/metadata/generate/{task_id}/resume" in paths


@pytest.mark.asyncio
async def test_list_agents_returns_registered_agent_metadata():
    from src.main import list_agents

    agent = SimpleNamespace(
        name="metadata",
        description="metadata agent",
        endpoints=[{"path": "/wrong"}],
        endpoints_info=[{"path": "/metadata/generate", "method": "POST", "description": "Generate"}],
    )
    import src.main as main_mod

    original_agents = getattr(main_mod.app.state, "agents", None)
    main_mod.app.state.agents = {"metadata": agent}
    try:
        result = await list_agents()
    finally:
        if original_agents is None:
            delattr(main_mod.app.state, "agents")
        else:
            main_mod.app.state.agents = original_agents

    assert result == {
        "agents": [
            {
                "name": "metadata",
                "description": "metadata agent",
                "endpoints": agent.endpoints_info,
                "status": "active",
            }
        ]
    }
